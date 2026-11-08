package com.oddfactory.update;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageInstaller;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.widget.Toast;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Locale;

import javax.net.ssl.HttpsURLConnection;

final class ApkInstaller {
    private static final int INSTALL_PERMISSION = 401;
    private static final int NETWORK_TIMEOUT_MS = 12_000;
    private static final long MAX_DOWNLOAD_MS = 120_000L;
    private final Activity activity;
    private final PackageInstaller installer;
    private final String statusAction;
    private UpdateCheck.Release permissionRequest;
    private Intent systemPrompt;
    private volatile int activeSession = -1;
    private volatile boolean destroyed;
    private boolean registered;
    private boolean started;
    private boolean systemPromptOpened;

    ApkInstaller(Activity activity) {
        this.activity = activity;
        installer = activity.getPackageManager().getPackageInstaller();
        statusAction = activity.getPackageName() + ".INSTALL_UPDATE";
    }

    boolean busy() {
        return started || permissionRequest != null;
    }

    void request(UpdateCheck.Release release) {
        if (busy() || destroyed) return;
        if (activity.getPackageManager().canRequestPackageInstalls()) {
            start(release);
            return;
        }
        permissionRequest = release;
        toast("두두 키우기의 앱 설치 허용을 켜 주세요.");
        try {
            activity.startActivityForResult(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.fromParts("package", activity.getPackageName(), null)), INSTALL_PERMISSION);
        } catch (ActivityNotFoundException e) {
            permissionRequest = null;
            toast("앱 설치 허용 설정을 열 수 없어요.");
        }
    }

    void onActivityResult(int requestCode) {
        if (requestCode != INSTALL_PERMISSION || permissionRequest == null) return;
        UpdateCheck.Release release = permissionRequest;
        permissionRequest = null;
        if (activity.getPackageManager().canRequestPackageInstalls()) start(release);
    }

    void onWindowFocus() {
        if (systemPrompt == null || destroyed || !activity.hasWindowFocus()) return;
        Intent intent = systemPrompt;
        systemPrompt = null;
        try {
            activity.startActivity(intent);
            systemPromptOpened = true;
        } catch (RuntimeException failure) {
            abandon(activeSession);
            finish("Android 설치창을 열 수 없어요. 다시 시도해 주세요.");
        }
    }

    void destroy() {
        destroyed = true;
        if (registered) activity.unregisterReceiver(callback);
        registered = false;
        if (!systemPromptOpened) abandon(activeSession);
    }

    private void start(UpdateCheck.Release release) {
        started = true;
        systemPromptOpened = false;
        try {
            IntentFilter filter = new IntentFilter(statusAction);
            if (Build.VERSION.SDK_INT >= 33) {
                activity.registerReceiver(callback, filter, Context.RECEIVER_NOT_EXPORTED);
            } else {
                // The update status is sent through an app-created PendingIntent.
                activity.registerReceiver(callback, filter, activity.getPackageName() + ".UPDATE_STATUS", null);
            }
            registered = true;
        } catch (RuntimeException failure) {
            finish("업데이트 설치를 준비할 수 없어요.");
            return;
        }
        toast(release.versionName + " 버전을 내려받고 있어요.");
        new Thread(() -> stage(release), "download-update").start();
    }

    private void stage(UpdateCheck.Release release) {
        int sessionId = -1;
        try {
            PackageInstaller.SessionParams params =
                    new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
            params.setAppPackageName(activity.getPackageName());
            params.setSize(release.size);
            if (Build.VERSION.SDK_INT >= 31) {
                params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED);
            }
            if (Build.VERSION.SDK_INT >= 33) {
                params.setPackageSource(PackageInstaller.PACKAGE_SOURCE_DOWNLOADED_FILE);
            }
            sessionId = installer.createSession(params);
            activeSession = sessionId;
            try (PackageInstaller.Session session = installer.openSession(sessionId)) {
                download(release, session);
                if (destroyed) throw new IOException("Activity closed");
                Intent status = new Intent(statusAction).setPackage(activity.getPackageName());
                int flags = PendingIntent.FLAG_UPDATE_CURRENT;
                if (Build.VERSION.SDK_INT >= 31) flags |= PendingIntent.FLAG_MUTABLE;
                PendingIntent pending = PendingIntent.getBroadcast(activity, sessionId, status, flags);
                session.commit(pending.getIntentSender());
            }
        } catch (Exception failure) {
            abandon(sessionId);
            activity.runOnUiThread(() -> {
                if (!destroyed) finish("업데이트를 내려받거나 확인할 수 없어요. 다시 시도해 주세요.");
            });
        }
    }

    private void download(UpdateCheck.Release release, PackageInstaller.Session session) throws Exception {
        URL url = new URL(release.downloadUrl);
        long startedAt = android.os.SystemClock.elapsedRealtime();
        for (int hop = 0; hop < 5; hop++) {
            String host = url.getHost().toLowerCase(Locale.ROOT);
            if (!"https".equals(url.getProtocol()) || url.getUserInfo() != null
                    || (url.getPort() != -1 && url.getPort() != 443)
                    || !(host.equals("github.com") || host.equals("release-assets.githubusercontent.com")
                         || host.equals("objects.githubusercontent.com"))) {
                throw new IOException("Unexpected download host");
            }
            HttpsURLConnection connection = (HttpsURLConnection) url.openConnection();
            try {
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(NETWORK_TIMEOUT_MS);
                connection.setReadTimeout(NETWORK_TIMEOUT_MS);
                connection.setRequestProperty("User-Agent", "ODD-FACTORY-Android");
                int status = connection.getResponseCode();
                if (status >= 300 && status < 400) {
                    String location = connection.getHeaderField("Location");
                    if (location == null) throw new IOException("Missing redirect");
                    url = new URL(url, location);
                    continue;
                }
                long length = connection.getContentLengthLong();
                if (status != 200 || (length >= 0 && length != release.size)) {
                    throw new IOException("Unexpected APK response");
                }
                MessageDigest hash = MessageDigest.getInstance("SHA-256");
                try (InputStream in = connection.getInputStream();
                     OutputStream out = session.openWrite("base.apk", 0, release.size)) {
                    byte[] buffer = new byte[32 * 1024];
                    long read = 0;
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        read += count;
                        if (destroyed || read > release.size
                                || android.os.SystemClock.elapsedRealtime() - startedAt > MAX_DOWNLOAD_MS) {
                            throw new IOException("Invalid or interrupted download");
                        }
                        hash.update(buffer, 0, count);
                        out.write(buffer, 0, count);
                    }
                    if (read != release.size
                            || !MessageDigest.isEqual(hash.digest(), release.sha256)) {
                        throw new IOException("APK checksum mismatch");
                    }
                    session.fsync(out);
                }
                return;
            } finally {
                connection.disconnect();
            }
        }
        throw new IOException("Too many APK redirects");
    }

    private final BroadcastReceiver callback = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent result) {
            if (destroyed || !statusAction.equals(result.getAction()) || activeSession < 0
                    || result.getIntExtra(PackageInstaller.EXTRA_SESSION_ID, -1) != activeSession) return;
            int status = result.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
            if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
                systemPrompt = Build.VERSION.SDK_INT >= 33
                        ? result.getParcelableExtra(Intent.EXTRA_INTENT, Intent.class)
                        : result.getParcelableExtra(Intent.EXTRA_INTENT);
                if (systemPrompt == null) {
                    abandon(activeSession);
                    finish("Android 설치창을 열 수 없어요.");
                } else onWindowFocus();
                return;
            }
            if (status == PackageInstaller.STATUS_SUCCESS) finish("업데이트가 완료됐어요.");
            else if (status == PackageInstaller.STATUS_FAILURE_ABORTED) finish(null);
            else finish("Android에서 설치를 완료하지 못했어요. 설치 안내를 확인해 주세요.");
        }
    };

    private void abandon(int id) {
        if (id < 0) return;
        try {
            installer.abandonSession(id);
        } catch (RuntimeException ignored) {
            // Session already closed by Android.
        }
    }

    private void finish(String message) {
        started = false;
        activeSession = -1;
        systemPrompt = null;
        systemPromptOpened = false;
        if (registered) activity.unregisterReceiver(callback);
        registered = false;
        if (message != null) toast(message);
    }

    private void toast(String text) {
        Toast.makeText(activity, text, Toast.LENGTH_SHORT).show();
    }
}

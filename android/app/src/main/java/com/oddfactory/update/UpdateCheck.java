package com.oddfactory.update;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Build;
import android.os.SystemClock;
import android.view.View;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.function.Consumer;

import javax.net.ssl.HttpsURLConnection;

public final class UpdateCheck {
    private static final String REPOSITORY = "oddfactory-dudu-motion";
    private static final String ASSET = "oddfactory-dudu";   // APK 파일명: oddfactory-dudu-vc<code>-sdk<min>.apk
    private static final String FEED =
            "https://api.github.com/repos/kimdongho321/" + REPOSITORY + "/releases/latest";
    private static final int MAX_BYTES = 128 * 1024;
    private static final int TIMEOUT_MS = 6000;
    private static final long AUTO_INTERVAL_MS = 2 * 60_000L;

    private final Activity activity;
    private final Consumer<View> applyFont;
    private final ApkInstaller installer;
    private long lastRequest = -AUTO_INTERVAL_MS;
    private boolean foreground;
    private boolean running;
    private boolean manual;
    private AlertDialog dialog;

    public UpdateCheck(Activity activity, Consumer<View> applyFont) {
        this.activity = activity;
        this.applyFont = applyFont;
        installer = new ApkInstaller(activity);
    }

    public void resume() {
        foreground = true;
        check(false);
    }

    public void pause() {
        foreground = false;
        manual = false;
        if (dialog != null) dialog.dismiss();
    }

    public void checkNow() {
        check(true);
    }

    public void destroy() { installer.destroy(); }

    public void onActivityResult(int requestCode) { installer.onActivityResult(requestCode); }

    public void onWindowFocus() { installer.onWindowFocus(); }

    private void check(boolean requested) {
        if (!foreground || dialog != null || installer.busy()) return;
        long now = SystemClock.elapsedRealtime();
        if (!requested && now - lastRequest < AUTO_INTERVAL_MS) return;
        if (requested && !manual) {
            manual = true;
            toast("새 버전을 확인하고 있어요.");
        }
        if (running) return;
        running = true;
        lastRequest = now;
        String packageName = activity.getPackageName();
        new Thread(() -> {
            Release release = null;
            boolean failed = false;
            try {
                android.content.pm.PackageInfo info = activity.getPackageManager()
                        .getPackageInfo(packageName, 0);
                long installed = Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
                release = select(readFeed(), installed);
            } catch (Exception e) {
                failed = true;
            }
            Release result = release;
            boolean error = failed;
            activity.runOnUiThread(() -> deliver(result, error));
        }, "update-check").start();
    }

    private void deliver(Release release, boolean failed) {
        running = false;
        boolean requested = manual;
        manual = false;
        if (!foreground || activity.isFinishing() || activity.isDestroyed()) return;
        if (failed) {
            if (requested) toast("업데이트를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.");
            return;
        }
        if (release == null) {
            if (requested) toast("최신 버전을 사용 중이에요.");
            return;
        }
        if (Build.VERSION.SDK_INT < release.minSdk) {
            if (requested) toast("새 버전은 더 최신 Android가 필요해요.");
            return;
        }
        if (!requested && !activity.hasWindowFocus()) {
            lastRequest = -AUTO_INTERVAL_MS;
            return;
        }
        dialog = new AlertDialog.Builder(activity)
                .setTitle("새 버전이 있어요")
                .setMessage(release.versionName + " 버전을 내려받아 설치할 수 있어요.")
                .setPositiveButton("다운로드", (d, w) -> installer.request(release))
                .setNegativeButton("나중에", null)
                .create();
        dialog.setOnDismissListener(d -> dialog = null);
        dialog.show();
        applyFont.accept(dialog.getWindow().getDecorView());
    }

    private void toast(String message) {
        Toast.makeText(activity, message, Toast.LENGTH_SHORT).show();
    }

    static Release select(String json, long installed) throws JSONException {
        JSONObject feed = new JSONObject(json);
        if (feed.getBoolean("draft") || feed.getBoolean("prerelease")) return null;
        String tag = feed.getString("tag_name");
        if (!tag.matches("v[0-9]+[.][0-9]+[.][0-9]+")) {
            throw new JSONException("Invalid release tag");
        }
        org.json.JSONArray assets = feed.getJSONArray("assets");
        java.util.regex.Pattern apkName = java.util.regex.Pattern.compile(
                ASSET + "-vc([1-9][0-9]{0,8})-sdk([1-9][0-9]?)\\.apk");
        Release release = null;
        for (int i = 0; i < assets.length(); i++) {
            JSONObject asset = assets.getJSONObject(i);
            String name = asset.getString("name");
            java.util.regex.Matcher match = apkName.matcher(name);
            if (!match.matches()) continue;
            if (release != null) throw new JSONException("Ambiguous release APK");
            String url = "https://github.com/kimdongho321/" + REPOSITORY
                    + "/releases/download/" + tag + "/" + name;
            if (!url.equals(asset.getString("browser_download_url"))
                    || !"uploaded".equals(asset.getString("state"))) {
                throw new JSONException("Invalid release APK");
            }
            long size = asset.getLong("size");
            String digest = asset.getString("digest");
            if (size <= 0 || size > 100L * 1024 * 1024 || !digest.matches("sha256:[a-f0-9]{64}")) {
                throw new JSONException("Invalid release APK digest");
            }
            byte[] sha256 = new byte[32];
            for (int b = 0; b < sha256.length; b++) {
                int offset = 7 + b * 2;
                sha256[b] = (byte) Integer.parseInt(digest.substring(offset, offset + 2), 16);
            }
            release = new Release(tag.substring(1), url, Integer.parseInt(match.group(1)),
                    Integer.parseInt(match.group(2)), size, sha256);
        }
        return release != null && release.versionCode > installed ? release : null;
    }

    private static String readFeed() throws IOException {
        URL url = new URL(FEED);
        long deadline = SystemClock.elapsedRealtime() + TIMEOUT_MS;
        for (int hop = 0; hop < 4; hop++) {
            String host = url.getHost();
            if (!"https".equals(url.getProtocol())
                    || !"api.github.com".equals(host)
                    || url.getUserInfo() != null || (url.getPort() != -1 && url.getPort() != 443)) {
                throw new IOException("Unexpected GitHub redirect");
            }
            HttpsURLConnection connection = (HttpsURLConnection) url.openConnection();
            try {
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(remaining(deadline));
                connection.setReadTimeout(remaining(deadline));
                connection.setUseCaches(false);
                connection.setRequestProperty("Accept", "application/vnd.github+json");
                connection.setRequestProperty("User-Agent", "ODD-FACTORY-Android");
                connection.setRequestProperty("Cache-Control", "no-cache");
                int status = connection.getResponseCode();
                if (status >= 300 && status < 400) {
                    String location = connection.getHeaderField("Location");
                    if (location == null) throw new IOException("Missing GitHub redirect");
                    url = new URL(url, location);
                    continue;
                }
                if (status != 200 || connection.getContentLength() > MAX_BYTES) {
                    throw new IOException("Invalid update list response");
                }
                try (InputStream stream = connection.getInputStream()) {
                    ByteArrayOutputStream data = new ByteArrayOutputStream();
                    byte[] block = new byte[2048];
                    int length;
                    while ((length = stream.read(block)) != -1) {
                        remaining(deadline);
                        if (data.size() + length > MAX_BYTES) throw new IOException("Update list too large");
                        data.write(block, 0, length);
                    }
                    String value = new String(data.toByteArray(), StandardCharsets.UTF_8);
                    return value.startsWith("\uFEFF") ? value.substring(1) : value;
                }
            } finally {
                connection.disconnect();
            }
        }
        throw new IOException("Too many GitHub redirects");
    }

    private static int remaining(long deadline) throws IOException {
        long left = deadline - SystemClock.elapsedRealtime();
        if (left <= 0) throw new IOException("Update check timed out");
        return (int) left;
    }

    static final class Release {
        final String versionName;
        final String downloadUrl;
        final int versionCode;
        final int minSdk;
        final long size;
        final byte[] sha256;

        Release(String versionName, String downloadUrl, int versionCode, int minSdk, long size, byte[] sha256) {
            this.versionName = versionName;
            this.downloadUrl = downloadUrl;
            this.versionCode = versionCode;
            this.minSdk = minSdk;
            this.size = size;
            this.sha256 = sha256;
        }
    }
}

package com.oddfactory.dudu;

import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.os.Build;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;

/** Crops the display window around the sprite while keeping the WebView's world coordinates. */
final class PetWindow extends FrameLayout {
    interface Listener {
        void pointer(String type, float x, float y);
    }

    private final WindowManager manager;
    private final RuntimeView web;
    private final Listener listener;
    private final WindowManager.LayoutParams layout;
    private final Rect world = new Rect();
    private final Rect bounds = new Rect();
    private boolean showing;
    private boolean active;
    private boolean suppress;

    PetWindow(Context context, WindowManager manager, RuntimeView web, Rect world, Listener listener) {
        super(context);
        this.manager = manager;
        this.web = web;
        this.listener = listener;
        setBackgroundColor(Color.TRANSPARENT);
        setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
        addView(web, new FrameLayout.LayoutParams(world.width(), world.height()));
        this.world.set(world);
        layout = new WindowManager.LayoutParams(1, 1, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                PixelFormat.TRANSLUCENT);
        layout.gravity = Gravity.TOP | Gravity.LEFT;
        layout.x = world.left;
        layout.y = world.top;
        layout.alpha = 0f;
        layout.setTitle("com.oddfactory.dudu.overlay");
        if (Build.VERSION.SDK_INT >= 30) {
            layout.setFitInsetsTypes(0);
            layout.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;
        } else if (Build.VERSION.SDK_INT >= 28) {
            layout.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }
        if (Build.VERSION.SDK_INT >= 34) layout.setCanPlayMoveAnimation(false);
    }

    void attach() {
        manager.addView(this, layout);
    }

    void place(Rect next) {
        if (bounds.equals(next)) return;
        bounds.set(next);
        applyWindow();
    }

    void show(boolean value) {
        if (showing == value) return;
        showing = value;
        if (!showing) cancelGesture();
        applyWindow();
    }

    void resizeWorld(Rect next) {
        cancelGesture();
        world.set(next);
        bounds.setEmpty();
        web.setLayoutParams(new FrameLayout.LayoutParams(next.width(), next.height()));
        applyWindow();
    }

    private void applyWindow() {
        boolean visible = showing && !bounds.isEmpty();
        int x = visible ? bounds.left : world.left;
        int y = visible ? bounds.top : world.top;
        int width = visible ? bounds.width() : 1;
        int height = visible ? bounds.height() : 1;
        float alpha = visible ? 1f : 0f;
        if (layout.x == x && layout.y == y && layout.width == width
                && layout.height == height && layout.alpha == alpha) return;

        layout.x = x;
        layout.y = y;
        layout.width = width;
        layout.height = height;
        layout.alpha = alpha;
        if (visible) {
            layout.flags &= ~WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        } else {
            layout.flags |= WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        }
        web.setTranslationX(world.left - x);
        web.setTranslationY(world.top - y);
        manager.updateViewLayout(this, layout);
    }

    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        if (!showing) return false;
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) suppress = false;
        if (event.getPointerCount() > 1 || action == MotionEvent.ACTION_POINTER_DOWN) {
            cancelGesture();
            suppress = true;
        }
        if (suppress) return true;
        switch (action) {
            case MotionEvent.ACTION_DOWN:
                active = true;
                send("down", event);
                break;
            case MotionEvent.ACTION_MOVE:
                if (active) send("move", event);
                break;
            case MotionEvent.ACTION_UP:
                if (active) send("up", event);
                active = false;
                break;
            case MotionEvent.ACTION_CANCEL:
                cancelGesture();
                break;
            default:
                break;
        }
        return true;
    }

    private void send(String type, MotionEvent event) {
        listener.pointer(type, event.getRawX(), event.getRawY());
    }

    private void cancelGesture() {
        if (active) listener.pointer("cancel", 0, 0);
        active = false;
        suppress = false;
    }

    void close() {
        cancelGesture();
        if (isAttachedToWindow() || getParent() != null) manager.removeViewImmediate(this);
    }
}

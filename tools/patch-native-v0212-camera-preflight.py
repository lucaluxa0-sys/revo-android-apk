#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/MacroEngine.java")
service_p = Path("revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java")
s = p.read_text()
service_s = service_p.read_text()

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"missing marker: {label}")
    s = s.replace(old, new, 1)

def service_once(old, new, label):
    global service_s
    if old not in service_s:
        raise SystemExit(f"missing service marker: {label}")
    service_s = service_s.replace(old, new, 1)

once(
'''    private final RevoPreGatherRouter routing;
    private final RevoGatherAdapter gather;

    private volatile Thread worker;
''',
'''    private final RevoPreGatherRouter routing;
    private final RevoGatherAdapter gather;

    private enum CameraPreflightState {
        WAIT_ROBLOX, OPEN_SETTINGS, SEEK_CLASSIC, CLOSE_MENU, DONE, FAILED
    }

    // Bright reference pixels from the word "Classic" in Roblox mobile's
    // Camera Mode row. Direct coordinates are deliberately used instead of a
    // packed bitset so the detector is auditable and cannot suffer bit-order
    // encoding mistakes.
    private static final int CAMERA_REF_W = 120;
    private static final int CAMERA_REF_H = 38;
    private static final int[] CAMERA_CLASSIC_X = new int[] {42,43,46,47,50,41,47,50,40,50,54,55,56,62,63,64,69,70,71,75,80,81,82,40,50,53,57,61,65,68,72,75,79,83,40,50,58,61,68,75,78,40,50,55,56,57,58,62,69,75,78,40,50,53,58,64,65,71,72,75,78,40,41,50,53,58,65,72,75,78,41,42,47,50,53,57,58,61,65,68,72,75,78,79,83,43,44,45,46,50,54,55,56,58,62,63,64,69,70,71,75,80,81,82};
    private static final int[] CAMERA_CLASSIC_Y = new int[] {15,15,15,15,15,16,16,16,17,17,17,17,17,17,17,17,17,17,17,17,17,17,17,18,18,18,18,18,18,18,18,18,18,18,19,19,19,19,19,19,19,20,20,20,20,20,20,20,20,20,20,21,21,21,21,21,21,21,21,21,21,22,22,22,22,22,22,22,22,22,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24,24};

    private volatile CameraPreflightState cameraPreflightState = CameraPreflightState.DONE;
    private volatile long cameraPreflightNextAtMs = 0;
    private volatile int cameraPreflightTaps = 0;
    private volatile int cameraPreflightMenuRetries = 0;
    private volatile int cameraPreflightGameplayReadyFrames = 0;
    private volatile boolean routeStarted = false;

    private volatile Thread worker;
''',
"preflight fields")

once(
'''        frameCount.set(0);
        routing.onStart();
        gather.onStart();
        status = "Starting";
''',
'''        frameCount.set(0);
        routeStarted = false;
        cameraPreflightState = CameraPreflightState.WAIT_ROBLOX;
        cameraPreflightNextAtMs = 0;
        cameraPreflightTaps = 0;
        cameraPreflightMenuRetries = 0;
        cameraPreflightGameplayReadyFrames = 0;
        status = "Starting camera preflight";
''',
"start preflight")

once(
'''        status = "Stopped";
        routing.onStop();
        gather.onStop();
''',
'''        status = "Stopped";
        routeStarted = false;
        cameraPreflightState = CameraPreflightState.DONE;
        routing.onStop();
        gather.onStop();
''',
"stop preflight")

once(
'''        long captureNowMs = SystemClock.elapsedRealtime();
        if (captureInFlight.get()) {
''',
'''        long captureNowMs = SystemClock.elapsedRealtime();
        // Do not begin a screenshot while a camera-setting gesture is still
        // settling. Screenshot callbacks can arrive much later than capture
        // time, so gating only in onFrame() can feed stale UI pixels into the
        // preflight and skip straight past Classic.
        if (!routeStarted && captureNowMs < cameraPreflightNextAtMs) return;
        if (captureInFlight.get()) {
''',
"preflight capture settle gate")

once(
'''    private void onFrame(Bitmap frame) {
        if (routing.onFrame(frame)) gather.onFrame(frame);
    }

    private void updateStatus() {
''',
'''    private void onFrame(Bitmap frame) {
        if (!routeStarted) {
            if (!runCameraPreflight(frame)) return;
            routing.onStart();
            gather.onStart();
            routeStarted = true;
        }
        if (routing.onFrame(frame)) gather.onFrame(frame);
    }

    private boolean runCameraPreflight(Bitmap frame) {
        RevoAccessibilityService svc = RevoAccessibilityService.get();
        if (svc == null) {
            status = "Enable Revolution Accessibility";
            return false;
        }

        String pkg = svc.activePackageName();
        if (pkg == null || !pkg.contains("com.roblox.client")) {
            status = "Waiting for Roblox before camera preflight";
            return false;
        }

        final long now = SystemClock.elapsedRealtime();
        final int w = frame.getWidth();
        final int h = frame.getHeight();

        switch (cameraPreflightState) {
            case WAIT_ROBLOX:
                // A cached foreground package can become Roblox before Android
                // exposes a real active/focused Accessibility application window.
                // dispatchGesture() can return true in that gap even though
                // InputDispatcher later drops the touch. Do not start the settle
                // timer or consume retries until a live Roblox window/root exists.
                if (!svc.isRobloxTouchWindowReady()) {
                    cameraPreflightGameplayReadyFrames = 0;
                    cameraPreflightNextAtMs = 0;
                    status = "Camera preflight: waiting for touch-ready Roblox window";
                    return false;
                }
                // A live Roblox application window also exists on Home/join/loading
                // screens. Require the actual mobile gameplay controls before a
                // pause-menu retry can be consumed.
                if (!isRobloxGameplayReady(frame)) {
                    cameraPreflightGameplayReadyFrames = 0;
                    cameraPreflightNextAtMs = 0;
                    status = "Camera preflight: waiting for Bee Swarm gameplay HUD";
                    return false;
                }
                cameraPreflightGameplayReadyFrames++;
                if (cameraPreflightGameplayReadyFrames < 2) {
                    cameraPreflightNextAtMs = 0;
                    status = "Camera preflight: confirming gameplay HUD";
                    return false;
                }
                // Once gameplay is visually ready on consecutive frames, preserve
                // a short settle window before opening the Roblox pause menu.
                if (cameraPreflightNextAtMs == 0) {
                    cameraPreflightNextAtMs = now + 500;
                    status = "Camera preflight: settling gameplay";
                    return false;
                }
                if (now < cameraPreflightNextAtMs) return false;
                boolean menuTapAccepted = svc.tap(
                        displayId, w * 0.0604167f, h * 0.0962963f, 35);
                if (!menuTapAccepted) {
                    cameraPreflightMenuRetries++;
                    if (cameraPreflightMenuRetries >= 4) {
                        cameraPreflightState = CameraPreflightState.FAILED;
                        lastError = "Camera preflight could not open Roblox pause menu";
                        status = "Camera preflight failed";
                        running.set(false);
                        return false;
                    }
                    cameraPreflightNextAtMs = now + 500;
                    status = "Camera preflight: menu gesture rejected; retrying";
                    return false;
                }
                cameraPreflightState = CameraPreflightState.OPEN_SETTINGS;
                cameraPreflightNextAtMs = now + 500;
                status = "Camera preflight: verifying pause menu";
                return false;

            case OPEN_SETTINGS:
                if (now < cameraPreflightNextAtMs) return false;
                if (!isRobloxPauseMenuOpen(frame)) {
                    // If rotation/loading temporarily removes Roblox's actionable
                    // Accessibility window, wait without burning a retry. A queued
                    // dispatchGesture is not proof the touch reached Roblox.
                    if (!svc.isRobloxTouchWindowReady()) {
                        cameraPreflightNextAtMs = now + 250;
                        status = "Camera preflight: waiting for touch-ready Roblox window";
                        return false;
                    }
                    if (cameraPreflightMenuRetries >= 4) {
                        cameraPreflightState = CameraPreflightState.FAILED;
                        lastError = "Camera preflight could not open Roblox pause menu";
                        status = "Camera preflight failed";
                        running.set(false);
                        return false;
                    }
                    boolean retryAccepted = svc.tap(
                            displayId, w * 0.0604167f, h * 0.0962963f, 35);
                    if (retryAccepted) cameraPreflightMenuRetries++;
                    cameraPreflightNextAtMs = now + 500;
                    status = "Camera preflight: pause menu missing; retrying "
                            + cameraPreflightMenuRetries;
                    return false;
                }
                // Settings tab in Roblox's mobile pause menu. Never tap this
                // coordinate until the pause overlay itself is visually verified.
                boolean settingsAccepted = svc.tap(
                        displayId, w * 0.3229167f, h * 0.2444444f, 35);
                if (!settingsAccepted) {
                    cameraPreflightMenuRetries++;
                    if (cameraPreflightMenuRetries >= 4) {
                        cameraPreflightState = CameraPreflightState.FAILED;
                        lastError = "Camera preflight Settings tap rejected";
                        status = "Camera preflight failed";
                        running.set(false);
                        return false;
                    }
                    cameraPreflightNextAtMs = now + 350;
                    status = "Camera preflight: Settings gesture rejected; retrying";
                    return false;
                }
                cameraPreflightState = CameraPreflightState.SEEK_CLASSIC;
                cameraPreflightNextAtMs = now + 500;
                status = "Camera preflight: checking camera mode";
                return false;

            case SEEK_CLASSIC:
                if (now < cameraPreflightNextAtMs) return false;
                // Do not classify or tap until the Camera Mode row itself is visible.
                // Current Roblox can return a stale pause/gameplay screenshot for a
                // short window after the Settings tab tap; blindly cycling here can
                // overshoot Classic even though the tap coordinates are correct.
                if (!isCameraSettingsRowVisible(frame)) {
                    // If the pause menu is definitely still on People, the prior
                    // Settings-tab gesture was queued but never took effect. Retry
                    // only that tab tap; never touch the Camera Mode arrow until the
                    // chevrons prove the Settings row is actually on screen.
                    if (isRobloxPauseMenuOpen(frame) && svc.isRobloxTouchWindowReady()) {
                        if (cameraPreflightMenuRetries >= 4) {
                            cameraPreflightState = CameraPreflightState.FAILED;
                            lastError = "Camera preflight could not open Settings camera row";
                            status = "Camera preflight failed";
                            running.set(false);
                            return false;
                        }
                        boolean retrySettingsAccepted = svc.tap(
                                displayId, w * 0.3229167f, h * 0.2444444f, 35);
                        if (retrySettingsAccepted) cameraPreflightMenuRetries++;
                        cameraPreflightNextAtMs = now + 500;
                        status = "Camera preflight: retrying Settings tab "
                                + cameraPreflightMenuRetries;
                        return false;
                    }
                    cameraPreflightNextAtMs = now + 250;
                    status = "Camera preflight: waiting for Camera Mode row";
                    return false;
                }
                if (isCameraClassic(frame)) {
                    // Toggle the Roblox menu closed.
                    svc.tap(displayId, w * 0.0604167f, h * 0.0962963f, 35);
                    cameraPreflightState = CameraPreflightState.CLOSE_MENU;
                    cameraPreflightNextAtMs = now + 350;
                    status = "Camera preflight: Classic confirmed";
                    return false;
                }
                if (cameraPreflightTaps >= 4) {
                    cameraPreflightState = CameraPreflightState.FAILED;
                    lastError = "Camera preflight could not reach Classic";
                    status = "Camera preflight failed";
                    running.set(false);
                    return false;
                }
                // Camera Mode right-arrow. Cycle until explicit "Classic" is visible.
                svc.tap(displayId, w * 0.9083333f, h * 0.4314815f, 35);
                cameraPreflightTaps++;
                cameraPreflightNextAtMs = now + 450;
                status = "Camera preflight: cycling mode " + cameraPreflightTaps;
                return false;

            case CLOSE_MENU:
                if (now < cameraPreflightNextAtMs) return false;
                cameraPreflightState = CameraPreflightState.DONE;
                status = "Camera preflight complete";
                return true;

            case DONE:
                return true;

            case FAILED:
            default:
                return false;
        }
    }

    private boolean isRobloxGameplayReady(Bitmap frame) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();
        final float scale = Math.min(fw / 960.0f, fh / 540.0f);
        final int cy = Math.round(fh * 0.8425926f);
        final int leftCx = Math.round(fw * 0.09375f);
        final int rightCx = Math.round(fw * 0.90625f);
        final int leftEdges = hudRadialContrastCount(frame, leftCx, cy, scale);
        final int rightEdges = hudRadialContrastCount(frame, rightCx, cy, scale);

        // Measured on real 960x540 BlueStacks frames:
        // joining/loading maxed at left/right=14/16; static-joystick gameplay
        // measured 43/16; Dynamic Thumbstick gameplay can hide the idle left
        // control entirely and measured 0/31. Keep the old strong-left path,
        // but also accept the clearly stronger live jump button by itself.
        return (leftEdges >= 28 && rightEdges >= 12) || rightEdges >= 24;
    }

    private int hudRadialContrastCount(Bitmap frame, int cx, int cy, float scale) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();
        final float innerR = 50.0f * scale;
        final float outerR = 65.0f * scale;
        int strong = 0;
        for (int i = 0; i < 48; i++) {
            double angle = (Math.PI * 2.0 * i) / 48.0;
            int x1 = Math.max(0, Math.min(fw - 1, Math.round(cx + innerR * (float)Math.cos(angle))));
            int y1 = Math.max(0, Math.min(fh - 1, Math.round(cy + innerR * (float)Math.sin(angle))));
            int x2 = Math.max(0, Math.min(fw - 1, Math.round(cx + outerR * (float)Math.cos(angle))));
            int y2 = Math.max(0, Math.min(fh - 1, Math.round(cy + outerR * (float)Math.sin(angle))));
            int p1 = frame.getPixel(x1, y1);
            int p2 = frame.getPixel(x2, y2);
            int l1 = (((p1 >> 16) & 0xff) + ((p1 >> 8) & 0xff) + (p1 & 0xff)) / 3;
            int l2 = (((p2 >> 16) & 0xff) + ((p2 >> 8) & 0xff) + (p2 & 0xff)) / 3;
            if (Math.abs(l1 - l2) >= 18) strong++;
        }
        return strong;
    }

    private boolean isRobloxPauseMenuOpen(Bitmap frame) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();

        // Measured on real 960x540 BlueStacks frames at the hive:
        // pause menu top-tabs band mean ~= (28,28,24), gameplay ~= (156,155,127).
        // A second independent cue is the blue Resume button near (0.78,0.43):
        // pause menu ~= (31,46,108), gameplay ~= (117,92,64).
        final int left = Math.max(0, Math.round(fw * 0.05f));
        final int right = Math.min(fw, Math.round(fw * 0.92f));
        final int top = Math.max(0, Math.round(fh * 0.18f));
        final int bottom = Math.min(fh, Math.round(fh * 0.31f));
        final int stepX = Math.max(1, (right - left) / 24);
        final int stepY = Math.max(1, (bottom - top) / 8);

        long luminanceSum = 0;
        int samples = 0;
        for (int y = top; y < bottom; y += stepY) {
            for (int x = left; x < right; x += stepX) {
                int pixel = frame.getPixel(x, y);
                int r = (pixel >> 16) & 0xff;
                int g = (pixel >> 8) & 0xff;
                int b = pixel & 0xff;
                luminanceSum += (r + g + b) / 3;
                samples++;
            }
        }
        if (samples == 0) return false;
        long mean = luminanceSum / samples;

        int rx = Math.max(0, Math.min(fw - 1, Math.round(fw * 0.78f)));
        int ry = Math.max(0, Math.min(fh - 1, Math.round(fh * 0.43f)));
        int resumePixel = frame.getPixel(rx, ry);
        int rr = (resumePixel >> 16) & 0xff;
        int rg = (resumePixel >> 8) & 0xff;
        int rb = resumePixel & 0xff;
        boolean resumeBlue = rb >= 85 && rb >= rr + 30 && rb >= rg + 20;

        return mean < 80 && resumeBlue;
    }

    private boolean isCameraSettingsRowVisible(Bitmap frame) {
        // Fixed normalized sample grids around the left/right Camera Mode chevrons.
        // Live 960x540 evidence on the current Roblox UI:
        // Settings Follow/Default/Classic = left 29/256, right 39/256;
        // gameplay = left 47/256, right 0/256; pause People = 0/256, 0/256.
        // Requiring both chevrons prevents stale gameplay/pause frames from
        // advancing SEEK_CLASSIC while remaining resolution-independent.
        int leftBright = normalizedBrightGridCount(frame, 0.405f, 0.445f, 0.385f, 0.475f);
        int rightBright = normalizedBrightGridCount(frame, 0.885f, 0.925f, 0.385f, 0.475f);
        return leftBright >= 18 && rightBright >= 24;
    }

    private int normalizedBrightGridCount(Bitmap frame, float x0, float x1, float y0, float y1) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();
        int bright = 0;
        final int cols = 16;
        final int rows = 16;
        for (int gy = 0; gy < rows; gy++) {
            float ny = y0 + (y1 - y0) * ((gy + 0.5f) / rows);
            int y = Math.max(0, Math.min(fh - 1, Math.round(fh * ny)));
            for (int gx = 0; gx < cols; gx++) {
                float nx = x0 + (x1 - x0) * ((gx + 0.5f) / cols);
                int x = Math.max(0, Math.min(fw - 1, Math.round(fw * nx)));
                int pixel = frame.getPixel(x, y);
                int r = (pixel >> 16) & 0xff;
                int g = (pixel >> 8) & 0xff;
                int b = pixel & 0xff;
                if (Math.min(r, Math.min(g, b)) >= 180) bright++;
            }
        }
        return bright;
    }

    private boolean isCameraClassic(Bitmap frame) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();

        final int left = Math.round(fw * 0.609375f);
        final int top = Math.round(fh * 0.3962963f);
        final int cropW = Math.max(1, Math.round(fw * 0.125f));
        final int cropH = Math.max(1, Math.round(fh * 0.0703704f));

        int matched = 0;
        for (int i = 0; i < CAMERA_CLASSIC_X.length; i++) {
            int rx = CAMERA_CLASSIC_X[i];
            int ry = CAMERA_CLASSIC_Y[i];
            int x = left + Math.min(cropW - 1, (rx * cropW) / CAMERA_REF_W);
            int y = top + Math.min(cropH - 1, (ry * cropH) / CAMERA_REF_H);
            x = Math.max(0, Math.min(fw - 1, x));
            y = Math.max(0, Math.min(fh - 1, y));

            int pixel = frame.getPixel(x, y);
            int r = (pixel >> 16) & 0xff;
            int g = (pixel >> 8) & 0xff;
            int b = pixel & 0xff;
            if (Math.min(r, Math.min(g, b)) >= 175) matched++;
        }
        // Measured on real 960x540 BlueStacks frames:
        // Follow=0/104, Classic=104/104, Default(Follow)=19/104.
        return matched >= 76;
    }

    private void updateStatus() {
''',
"preflight methods")

once(
'''        if (RevoAccessibilityService.get() == null) {
            status = "Enable Revolution Accessibility";
            return;
        }
        long elapsed = Math.max(1, SystemClock.elapsedRealtime() - startedAtMs);
''',
'''        if (RevoAccessibilityService.get() == null) {
            status = "Enable Revolution Accessibility";
            return;
        }
        if (!routeStarted) {
            if (cameraPreflightState == CameraPreflightState.FAILED) {
                status = "Camera preflight failed";
            } else {
                status = "Camera preflight: " + cameraPreflightState.name()
                        + " taps=" + cameraPreflightTaps;
            }
            return;
        }
        long elapsed = Math.max(1, SystemClock.elapsedRealtime() - startedAtMs);
''',
"preflight status")

once(
'''            o.put("captureGeneration", captureGeneration.get());
            routing.appendState(o);
''',
'''            o.put("captureGeneration", captureGeneration.get());
            o.put("cameraPreflightState", cameraPreflightState.name());
            o.put("cameraPreflightTaps", cameraPreflightTaps);
            o.put("cameraPreflightMenuRetries", cameraPreflightMenuRetries);
            o.put("routeStarted", routeStarted);
            routing.appendState(o);
''',
"preflight state json")

service_once(
r'''    public boolean isRobloxForeground() {
        return isRobloxPackageName(activePackageName());
    }

''',
r'''    public boolean isRobloxForeground() {
        return isRobloxPackageName(activePackageName());
    }

    /**
     * Stronger than the foreground-package cache: require a current active/focused
     * Accessibility application window whose live root belongs to Roblox.
     * This prevents dispatchGesture() from reporting queued-success while Android
     * still has no touchable Roblox window during launch/rotation.
     */
    public boolean isRobloxTouchWindowReady() {
        try {
            java.util.List<android.view.accessibility.AccessibilityWindowInfo> windows = getWindows();
            if (windows == null) return false;
            for (android.view.accessibility.AccessibilityWindowInfo window : windows) {
                if (window == null
                        || window.getType() != android.view.accessibility.AccessibilityWindowInfo.TYPE_APPLICATION
                        || !(window.isActive() || window.isFocused())) {
                    continue;
                }
                AccessibilityNodeInfo root = window.getRoot();
                if (root == null || root.getPackageName() == null) continue;
                if (isRobloxPackageName(String.valueOf(root.getPackageName()))) return true;
            }
        } catch (Throwable ignored) {}
        return false;
    }

''',
"Roblox touch-ready window gate")

service_p.write_text(service_s)
p.write_text(s)

verify_service = service_p.read_text()
verify_macro = p.read_text()
assert "isRobloxTouchWindowReady()" in verify_service
assert "waiting for touch-ready Roblox window" in verify_macro
assert "isRobloxGameplayReady(frame)" in verify_macro
assert "waiting for Bee Swarm gameplay HUD" in verify_macro
assert "isCameraSettingsRowVisible(frame)" in verify_macro
assert "waiting for Camera Mode row" in verify_macro
assert "retrying Settings tab" in verify_macro
assert "could not open Settings camera row" in verify_macro
print("PASS: installed Roblox gameplay-ready gate + Camera Mode-row visual gate/retry + Classic startup preflight")

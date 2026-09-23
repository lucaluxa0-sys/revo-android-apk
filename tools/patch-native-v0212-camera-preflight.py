#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/MacroEngine.java")
s = p.read_text()

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"missing marker: {label}")
    s = s.replace(old, new, 1)

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

    // Binary mask of the word "Classic" from Roblox mobile's Camera Mode row.
    // Reference crop: x=585..704, y=214..251 on a 960x540 viewport.
    private static final int CAMERA_REF_W = 120;
    private static final int CAMERA_REF_H = 38;
    private static final int CAMERA_REF_ON_PIXELS = 104;
    private static final byte[] CAMERA_CLASSIC_MASK = android.util.Base64.decode(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzIAAAAAAAAAAAAAAAAABBIAAAAAAAAAAAAAAAAACAI4OHEOAAAAAAAAAAAACAJERIkRAAAAAAAAAAAACAICQIEgAAAAAAAAAAAACAIeIEEgAAAAAAAAAAAACAJCDBkgAAAAAAAAAAAADAJCBAkgAAAAAAAAAAAABhJGRIkxAAAAAAAAAAAAAeI6OHEOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            android.util.Base64.DEFAULT);

    private volatile CameraPreflightState cameraPreflightState = CameraPreflightState.DONE;
    private volatile long cameraPreflightNextAtMs = 0;
    private volatile int cameraPreflightTaps = 0;
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
                // Open Roblox menu.
                svc.tap(displayId, w * 0.0604167f, h * 0.0962963f, 35);
                cameraPreflightState = CameraPreflightState.OPEN_SETTINGS;
                cameraPreflightNextAtMs = now + 350;
                status = "Camera preflight: opening settings";
                return false;

            case OPEN_SETTINGS:
                if (now < cameraPreflightNextAtMs) return false;
                // Settings tab in Roblox's mobile menu.
                svc.tap(displayId, w * 0.3229167f, h * 0.2444444f, 35);
                cameraPreflightState = CameraPreflightState.SEEK_CLASSIC;
                cameraPreflightNextAtMs = now + 500;
                status = "Camera preflight: checking camera mode";
                return false;

            case SEEK_CLASSIC:
                if (now < cameraPreflightNextAtMs) return false;
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

    private boolean isCameraClassic(Bitmap frame) {
        final int fw = frame.getWidth();
        final int fh = frame.getHeight();

        final int left = Math.round(fw * 0.609375f);
        final int top = Math.round(fh * 0.3962963f);
        final int cropW = Math.max(1, Math.round(fw * 0.125f));
        final int cropH = Math.max(1, Math.round(fh * 0.0703704f));

        int matched = 0;
        for (int ry = 0; ry < CAMERA_REF_H; ry++) {
            for (int rx = 0; rx < CAMERA_REF_W; rx++) {
                int refIndex = ry * CAMERA_REF_W + rx;
                int maskByte = CAMERA_CLASSIC_MASK[refIndex >> 3] & 0xff;
                int maskBit = 7 - (refIndex & 7);
                if (((maskByte >> maskBit) & 1) == 0) continue;

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
        }
        // Reference experiments: Classic=104/104, Follow~25/104,
        // Default(Follow)~19/104. Leave generous anti-aliasing headroom.
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
            o.put("routeStarted", routeStarted);
            routing.appendState(o);
''',
"preflight state json")

p.write_text(s)
print("PASS: installed Roblox mobile Camera Mode=Classic startup preflight")

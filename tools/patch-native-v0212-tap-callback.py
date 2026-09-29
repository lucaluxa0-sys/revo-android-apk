#!/usr/bin/env python3
from pathlib import Path

SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')
if not SERVICE.exists():
    raise SystemExit('RevoAccessibilityService.java missing')

src = SERVICE.read_text(encoding='utf-8')
marker = 'tap-callback-diagnostics-v1'
if marker in src:
    print('PASS: tap callback diagnostics already present')
    raise SystemExit(0)

old = '''    public boolean tap(int displayId, float x, float y, long durationMs) {
        Path p = new Path();
        p.moveTo(x, y);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(p, 0, Math.max(1, durationMs));
        GestureDescription gesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(stroke)
                .build();
        return dispatchGesture(gesture, null, null);
    }
'''

new = '''    /** tap-callback-diagnostics-v1 */
    public boolean tap(int displayId, float x, float y, long durationMs) {
        final long safeDuration = Math.max(1L, durationMs);
        Path p = new Path();
        p.moveTo(x, y);
        GestureDescription.StrokeDescription stroke =
                new GestureDescription.StrokeDescription(p, 0, safeDuration);
        GestureDescription gesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(stroke)
                .build();
        boolean accepted = dispatchGesture(
                gesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription completed) {
                        android.util.Log.i("RevoTap",
                                "completed=true display=" + displayId
                                        + " x=" + x + " y=" + y
                                        + " durationMs=" + safeDuration);
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoTap",
                                "cancelled=true display=" + displayId
                                        + " x=" + x + " y=" + y
                                        + " durationMs=" + safeDuration);
                    }
                },
                JOYSTICK_CALLBACK_HANDLER);
        android.util.Log.i("RevoTap",
                "accepted=" + accepted
                        + " display=" + displayId
                        + " x=" + x + " y=" + y
                        + " durationMs=" + safeDuration);
        return accepted;
    }
'''

if old not in src:
    raise SystemExit('generic tap method anchor missing')
SERVICE.write_text(src.replace(old, new, 1), encoding='utf-8')
print('PASS: instrumented generic Accessibility tap accepted/completed/cancelled callbacks')

#!/usr/bin/env python3
from pathlib import Path
import re

ROUTER = Path('revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java')
SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')

for path in (ROUTER, SERVICE):
    if not path.exists():
        raise SystemExit(f'{path.name} missing; apply the v0.2.12 native patch sequence first')


def method_span(text, name):
    m = re.search(r'(?m)^    public boolean ' + re.escape(name) + r'\s*\(', text)
    if not m:
        raise SystemExit(f'Accessibility method missing: {name}')
    brace = text.find('{', m.end())
    if brace < 0:
        raise SystemExit(f'Accessibility method opening brace missing: {name}')
    depth = 0
    in_string = False
    quote = ''
    escaped = False
    line_comment = False
    block_comment = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if line_comment:
            if ch == '\n':
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == '*' and nxt == '/':
                block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                in_string = False
            i += 1
            continue
        if ch == '/' and nxt == '/':
            line_comment = True
            i += 2
            continue
        if ch == '/' and nxt == '*':
            block_comment = True
            i += 2
            continue
        if ch in ('"', "'"):
            in_string = True
            quote = ch
            i += 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return m.start(), i + 1
        i += 1
    raise SystemExit(f'Accessibility method closing brace missing: {name}')


def replace_method(text, name, replacement):
    start, end = method_span(text, name)
    return text[:start] + replacement + text[end:]


router = ROUTER.read_text(encoding='utf-8')
old_marker = '"accessibility-joystick-touch-v1"'
if router.count(old_marker) != 1:
    raise SystemExit('router input-adaptation marker missing or duplicated')
router = router.replace(old_marker, '"accessibility-joystick-hold-v2"', 1)
ROUTER.write_text(router, encoding='utf-8')

svc = SERVICE.read_text(encoding='utf-8')
if 'joystickHoldWithTaps(' in svc:
    raise SystemExit('full-deflection joystick hold adaptation already present')

joystick = r'''    private static final long JOYSTICK_ACQUIRE_MS = 35L;

    /**
     * Android equivalent of a desktop direction-key hold.
     *
     * Accessibility StrokeDescription duration is traversal time, so using one
     * center->edge path for the requested hold duration only ramps joystick
     * strength for the whole command. Acquire full deflection quickly, keep the
     * pointer down, then continue it with a zero-motion stroke at the endpoint.
     * The requested holdMs begins at full deflection; optional tap offsets are
     * therefore relative to the same point desktop Revolution begins its hold.
     */
    private boolean joystickHoldWithTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        final long safeHold = Math.max(50L, holdMs);
        final long acquireMs = Math.max(1L, Math.min(JOYSTICK_ACQUIRE_MS, safeHold));
        final long safeTap = Math.max(1L, tapDurationMs);
        if (tapOffsetsMs != null) {
            for (long offset : tapOffsetsMs) {
                if (offset < 0 || offset + safeTap > safeHold) return false;
            }
        }

        Path acquirePath = new Path();
        acquirePath.moveTo(centerX, centerY);
        acquirePath.lineTo(targetX, targetY);
        final GestureDescription.StrokeDescription acquireStroke =
                new GestureDescription.StrokeDescription(acquirePath, 0, acquireMs, true);
        GestureDescription acquireGesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(acquireStroke)
                .build();

        return dispatchGesture(acquireGesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription completed) {
                        Path holdPath = new Path();
                        holdPath.moveTo(targetX, targetY);
                        GestureDescription.StrokeDescription heldStroke =
                                acquireStroke.continueStroke(holdPath, 0, safeHold, false);
                        GestureDescription.Builder hold = new GestureDescription.Builder()
                                .setDisplayId(displayId)
                                .addStroke(heldStroke);
                        if (tapOffsetsMs != null) {
                            for (long offset : tapOffsetsMs) {
                                Path tap = new Path();
                                tap.moveTo(tapX, tapY);
                                hold.addStroke(new GestureDescription.StrokeDescription(
                                        tap, offset, safeTap));
                            }
                        }
                        boolean accepted = dispatchGesture(hold.build(),
                                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                                    @Override public void onCompleted(GestureDescription done) {
                                        android.util.Log.i("RevoJoystickHold",
                                                "holdCompleted=true display=" + displayId
                                                        + " acquireMs=" + acquireMs
                                                        + " holdMs=" + safeHold);
                                    }
                                    @Override public void onCancelled(GestureDescription cancelled) {
                                        android.util.Log.e("RevoJoystickHold",
                                                "holdCancelled=true display=" + displayId
                                                        + " acquireMs=" + acquireMs
                                                        + " holdMs=" + safeHold);
                                    }
                                }, null);
                        android.util.Log.i("RevoJoystickHold",
                                "continuationAccepted=" + accepted
                                        + " display=" + displayId
                                        + " acquireMs=" + acquireMs
                                        + " holdMs=" + safeHold);
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "acquireCancelled=true display=" + displayId
                                        + " acquireMs=" + acquireMs
                                        + " holdMs=" + safeHold);
                    }
                }, null);
    }

    public boolean joystick(int displayId, float centerX, float centerY,
                            float targetX, float targetY, long durationMs) {
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, durationMs,
                0f, 0f, 1L, null);
    }'''

svc = replace_method(svc, 'joystick', joystick)

svc = replace_method(svc, 'joystickWithDoubleTap', r'''    public boolean joystickWithDoubleTap(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long secondTapDelayMs) {
        long safeHold = Math.max(secondTapDelayMs + tapDurationMs + 1, holdMs);
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, safeHold,
                tapX, tapY, tapDurationMs,
                new long[]{0L, Math.max(1L, secondTapDelayMs)});
    }''')

svc = replace_method(svc, 'joystickWithTimedTaps', r'''    public boolean joystickWithTimedTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, holdMs,
                tapX, tapY, tapDurationMs, tapOffsetsMs);
    }''')

SERVICE.write_text(svc, encoding='utf-8')

required = (
    'JOYSTICK_ACQUIRE_MS = 35L',
    'joystickHoldWithTaps',
    'new GestureDescription.StrokeDescription(acquirePath, 0, acquireMs, true)',
    'continueStroke(holdPath, 0, safeHold, false)',
    'continuationAccepted=',
    'holdCompleted=true',
)
missing = [item for item in required if item not in svc]
if missing:
    raise SystemExit('full-deflection joystick hold patch incomplete: ' + repr(missing))
if 'accessibility-joystick-hold-v2' not in router:
    raise SystemExit('router input-adaptation marker was not updated')

print('Patched v0.2.12 Android joystick to acquire then hold full deflection')

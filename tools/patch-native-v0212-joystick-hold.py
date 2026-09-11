#!/usr/bin/env python3
from pathlib import Path
import re

ROUTER = Path('revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java')
GATHER = Path('revo-android/app/src/main/java/com/revolution/android/RevoGatherAdapter.java')
SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')

for path in (ROUTER, GATHER, SERVICE):
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

router_busy_anchor = '''        if (now < nextActionAtMs) { lastDecision = "waiting:gesture:" + state; return false; }\n\n        switch (state) {\n'''
router_busy_replacement = '''        if (now < nextActionAtMs) { lastDecision = "waiting:gesture:" + state; return false; }\n        if (svc.joystickHoldInFlight()) {\n            lastDecision = "waiting:joystick-in-flight:" + state;\n            return false;\n        }\n\n        switch (state) {\n'''
if router.count(router_busy_anchor) != 1:
    raise SystemExit('router joystick serialization anchor missing or duplicated')
router = router.replace(router_busy_anchor, router_busy_replacement, 1)
ROUTER.write_text(router, encoding='utf-8')


gather = GATHER.read_text(encoding='utf-8')
gather_busy_anchor = '''        if (now < nextActionAtMs) { lastDecision = "waiting:step-duration"; return; }\n        if (patternStep >= c.steps.size()) { patternStep = 0; patternIteration++; }\n'''
gather_busy_replacement = '''        if (now < nextActionAtMs) { lastDecision = "waiting:step-duration"; return; }\n        if (svc.joystickHoldInFlight()) {\n            lastDecision = "waiting:joystick-in-flight";\n            nextActionAtMs = now + 25L;\n            return;\n        }\n        if (patternStep >= c.steps.size()) { patternStep = 0; patternIteration++; }\n'''
if gather.count(gather_busy_anchor) != 1:
    raise SystemExit('gather joystick serialization anchor missing or duplicated')
gather = gather.replace(gather_busy_anchor, gather_busy_replacement, 1)
GATHER.write_text(gather, encoding='utf-8')


svc = SERVICE.read_text(encoding='utf-8')
if 'joystickHoldWithTaps(' in svc:
    raise SystemExit('full-deflection joystick hold adaptation already present')

joystick = r'''    private static final long JOYSTICK_ACQUIRE_MS = 35L;
    private final java.util.concurrent.atomic.AtomicBoolean joystickHoldInFlight =
            new java.util.concurrent.atomic.AtomicBoolean(false);

    public boolean joystickHoldInFlight() {
        return joystickHoldInFlight.get();
    }

    private void failJoystickSequence(String reason, int displayId, long logicalHoldMs,
                                      long fullDeflectionMs, int tapCount) {
        joystickHoldInFlight.set(false);
        android.util.Log.e("RevoJoystickHold",
                "sequenceFailed=true reason=" + reason
                        + " display=" + displayId
                        + " holdMs=" + logicalHoldMs
                        + " fullDeflectionMs=" + fullDeflectionMs
                        + " tapCount=" + tapCount);
    }

    private void completeJoystickSequence(int displayId, long logicalHoldMs,
                                          long fullDeflectionMs, int tapCount) {
        joystickHoldInFlight.set(false);
        android.util.Log.i("RevoJoystickHold",
                "holdCompleted=true sequenceCompleted=true display=" + displayId
                        + " holdMs=" + logicalHoldMs
                        + " fullDeflectionMs=" + fullDeflectionMs
                        + " tapCount=" + tapCount);
    }

    /** Dispatch one full-deflection movement segment with no competing second pointer. */
    private boolean dispatchJoystickSegment(int displayId, float centerX, float centerY,
                                            float targetX, float targetY, long segmentMs,
                                            long logicalHoldMs, long movementDoneBeforeMs,
                                            int segmentIndex, int tapCount,
                                            Runnable onDone) {
        final long safeSegment = Math.max(1L, segmentMs);
        final long acquireMs = Math.max(1L, Math.min(JOYSTICK_ACQUIRE_MS, safeSegment));
        final long movementDoneAfterMs = movementDoneBeforeMs + safeSegment;

        Path acquirePath = new Path();
        acquirePath.moveTo(centerX, centerY);
        acquirePath.lineTo(targetX, targetY);
        final GestureDescription.StrokeDescription acquireStroke =
                new GestureDescription.StrokeDescription(acquirePath, 0, acquireMs, true);
        GestureDescription acquireGesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(acquireStroke)
                .build();

        boolean acquireAccepted = dispatchGesture(acquireGesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription completed) {
                        Path holdPath = new Path();
                        holdPath.moveTo(targetX, targetY);
                        GestureDescription.StrokeDescription heldStroke =
                                acquireStroke.continueStroke(holdPath, 0, safeSegment, false);
                        GestureDescription holdGesture = new GestureDescription.Builder()
                                .setDisplayId(displayId)
                                .addStroke(heldStroke)
                                .build();
                        boolean accepted = dispatchGesture(holdGesture,
                                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                                    @Override public void onCompleted(GestureDescription done) {
                                        android.util.Log.i("RevoJoystickHold",
                                                "segmentCompleted=true display=" + displayId
                                                        + " logicalHoldMs=" + logicalHoldMs
                                                        + " segmentIndex=" + segmentIndex
                                                        + " segmentMs=" + safeSegment
                                                        + " movementDoneMs=" + movementDoneAfterMs);
                                        onDone.run();
                                    }
                                    @Override public void onCancelled(GestureDescription cancelled) {
                                        android.util.Log.e("RevoJoystickHold",
                                                "holdCancelled=true display=" + displayId
                                                        + " logicalHoldMs=" + logicalHoldMs
                                                        + " segmentIndex=" + segmentIndex
                                                        + " segmentMs=" + safeSegment);
                                        failJoystickSequence("hold-cancelled", displayId,
                                                logicalHoldMs, movementDoneBeforeMs, tapCount);
                                    }
                                }, null);
                        android.util.Log.i("RevoJoystickHold",
                                "continuationAccepted=" + accepted
                                        + " display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment);
                        if (!accepted) {
                            failJoystickSequence("hold-dispatch-rejected", displayId,
                                    logicalHoldMs, movementDoneBeforeMs, tapCount);
                        }
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "acquireCancelled=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment);
                        failJoystickSequence("acquire-cancelled", displayId,
                                logicalHoldMs, movementDoneBeforeMs, tapCount);
                    }
                }, null);
        if (!acquireAccepted) {
            android.util.Log.e("RevoJoystickHold",
                    "acquireDispatchRejected=true display=" + displayId
                            + " logicalHoldMs=" + logicalHoldMs
                            + " segmentIndex=" + segmentIndex
                            + " segmentMs=" + safeSegment);
            failJoystickSequence("acquire-dispatch-rejected", displayId,
                    logicalHoldMs, movementDoneBeforeMs, tapCount);
        }
        return acquireAccepted;
    }

    /** Dispatch one jump tap only after the previous joystick pointer is fully up. */
    private boolean dispatchSerializedTap(int displayId, float tapX, float tapY,
                                          long tapDurationMs, int tapIndex,
                                          long offsetMs, long logicalHoldMs,
                                          long movementDoneMs, int tapCount,
                                          Runnable onDone) {
        final long safeTap = Math.max(1L, tapDurationMs);
        Path tap = new Path();
        tap.moveTo(tapX, tapY);
        GestureDescription tapGesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(new GestureDescription.StrokeDescription(tap, 0, safeTap))
                .build();
        boolean accepted = dispatchGesture(tapGesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription done) {
                        android.util.Log.i("RevoJoystickHold",
                                "tapCompleted=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " tapIndex=" + tapIndex
                                        + " offsetMs=" + offsetMs
                                        + " movementDoneMs=" + movementDoneMs);
                        onDone.run();
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "tapCancelled=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " tapIndex=" + tapIndex
                                        + " offsetMs=" + offsetMs);
                        failJoystickSequence("tap-cancelled", displayId,
                                logicalHoldMs, movementDoneMs, tapCount);
                    }
                }, null);
        android.util.Log.i("RevoJoystickHold",
                "tapAccepted=" + accepted
                        + " display=" + displayId
                        + " logicalHoldMs=" + logicalHoldMs
                        + " tapIndex=" + tapIndex
                        + " offsetMs=" + offsetMs
                        + " movementDoneMs=" + movementDoneMs);
        if (!accepted) {
            failJoystickSequence("tap-dispatch-rejected", displayId,
                    logicalHoldMs, movementDoneMs, tapCount);
        }
        return accepted;
    }

    /**
     * Continue a desktop movement/tap command without asking Android Accessibility
     * to introduce a new pointer into a continued joystick gesture. API 35 cancels
     * that mixed continuation at runtime. Instead, preserve the recovered desktop
     * movement offsets in full-deflection-distance time: complete each movement
     * segment, release, issue the jump tap, reacquire full deflection, and continue.
     * The sum of full-deflection segments remains exactly logicalHoldMs.
     */
    private boolean runJoystickTapSequence(int displayId, float centerX, float centerY,
                                           float targetX, float targetY, long logicalHoldMs,
                                           float tapX, float tapY, long tapDurationMs,
                                           long[] tapOffsetsMs, int tapIndex,
                                           long movementDoneMs, int segmentIndex) {
        final int tapCount = tapOffsetsMs == null ? 0 : tapOffsetsMs.length;
        if (tapIndex < tapCount) {
            final long offset = tapOffsetsMs[tapIndex];
            final long segmentMs = offset - movementDoneMs;
            if (segmentMs > 0) {
                return dispatchJoystickSegment(
                        displayId, centerX, centerY, targetX, targetY,
                        segmentMs, logicalHoldMs, movementDoneMs, segmentIndex, tapCount,
                        () -> runJoystickTapSequence(
                                displayId, centerX, centerY, targetX, targetY,
                                logicalHoldMs, tapX, tapY, tapDurationMs, tapOffsetsMs,
                                tapIndex, offset, segmentIndex + 1));
            }
            return dispatchSerializedTap(
                    displayId, tapX, tapY, tapDurationMs, tapIndex, offset,
                    logicalHoldMs, movementDoneMs, tapCount,
                    () -> runJoystickTapSequence(
                            displayId, centerX, centerY, targetX, targetY,
                            logicalHoldMs, tapX, tapY, tapDurationMs, tapOffsetsMs,
                            tapIndex + 1, movementDoneMs, segmentIndex));
        }

        final long remainingMs = logicalHoldMs - movementDoneMs;
        if (remainingMs <= 0) {
            completeJoystickSequence(displayId, logicalHoldMs, movementDoneMs, tapCount);
            return true;
        }
        return dispatchJoystickSegment(
                displayId, centerX, centerY, targetX, targetY,
                remainingMs, logicalHoldMs, movementDoneMs, segmentIndex, tapCount,
                () -> completeJoystickSequence(
                        displayId, logicalHoldMs, logicalHoldMs, tapCount));
    }

    /** Android equivalent of a desktop direction-key hold with optional jump taps. */
    private boolean joystickHoldWithTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        final long safeHold = Math.max(50L, holdMs);
        final long safeTap = Math.max(1L, tapDurationMs);
        long previous = -1L;
        if (tapOffsetsMs != null) {
            for (long offset : tapOffsetsMs) {
                if (offset < 0 || offset < previous || offset + safeTap > safeHold) return false;
                previous = offset;
            }
        }
        if (!joystickHoldInFlight.compareAndSet(false, true)) {
            android.util.Log.w("RevoJoystickHold",
                    "busyRejected=true display=" + displayId + " holdMs=" + safeHold);
            return false;
        }
        final int tapCount = tapOffsetsMs == null ? 0 : tapOffsetsMs.length;
        android.util.Log.i("RevoJoystickHold",
                "sequenceStarted=true display=" + displayId
                        + " holdMs=" + safeHold
                        + " tapCount=" + tapCount
                        + " tapAdaptation=serialized-between-full-deflection-segments-v1");
        boolean accepted = runJoystickTapSequence(
                displayId, centerX, centerY, targetX, targetY, safeHold,
                tapX, tapY, safeTap, tapOffsetsMs, 0, 0L, 0);
        if (!accepted && joystickHoldInFlight.get()) {
            failJoystickSequence("initial-dispatch-rejected", displayId,
                    safeHold, 0L, tapCount);
        }
        return accepted;
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

required_service = (
    'JOYSTICK_ACQUIRE_MS = 35L',
    'joystickHoldInFlight',
    'joystickHoldWithTaps',
    'runJoystickTapSequence',
    'dispatchSerializedTap',
    'new GestureDescription.StrokeDescription(acquirePath, 0, acquireMs, true)',
    'continueStroke(holdPath, 0, safeSegment, false)',
    'tapAdaptation=serialized-between-full-deflection-segments-v1',
    'sequenceCompleted=true',
    'fullDeflectionMs=',
    'continuationAccepted=',
    'holdCompleted=true',
)
missing = [item for item in required_service if item not in svc]
if missing:
    raise SystemExit('full-deflection joystick hold patch incomplete: ' + repr(missing))
if 'accessibility-joystick-hold-v2' not in router:
    raise SystemExit('router input-adaptation marker was not updated')
if 'waiting:joystick-in-flight:' not in router:
    raise SystemExit('router does not defer while a continued joystick sequence is in flight')
if 'waiting:joystick-in-flight' not in gather:
    raise SystemExit('gather does not defer while a continued joystick sequence is in flight')

print('Patched v0.2.12 Android joystick to serialize jump taps between full-deflection segments')

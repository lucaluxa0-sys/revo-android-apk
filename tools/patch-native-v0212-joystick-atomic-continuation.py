#!/usr/bin/env python3
from pathlib import Path

SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')

if not SERVICE.exists():
    raise SystemExit('RevoAccessibilityService.java missing; apply joystick hold/callback patches first')

svc = SERVICE.read_text(encoding='utf-8')

required_pre = (
    'private boolean dispatchJoystickSegment(',
    'JOYSTICK_CALLBACK_HANDLER',
    'continueStroke(holdPath, 0, safeSegment, false)',
    'callbackHandler=dedicated-handler-thread-v1',
)
missing = [item for item in required_pre if item not in svc]
if missing:
    raise SystemExit('atomic continuation prerequisites missing: ' + repr(missing))
if 'segmentDispatch=atomic-continued-strokes-v1' in svc:
    raise SystemExit('atomic joystick continuation patch already present')

start_marker = '    private boolean dispatchJoystickSegment('
end_marker = '    /** Dispatch one jump tap only after the previous joystick pointer is fully up. */'
start = svc.find(start_marker)
end = svc.find(end_marker, start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('dispatchJoystickSegment method region missing')

replacement = r'''    /**
     * Dispatch one full-deflection movement segment as a single Accessibility gesture.
     *
     * Android's MotionEventInjector can accept a continued stroke while the preceding
     * stroke is still dispatching. Keeping the acquire stroke and its continuation in
     * the same GestureDescription removes the uncontrolled inter-dispatch gap that was
     * observed on API 35 when the continuation was submitted from onCompleted().
     *
     * Logical movement remains source-faithful: JOYSTICK_ACQUIRE_MS reaches full
     * deflection, then safeSegment milliseconds are spent at the target. Jump-bearing
     * routes still release/tap/reacquire between recovered desktop movement offsets.
     */
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

        Path holdPath = new Path();
        holdPath.moveTo(targetX, targetY);
        final GestureDescription.StrokeDescription holdStroke =
                acquireStroke.continueStroke(holdPath, 0, safeSegment, false);

        GestureDescription segmentGesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(acquireStroke)
                .addStroke(holdStroke)
                .build();

        boolean accepted = dispatchGesture(segmentGesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription done) {
                        android.util.Log.i("RevoJoystickHold",
                                "segmentCompleted=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment
                                        + " movementDoneMs=" + movementDoneAfterMs
                                        + " segmentDispatch=atomic-continued-strokes-v1");
                        onDone.run();
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "holdCancelled=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment
                                        + " segmentDispatch=atomic-continued-strokes-v1");
                        failJoystickSequence("atomic-segment-cancelled", displayId,
                                logicalHoldMs, movementDoneBeforeMs, tapCount);
                    }
                }, JOYSTICK_CALLBACK_HANDLER);

        android.util.Log.i("RevoJoystickHold",
                "continuationAccepted=" + accepted
                        + " display=" + displayId
                        + " logicalHoldMs=" + logicalHoldMs
                        + " segmentIndex=" + segmentIndex
                        + " segmentMs=" + safeSegment
                        + " segmentDispatch=atomic-continued-strokes-v1");
        if (!accepted) {
            failJoystickSequence("atomic-segment-dispatch-rejected", displayId,
                    logicalHoldMs, movementDoneBeforeMs, tapCount);
        }
        return accepted;
    }

'''

svc = svc[:start] + replacement + svc[end:]

post_start = svc.find(start_marker)
post_end = svc.find(end_marker, post_start)
post_region = svc[post_start:post_end]
required_post = (
    '.addStroke(acquireStroke)',
    '.addStroke(holdStroke)',
    'acquireStroke.continueStroke(holdPath, 0, safeSegment, false)',
    'segmentDispatch=atomic-continued-strokes-v1',
    'JOYSTICK_CALLBACK_HANDLER',
)
missing = [item for item in required_post if item not in post_region]
if missing:
    raise SystemExit('atomic joystick continuation patch incomplete: ' + repr(missing))
if post_region.count('dispatchGesture(') != 1:
    raise SystemExit('dispatchJoystickSegment must contain exactly one dispatchGesture call')
if 'new GestureDescription.Builder()' not in post_region:
    raise SystemExit('atomic segment GestureDescription builder missing')

SERVICE.write_text(svc, encoding='utf-8')
print('PASS: queued joystick acquire + continued full-deflection hold in one Accessibility gesture')

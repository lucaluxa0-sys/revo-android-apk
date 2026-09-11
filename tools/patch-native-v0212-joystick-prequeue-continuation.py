#!/usr/bin/env python3
from pathlib import Path

SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')
if not SERVICE.exists():
    raise SystemExit('RevoAccessibilityService.java missing; apply joystick hold/callback patches first')

svc = SERVICE.read_text(encoding='utf-8')
if 'continuationQueue=prequeued-before-acquire-completion-v1' in svc:
    raise SystemExit('prequeued continuation patch already present')
if 'JOYSTICK_CALLBACK_HANDLER' not in svc:
    raise SystemExit('dedicated joystick callback handler missing; apply callback-thread patch first')

start_marker = '    private boolean dispatchJoystickSegment('
end_marker = '    /** Dispatch one jump tap only after the previous joystick pointer is fully up. */'
start = svc.find(start_marker)
end = svc.find(end_marker, start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('dispatchJoystickSegment region missing')

replacement = r'''    private boolean dispatchJoystickSegment(int displayId, float centerX, float centerY,
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
                        android.util.Log.i("RevoJoystickHold",
                                "acquireCompleted=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " acquireMs=" + acquireMs
                                        + " continuationQueue=prequeued-before-acquire-completion-v1");
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "acquireCancelled=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment
                                        + " continuationQueue=prequeued-before-acquire-completion-v1");
                        failJoystickSequence("acquire-cancelled", displayId,
                                logicalHoldMs, movementDoneBeforeMs, tapCount);
                    }
                }, JOYSTICK_CALLBACK_HANDLER);
        if (!acquireAccepted) {
            android.util.Log.e("RevoJoystickHold",
                    "acquireDispatchRejected=true display=" + displayId
                            + " logicalHoldMs=" + logicalHoldMs
                            + " segmentIndex=" + segmentIndex
                            + " segmentMs=" + safeSegment
                            + " continuationQueue=prequeued-before-acquire-completion-v1");
            failJoystickSequence("acquire-dispatch-rejected", displayId,
                    logicalHoldMs, movementDoneBeforeMs, tapCount);
            return false;
        }

        // Queue the valid continuation immediately. MotionEventInjector processes the
        // two dispatch requests in order while the acquisition sequence is still
        // registered, so continuation event times stay anchored to the acquisition's
        // scheduled endpoint instead of restarting from a later handler wake-up.
        Path holdPath = new Path();
        holdPath.moveTo(targetX, targetY);
        GestureDescription.StrokeDescription heldStroke =
                acquireStroke.continueStroke(holdPath, 0, safeSegment, false);
        GestureDescription holdGesture = new GestureDescription.Builder()
                .setDisplayId(displayId)
                .addStroke(heldStroke)
                .build();
        boolean continuationAccepted = dispatchGesture(holdGesture,
                new android.accessibilityservice.AccessibilityService.GestureResultCallback() {
                    @Override public void onCompleted(GestureDescription done) {
                        android.util.Log.i("RevoJoystickHold",
                                "segmentCompleted=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment
                                        + " movementDoneMs=" + movementDoneAfterMs
                                        + " continuationQueue=prequeued-before-acquire-completion-v1");
                        onDone.run();
                    }
                    @Override public void onCancelled(GestureDescription cancelled) {
                        android.util.Log.e("RevoJoystickHold",
                                "holdCancelled=true display=" + displayId
                                        + " logicalHoldMs=" + logicalHoldMs
                                        + " segmentIndex=" + segmentIndex
                                        + " segmentMs=" + safeSegment
                                        + " continuationQueue=prequeued-before-acquire-completion-v1");
                        failJoystickSequence("hold-cancelled", displayId,
                                logicalHoldMs, movementDoneBeforeMs, tapCount);
                    }
                }, JOYSTICK_CALLBACK_HANDLER);
        android.util.Log.i("RevoJoystickHold",
                "continuationAccepted=" + continuationAccepted
                        + " display=" + displayId
                        + " logicalHoldMs=" + logicalHoldMs
                        + " segmentIndex=" + segmentIndex
                        + " segmentMs=" + safeSegment
                        + " continuationQueue=prequeued-before-acquire-completion-v1");
        if (!continuationAccepted) {
            failJoystickSequence("hold-dispatch-rejected", displayId,
                    logicalHoldMs, movementDoneBeforeMs, tapCount);
        }
        return continuationAccepted;
    }

'''

svc = svc[:start] + replacement + svc[end:]
required = (
    'continuationQueue=prequeued-before-acquire-completion-v1',
    'acquireCompleted=true',
    'acquireStroke.continueStroke(holdPath, 0, safeSegment, false)',
    'continuationAccepted=',
    'JOYSTICK_CALLBACK_HANDLER',
)
missing = [item for item in required if item not in svc]
if missing:
    raise SystemExit('prequeued continuation patch incomplete: ' + repr(missing))

SERVICE.write_text(svc, encoding='utf-8')
print('PASS: prequeued v0.2.12 joystick continuation before acquisition completion')

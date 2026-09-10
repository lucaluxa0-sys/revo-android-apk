#!/usr/bin/env python3
from pathlib import Path

JAVA = Path('revo-android/app/src/main/java/com/revolution/android')
router_path = JAVA / 'RevoPreGatherRouter.java'
svc_path = JAVA / 'RevoAccessibilityService.java'

if not router_path.exists() or not svc_path.exists():
    raise SystemExit('run patch-native-v0212-hive-routing.py first')

router = router_path.read_text(encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit('field-routing patch anchor missing: ' + label)
    return text.replace(old, new, 1)

router = replace_once(
    router,
    '''        READY_AT_CANNON,
        FAILED
''',
    '''        READY_AT_CANNON,
        CANNON_ROUTE_INTERACT,
        CANNON_ROUTE_FLIGHT,
        CANNON_ROUTE_ALIGN_DIAGONAL,
        CANNON_ROUTE_ALIGN_FORWARD,
        PINE_ROUTE_YAW_2,
        PINE_ROUTE_CENTER_DIAGONAL,
        PINE_ROUTE_CENTER_LEFT,
        FIELD_READY,
        FAILED
''',
    'state enum'
)

router = replace_once(
    router,
    '''    private volatile int cannonSlotMoves = 0;
    private volatile boolean lastGestureAccepted;
''',
    '''    private volatile int cannonSlotMoves = 0;
    private volatile int currentYawSlot = 0;
    private volatile long fieldRouteActionCount = 0;
    private volatile boolean lastGestureAccepted;
''',
    'route state fields'
)

router = replace_once(
    router,
    '''        cannonSlotMoves = 0; lastGestureAccepted = false; lastAction = ""; lastError = ""; lastTemplate = ""; lastMatch = null;
''',
    '''        cannonSlotMoves = 0; currentYawSlot = 0; fieldRouteActionCount = 0;
        lastGestureAccepted = false; lastAction = ""; lastError = ""; lastTemplate = ""; lastMatch = null;
''',
    'onStart reset'
)

old_ready = '''            case READY_AT_CANNON:
                lastDecision = "blocked:field-routing-not-yet-ported:" + c.field;
                break;
'''
new_ready = r'''            case READY_AT_CANNON:
                if (!isPineTree(c.field)) return fail("unsupported field route: " + c.field);
                // v0.9c-hotfix3 datasets/v8 route "cannon.pinetree-br":
                // SetYaw(4); Sleep(300); E; hold Forward+Left; jump at
                // t=0,850,5670ms; release at 6050ms.
                if (setYaw(frame, svc, 4, 300, "desktop cannon.pinetree-br: SetYaw(4)")) {
                    transitionAfterGesture(State.CANNON_ROUTE_INTERACT);
                }
                break;
            case CANNON_ROUTE_INTERACT: {
                Match p = find(frame, "press_e", c, now);
                if (p == null) p = lastMatch;
                if (p == null || !"press_e".equals(p.name)) return fail("lost cannon Press E before route interaction");
                fieldRouteActionCount++;
                if (tapInteraction(frame, svc, c, p, "desktop cannon.pinetree-br: KeyPress(E)")) {
                    transitionAfterGesture(State.CANNON_ROUTE_FLIGHT);
                }
                break;
            }
            case CANNON_ROUTE_FLIGHT: {
                float w = frame.getWidth(), h = frame.getHeight();
                float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY);
                float r = (float)(Math.min(w, h) * c.joyR);
                float jumpX = (float)(w * c.jumpX), jumpY = (float)(h * c.jumpY);
                boolean accepted = svc.joystickWithTimedTaps(
                        displayId,
                        cx, cy, cx - r, cy - r,
                        6050,
                        jumpX, jumpY, 70,
                        new long[]{0, 850, 5670});
                fieldRouteActionCount++;
                recordGesture(accepted,
                        "desktop cannon.pinetree-br: Forward+Left 6050ms + Space@0,850,5670");
                nextActionAtMs = now + 6130;
                if (accepted) transitionKeepDeadline(State.CANNON_ROUTE_ALIGN_DIAGONAL);
                break;
            }
            case CANNON_ROUTE_ALIGN_DIAGONAL:
                // Desktop runs WalkAsync(Left,77.5) concurrently with
                // WalkAlign(Forward,110): first 77.5 studs are diagonal.
                if (moveDiagonal(frame, svc, c, Direction.FORWARD, Direction.LEFT, 77.5,
                        "desktop cannon.pinetree-br: WalkAsync Left 77.5 + WalkAlign Forward")) {
                    transitionAfterGesture(State.CANNON_ROUTE_ALIGN_FORWARD);
                }
                break;
            case CANNON_ROUTE_ALIGN_FORWARD:
                // Left async walk has ended; complete Forward 110 - 77.5.
                if (moveField(frame, svc, c, Direction.FORWARD, 32.5,
                        "desktop cannon.pinetree-br: WalkAlign Forward remainder")) {
                    transitionAfterGesture(State.PINE_ROUTE_YAW_2);
                }
                break;
            case PINE_ROUTE_YAW_2:
                // v0.9c-hotfix3 "pinetree-br.pinetree-center": SetYaw(2).
                if (setYaw(frame, svc, 2, 0, "desktop pinetree-br.pinetree-center: SetYaw(2)")) {
                    transitionAfterGesture(State.PINE_ROUTE_CENTER_DIAGONAL);
                }
                break;
            case PINE_ROUTE_CENTER_DIAGONAL:
                // Walk({[0]={Backward,Left}, [70]=Left, [90]=End})
                if (moveDiagonal(frame, svc, c, Direction.BACKWARD, Direction.LEFT, 70.0,
                        "desktop pinetree-br.pinetree-center: Backward+Left 70")) {
                    transitionAfterGesture(State.PINE_ROUTE_CENTER_LEFT);
                }
                break;
            case PINE_ROUTE_CENTER_LEFT:
                if (moveField(frame, svc, c, Direction.LEFT, 20.0,
                        "desktop pinetree-br.pinetree-center: Left 20")) {
                    transitionAfterGesture(State.FIELD_READY);
                    Log.i(TAG, "FIELD_ROUTE_READY route=cannon->pinetree-br->pinetree-center field=" + c.field);
                }
                break;
            case FIELD_READY:
                lastDecision = "ready:field:" + c.field;
                return true;
'''
router = replace_once(router, old_ready, new_ready, 'READY_AT_CANNON')

helper_anchor = '''    private void prepareNextHive() {
'''
helpers = r'''    private boolean isPineTree(String field) {
        String n = field == null ? "" : field.toLowerCase(Locale.US).replaceAll("[^a-z0-9]", "");
        return "pinetree".equals(n) || "pinetreeforest".equals(n);
    }

    /**
     * Desktop SetYaw uses eight absolute 45-degree yaw slots. Android has no
     * keyboard RotLeft/RotRight, so preserve the discrete slot semantics with
     * one calibrated camera drag per 45-degree step.
     */
    private boolean setYaw(Bitmap frame, RevoAccessibilityService svc, int target, long postDelayMs, String label) {
        target = ((target % 8) + 8) % 8;
        int right = (target - currentYawSlot + 8) % 8;
        int left = (currentYawSlot - target + 8) % 8;
        int signedSteps = right <= left ? right : -left;
        if (signedSteps == 0) {
            lastDecision = "yaw-already:" + target;
            currentYawSlot = target;
            nextActionAtMs = SystemClock.elapsedRealtime() + postDelayMs;
            return true;
        }
        long stepMs = 110, gapMs = 45;
        boolean accepted = svc.cameraYawSteps(
                displayId, frame.getWidth(), frame.getHeight(), signedSteps, stepMs, gapMs);
        fieldRouteActionCount++;
        recordGesture(accepted, label + " androidSteps=" + signedSteps);
        if (accepted) currentYawSlot = target;
        nextActionAtMs = SystemClock.elapsedRealtime()
                + Math.abs(signedSteps) * (stepMs + gapMs) + postDelayMs;
        return accepted;
    }

    private boolean moveField(Bitmap frame, RevoAccessibilityService svc, Config c,
                              Direction d, double studs, String label) {
        boolean accepted = move(frame, svc, c, d, studs, label);
        fieldRouteActionCount++;
        return accepted;
    }

    private boolean moveDiagonal(Bitmap frame, RevoAccessibilityService svc, Config c,
                                 Direction a, Direction b, double studs, String label) {
        long now = SystemClock.elapsedRealtime();
        long duration = Math.max(50, Math.min(MAX_GESTURE_MS, Math.round(studs * c.msPerStud)));
        float w = frame.getWidth(), h = frame.getHeight();
        float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY);
        float r = (float)(Math.min(w, h) * c.joyR);
        float dx = 0f, dy = 0f;
        Direction[] dirs = new Direction[]{a, b};
        for (Direction d : dirs) {
            switch (d) {
                case FORWARD: dy -= 1f; break;
                case BACKWARD: dy += 1f; break;
                case LEFT: dx -= 1f; break;
                case RIGHT: dx += 1f; break;
            }
        }
        float norm = (float)Math.max(1.0, Math.sqrt(dx * dx + dy * dy));
        float tx = cx + r * dx / norm, ty = cy + r * dy / norm;
        boolean accepted = svc.joystick(displayId, cx, cy, tx, ty, duration);
        fieldRouteActionCount++;
        recordGesture(accepted, label + String.format(Locale.US, " %.2f studs %dms", studs, duration));
        nextActionAtMs = now + duration + 80;
        return accepted;
    }

'''
router = replace_once(router, helper_anchor, helpers + helper_anchor, 'helper insertion')

router = replace_once(
    router,
    '''            r.put("source", "GPL Revolution ClaimHive+GotoCannon 3f890744b55a");
            r.put("androidInputAdaptation", "accessibility-joystick-touch-v1");
            r.put("fieldRoutingPorted", false);
''',
    '''            r.put("source", "GPL Revolution ClaimHive+GotoCannon 3f890744b55a");
            r.put("fieldRouteSource", "Revolution v0.9c-hotfix3 datasets/v8/patterns.bin");
            r.put("fieldRouteDatasetSha256", "c0a499ba9512b4282bc3f59bdf9daacedd6841b1d7a2008f90075e3d0c07859f");
            r.put("fieldRoute", "cannon->pinetree-br->pinetree-center");
            r.put("fieldRouteActionCount", fieldRouteActionCount);
            r.put("currentYawSlot", currentYawSlot);
            r.put("androidInputAdaptation", "accessibility-joystick-touch-v1");
            r.put("androidCameraYawAdaptation", "8-slot-camera-drag-v1");
            r.put("fieldRoutingPorted", true);
''',
    'routing state JSON'
)

router_path.write_text(router, encoding='utf-8')

svc = svc_path.read_text(encoding='utf-8')
svc_anchor = '''    public void screenshot(int displayId, Consumer<Bitmap> ok, Consumer<Integer> fail) {
'''
svc_methods = r'''    /**
     * Hold one joystick vector while issuing jump taps at exact offsets.
     * Used for the decoded v0.9c cannon.pinetree-br route.
     */
    public boolean joystickWithTimedTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        Path joy = new Path();
        joy.moveTo(centerX, centerY);
        joy.lineTo(targetX, targetY);
        GestureDescription.Builder b = new GestureDescription.Builder().setDisplayId(displayId);
        b.addStroke(new GestureDescription.StrokeDescription(joy, 0, Math.max(50, holdMs)));
        if (tapOffsetsMs != null) {
            for (long offset : tapOffsetsMs) {
                if (offset < 0 || offset + tapDurationMs > holdMs) return false;
                Path tap = new Path();
                tap.moveTo(tapX, tapY);
                b.addStroke(new GestureDescription.StrokeDescription(
                        tap, offset, Math.max(1, tapDurationMs)));
            }
        }
        return dispatchGesture(b.build(), null, null);
    }

    /**
     * Android adaptation of Revolution's eight-slot SetYaw controller.
     * Positive steps rotate right (finger drags left); negative rotate left.
     * Each stroke is separate so one requested desktop 45-degree step remains
     * one observable mobile camera action.
     */
    public boolean cameraYawSteps(int displayId, float width, float height,
                                  int signedSteps, long stepMs, long gapMs) {
        int count = Math.abs(signedSteps);
        if (count == 0) return true;
        float y = height * 0.43f;
        float left = width * 0.46f;
        float right = width * 0.72f;
        GestureDescription.Builder b = new GestureDescription.Builder().setDisplayId(displayId);
        for (int i = 0; i < count; i++) {
            Path p = new Path();
            if (signedSteps > 0) {
                p.moveTo(right, y);
                p.lineTo(left, y);
            } else {
                p.moveTo(left, y);
                p.lineTo(right, y);
            }
            long start = i * (Math.max(1, stepMs) + Math.max(0, gapMs));
            b.addStroke(new GestureDescription.StrokeDescription(p, start, Math.max(1, stepMs)));
        }
        return dispatchGesture(b.build(), null, null);
    }

'''
if 'public boolean joystickWithTimedTaps(' in svc:
    raise SystemExit('field-routing service methods already present')
svc = replace_once(svc, svc_anchor, svc_methods + svc_anchor, 'service method insertion')
svc_path.write_text(svc, encoding='utf-8')

print('PASS: patched v0.2.12 source-grounded cannon -> Pine Tree -> Gather handoff')

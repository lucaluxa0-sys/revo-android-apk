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
        CANNON_BLACK_BEAR_FORWARD,
        CANNON_BLACK_BEAR_RIGHT,
        BLACK_BEAR_CHECKPOINT_WALK,
        BLACK_BEAR_CHECKPOINT_DETECT,
        BLACK_BEAR_CHECKPOINT_FAILED,
        MOBILE_BLACK_BEAR_RECOVER_YAW,
        MOBILE_BLACK_BEAR_RECOVER_FORWARD_A,
        MOBILE_BLACK_BEAR_RECOVER_FORWARD_B,
        MOBILE_BLACK_BEAR_RECOVER_RIGHT,
        MOBILE_BLACK_BEAR_RECOVER_DIAGONAL,
        MOBILE_BLACK_BEAR_RECOVER_DETECT,
        SUNFLOWER_ROUTE_LEFT,
        SUNFLOWER_ROUTE_BACKWARD,
        SUNFLOWER_ROUTE_ALIGN_RIGHT,
        SUNFLOWER_ROUTE_FORWARD,
        SUNFLOWER_ROUTE_CENTER_RIGHT,
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
    private volatile int blackBearCheckpointAttempts = 0;
    private volatile int claimModalCloseAttempts = 0;
    private volatile boolean claimModalGateDone = false;
    private volatile boolean lastGestureAccepted;
''',
    'route state fields'
)

router = replace_once(
    router,
    '''        cannonSlotMoves = 0; lastGestureAccepted = false; lastAction = ""; lastError = ""; lastTemplate = ""; lastMatch = null;
''',
    '''        cannonSlotMoves = 0; currentYawSlot = 0; fieldRouteActionCount = 0;
        blackBearCheckpointAttempts = 0; claimModalCloseAttempts = 0; claimModalGateDone = false;
        lastGestureAccepted = false; lastAction = ""; lastError = ""; lastTemplate = ""; lastMatch = null;
''',
    'onStart reset'
)

# Live Android QA at yaw slot 0 wedges the avatar against the hive wall before
# the cannon route. Match the desktop route's expected approach frame by turning
# the camera 180 degrees (four 45-degree slots) once after a successful claim.
router = replace_once(
    router,
    '''            case CLAIMED:
                if (claimedHive <= 0) return fail("invalid claimed hive");
                Log.i(TAG, "Claimed Hive: " + claimedHive);
                if (move(frame, svc, c, Direction.FORWARD, 12.0, "desktop GotoCannon: Forward 12")) {
                    cannonSlotMoves = 0;
                    transitionAfterGesture(State.CANNON_FORWARD);
                }
                break;
''',
    '''            case CLAIMED:
                if (claimedHive <= 0) return fail("invalid claimed hive");
                Log.i(TAG, "Claimed Hive: " + claimedHive);

                // Bee Swarm mobile can open the claimed bee's detail panel from the
                // same interaction used to claim a hive. That modal intercepts the
                // movement, so never leave the hive until the panel is visibly gone.
                if (!claimModalGateDone) {
                    if (closeBeeModalIfPresent(frame, svc, now, "before-yaw")) break;
                    if (claimModalCloseAttempts == 0 && elapsedState(now) < 1600) {
                        lastDecision = "waiting:claim-modal-before-cannon-move";
                        break;
                    }
                    claimModalGateDone = true;
                    lastDecision = "claim-modal-clear-before-cannon-move";
                }

                // Mobile spawns facing the hive wall. Back away from the hive
                // without rotating the camera, so the subsequent Right leg stays
                // on the cannon side of the hive row.
                if (move(frame, svc, c, Direction.BACKWARD, 12.0, "mobile GotoCannon: Backward 12 (preserve world-right)")) {
                    cannonSlotMoves = 0;
                    transitionAfterGesture(State.CANNON_FORWARD);
                }
                break;
''',
    'mobile cannon approach backward'
)

# Bee-detail panels can also be opened by later mobile camera/movement gestures.
# Re-check before every cannon-phase action so a panel never survives long enough
# to intercept camera input or cover the Press-E detector.
router = replace_once(
    router,
    """            case CANNON_FORWARD:
                if (cannonSlotMoves >= claimedHive) { transition(State.CANNON_DOUBLE_JUMP, "cannon-slot-offset-complete"); break; }
""",
    """            case CANNON_FORWARD:
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-forward")) break;
                if (cannonSlotMoves >= claimedHive) { transition(State.CANNON_DOUBLE_JUMP, "cannon-slot-offset-complete"); break; }
""",
    'cannon forward modal guard'
)
router = replace_once(
    router,
    """            case CANNON_SLOT_RIGHT:
                transition(State.CANNON_FORWARD, "cannon-slot-step-complete");
""",
    """            case CANNON_SLOT_RIGHT:
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-slot-right")) break;
                transition(State.CANNON_FORWARD, "cannon-slot-step-complete");
""",
    'cannon slot modal guard'
)
router = replace_once(
    router,
    """            case CANNON_DOUBLE_JUMP: {
                float w = frame.getWidth(), h = frame.getHeight();
""",
    """            case CANNON_DOUBLE_JUMP: {
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-double-jump")) break;
                float w = frame.getWidth(), h = frame.getHeight();
""",
    'cannon jump modal guard'
)
router = replace_once(
    router,
    """            case CANNON_SEEK_PROMPT: {
                Match p = find(frame, "press_e", c, now);
""",
    """            case CANNON_SEEK_PROMPT: {
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-seek-prompt")) break;
                Match p = find(frame, "press_e", c, now);
""",
    'cannon seek modal guard'
)

# Sunflower does not actually require firing the Red Cannon. On accounts that
# have fewer than 25 discovered bee types, the cannon prompt cannot exist. Keep
# the normal cannon search untouched first; only after its timeout, use the
# proven nearby Black Bear mobile Tap prompt as the anchor for the already-ported
# black-bear.sunflower-tr edge.
router = replace_once(
    router,
    """            case CANNON_SEEK_PROMPT: {
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-seek-prompt")) break;
                Match p = find(frame, "press_e", c, now);
                if (p != null) {
                    lastMatch = p;
                    transition(State.READY_AT_CANNON, "desktop PressEImage found");
                    Log.i(TAG, "Reached cannon prompt; field routing is the next unported desktop layer");
                    break;
                }
                moveMobileProbe(frame, svc, c, Direction.RIGHT, CANNON_SEEK_CHUNK_STUDS, 170, "desktop GotoCannon: continue Right seeking Press E");
                if (elapsedState(now) > CANNON_SEEK_TIMEOUT_MS) return fail("failed to goto cannon prompt");
                break;
            }
""",
    """            case CANNON_SEEK_PROMPT: {
                if (closeBeeModalIfPresent(frame, svc, now, "cannon-seek-prompt")) break;

                // Preserve normal cannon behavior for the full desktop search window.
                // If no cannon prompt can exist, the proven Android endpoint is already
                // beside Black Bear. Seek his mobile Tap banner with small forward probes.
                if (isSunflower(c.field) && elapsedState(now) > CANNON_SEEK_TIMEOUT_MS) {
                    if (beginSunflowerFromMobileBlackBear(frame, svc,
                            "mobile sunflower fallback: direct Black Bear Tap")) break;

                    blackBearCheckpointAttempts++;
                    if (blackBearCheckpointAttempts <= 4) {
                        moveMobileProbe(frame, svc, c, Direction.FORWARD, 1.25, 170,
                                "mobile sunflower fallback: direct seek Black Bear Tap attempt " + blackBearCheckpointAttempts);
                        break;
                    }

                    // Live QA can land hard against the brown wall beside Black Bear.
                    // Stop pushing into it and run the calibrated local recovery.
                    blackBearCheckpointAttempts = 0;
                    transition(State.MOBILE_BLACK_BEAR_RECOVER_YAW,
                            "mobile Black Bear wall recovery");
                    break;
                }

                Match p = find(frame, "press_e", c, now);
                if (p != null) {
                    lastMatch = p;
                    transition(State.READY_AT_CANNON, "desktop PressEImage found");
                    Log.i(TAG, "Reached cannon prompt; field routing is the next unported desktop layer");
                    break;
                }
                moveMobileProbe(frame, svc, c, Direction.RIGHT, CANNON_SEEK_CHUNK_STUDS, 170, "desktop GotoCannon: continue Right seeking Press E");
                if (elapsedState(now) > CANNON_SEEK_TIMEOUT_MS) return fail("failed to goto cannon prompt");
                break;
            }
""",
    'sunflower mobile Black Bear fallback'
)

old_ready = '''            case READY_AT_CANNON:
                lastDecision = "blocked:field-routing-not-yet-ported:" + c.field;
                break;
'''
new_ready = r'''            case READY_AT_CANNON:
                if (isSunflower(c.field)) {
                    blackBearCheckpointAttempts = 0;
                    // Exact v0.9c-hotfix3 edge 118 cannon.black-bear begins at yaw slot 2.
                    if (setYaw(frame, svc, 2, 300, "desktop cannon.black-bear: SetYaw(2)")) {
                        transitionAfterGesture(State.CANNON_BLACK_BEAR_FORWARD);
                    }
                    break;
                }
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
            case CANNON_BLACK_BEAR_FORWARD:
                // Walk({[0]=Forward,[30]=Right,[80]=End}) => Forward 30, then Right 50.
                if (moveField(frame, svc, c, Direction.FORWARD, 30.0,
                        "desktop cannon.black-bear: Walk Forward 30")) {
                    transitionAfterGesture(State.CANNON_BLACK_BEAR_RIGHT);
                }
                break;
            case CANNON_BLACK_BEAR_RIGHT:
                if (moveField(frame, svc, c, Direction.RIGHT, 50.0,
                        "desktop cannon.black-bear: Walk Right 50")) {
                    transitionAfterGesture(State.BLACK_BEAR_CHECKPOINT_WALK);
                }
                break;
            case BLACK_BEAR_CHECKPOINT_WALK:
                if (moveField(frame, svc, c, Direction.BACKWARD, 10.0,
                        "desktop cannon.black-bear Checkpoint WalkDetector interaction: Backward 10")) {
                    transitionAfterGesture(State.BLACK_BEAR_CHECKPOINT_DETECT);
                }
                break;
            case BLACK_BEAR_CHECKPOINT_DETECT: {
                Match p = find(frame, "press_e", c, now);
                if (p != null) {
                    lastMatch = p;
                    if (setYaw(frame, svc, 0, 0, "desktop black-bear.sunflower-tr: SetYaw(0)")) {
                        transitionAfterGesture(State.SUNFLOWER_ROUTE_LEFT);
                    }
                    break;
                }
                blackBearCheckpointAttempts++;
                if (moveField(frame, svc, c, Direction.BACKWARD, 5.0,
                        "desktop cannon.black-bear Checkpoint Nudge Backward 5 attempt " + blackBearCheckpointAttempts)) {
                    if (blackBearCheckpointAttempts >= 3) {
                        transitionAfterGesture(State.BLACK_BEAR_CHECKPOINT_FAILED);
                    } else {
                        transitionAfterGesture(State.BLACK_BEAR_CHECKPOINT_DETECT);
                    }
                }
                break;
            }
            case BLACK_BEAR_CHECKPOINT_FAILED:
                return fail("desktop cannon.black-bear checkpoint interaction failed after 3 attempts");
            case MOBILE_BLACK_BEAR_RECOVER_YAW:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: prompt before yaw")) break;
                // Two rightward 45-degree camera slots reproduced the manual wall
                // recovery and exposed Black Bear's blue platform.
                if (setYaw(frame, svc, 2, 300,
                        "mobile Black Bear recovery: SetYaw(2)")) {
                    transitionAfterGesture(State.MOBILE_BLACK_BEAR_RECOVER_FORWARD_A);
                }
                break;
            case MOBILE_BLACK_BEAR_RECOVER_FORWARD_A:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: prompt after forward A")) break;
                if (moveField(frame, svc, c, Direction.FORWARD, 12.0,
                        "mobile Black Bear recovery: Forward 12")) {
                    transitionAfterGesture(State.MOBILE_BLACK_BEAR_RECOVER_FORWARD_B);
                }
                break;
            case MOBILE_BLACK_BEAR_RECOVER_FORWARD_B:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: prompt after forward B")) break;
                if (moveField(frame, svc, c, Direction.FORWARD, 13.0,
                        "mobile Black Bear recovery: Forward 13")) {
                    transitionAfterGesture(State.MOBILE_BLACK_BEAR_RECOVER_RIGHT);
                }
                break;
            case MOBILE_BLACK_BEAR_RECOVER_RIGHT:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: prompt after right")) break;
                if (moveField(frame, svc, c, Direction.RIGHT, 8.0,
                        "mobile Black Bear recovery: Right 8")) {
                    transitionAfterGesture(State.MOBILE_BLACK_BEAR_RECOVER_DIAGONAL);
                }
                break;
            case MOBILE_BLACK_BEAR_RECOVER_DIAGONAL:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: prompt before diagonal")) break;
                if (moveDiagonal(frame, svc, c, Direction.FORWARD, Direction.RIGHT, 10.0,
                        "mobile Black Bear recovery: Forward+Right 10")) {
                    transitionAfterGesture(State.MOBILE_BLACK_BEAR_RECOVER_DETECT);
                }
                break;
            case MOBILE_BLACK_BEAR_RECOVER_DETECT:
                if (beginSunflowerFromMobileBlackBear(frame, svc,
                        "mobile Black Bear recovery: final prompt")) break;
                return fail("mobile Black Bear wall recovery prompt not found");
            case SUNFLOWER_ROUTE_LEFT:
                if (moveField(frame, svc, c, Direction.LEFT, 30.0,
                        "desktop black-bear.sunflower-tr: Walk Left 30")) {
                    transitionAfterGesture(State.SUNFLOWER_ROUTE_BACKWARD);
                }
                break;
            case SUNFLOWER_ROUTE_BACKWARD:
                if (moveField(frame, svc, c, Direction.BACKWARD, 70.0,
                        "desktop black-bear.sunflower-tr: Walk Backward 70")) {
                    transitionAfterGesture(State.SUNFLOWER_ROUTE_ALIGN_RIGHT);
                }
                break;
            case SUNFLOWER_ROUTE_ALIGN_RIGHT:
                // Exact edge 59 command is WalkAlign(Right,35), not Left.
                if (moveField(frame, svc, c, Direction.RIGHT, 35.0,
                        "desktop black-bear.sunflower-tr: WalkAlign Right 35")) {
                    transitionAfterGesture(State.SUNFLOWER_ROUTE_FORWARD);
                }
                break;
            case SUNFLOWER_ROUTE_FORWARD:
                if (moveField(frame, svc, c, Direction.FORWARD, 40.0,
                        "desktop black-bear.sunflower-tr: Walk Forward 40")) {
                    transitionAfterGesture(State.SUNFLOWER_ROUTE_CENTER_RIGHT);
                }
                break;
            case SUNFLOWER_ROUTE_CENTER_RIGHT:
                // Real-field WGC on the corrected Black Bear route shows the e_lol
                // cycle anchor still lands on bare grass, while its first Left 10 step
                // lands back on Sunflower tiles. Shift that proven 10-stud correction
                // into the route anchor and keep the desktop 2x8 pattern unchanged.
                if (moveField(frame, svc, c, Direction.LEFT, 37.0,
                        "mobile sunflower: center Left 37 before gather")) {
                    transitionAfterGesture(State.FIELD_READY);
                    Log.i(TAG, "FIELD_ROUTE_READY route=black-bear->sunflower-tr->mobile-center-left37 field=" + c.field);
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

    private boolean isSunflower(String field) {
        String n = field == null ? "" : field.toLowerCase(Locale.US).replaceAll("[^a-z0-9]", "");
        return "sunflower".equals(n) || "sunflowerfield".equals(n);
    }

    private static final int[] MOBILE_BLACK_BEAR_TEXT_X =
            new int[]{463, 428, 469, 504, 519, 544, 504};
    private static final int[] MOBILE_BLACK_BEAR_TEXT_Y =
            new int[]{109, 118, 120, 120, 123, 126, 127};

    private boolean isMobileBlackBearPrompt(Bitmap frame) {
        if (!isMobileTapPrompt(frame)) return false;

        int fw = frame.getWidth(), fh = frame.getHeight();
        float sx = fw / 960.0f, sy = fh / 540.0f;
        int radius = Math.max(1, Math.round(Math.min(sx, sy) * 2.0f));
        int matched = 0;

        for (int i = 0; i < MOBILE_BLACK_BEAR_TEXT_X.length; i++) {
            int cx = Math.max(0, Math.min(fw - 1, Math.round(MOBILE_BLACK_BEAR_TEXT_X[i] * sx)));
            int cy = Math.max(0, Math.min(fh - 1, Math.round(MOBILE_BLACK_BEAR_TEXT_Y[i] * sy)));
            boolean found = false;
            for (int yy = Math.max(0, cy - radius); yy <= Math.min(fh - 1, cy + radius) && !found; yy++) {
                for (int xx = Math.max(0, cx - radius); xx <= Math.min(fw - 1, cx + radius); xx++) {
                    int p = frame.getPixel(xx, yy);
                    int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
                    int hi=Math.max(r,Math.max(g,b)), lo=Math.min(r,Math.min(g,b));
                    if (lo >= 205 && hi - lo <= 38) {
                        found = true;
                        break;
                    }
                }
            }
            if (found) matched++;
        }

        // Saved 960x540 QA: real "Talk to Black Bear" = 7/7.
        // Claim Hive, Make Honey, occupied-hive and live Send Trade Request = 0/7.
        return matched >= 5;
    }

    private boolean beginSunflowerFromMobileBlackBear(Bitmap frame,
                                                       RevoAccessibilityService svc,
                                                       String label) {
        if (!isMobileBlackBearPrompt(frame)) return false;
        lastTemplate = "mobile-black-bear";
        blackBearCheckpointAttempts = 0;
        if (setYaw(frame, svc, 0, 0, label + " -> SetYaw(0)")) {
            transitionAfterGesture(State.SUNFLOWER_ROUTE_LEFT);
        }
        return true;
    }

    // Locate the Bee detail modal by color structure instead of one fixed pixel.
    // The panel shifts vertically between Android UI states, but it consistently
    // has a red close square immediately left of a wide yellow title strip.
    private float[] findClaimBeeModalClose(Bitmap frame) {
        int w = frame.getWidth(), h = frame.getHeight();
        int x0 = Math.max(0, Math.round(w * 0.24f));
        int x1 = Math.min(w - 1, Math.round(w * 0.54f));
        int y0 = Math.max(0, Math.round(h * 0.07f));
        int y1 = Math.min(h - 1, Math.round(h * 0.34f));

        for (int y = y0; y <= y1; y += 3) {
            for (int x = x0; x <= x1; x += 3) {
                int p = frame.getPixel(x, y);
                int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
                boolean red = r >= 175 && g <= 120 && b <= 115 && r - g >= 65;
                if (!red) continue;

                // The true Bee detail close square has its yellow title bar
                // immediately to the right on the same horizontal band. A broad
                // top-center trade banner can sit over yellow hive scenery and
                // fooled the old "10 yellow pixels anywhere nearby" check.
                int yellow = 0, titleSamples = 0;
                int yTop = Math.max(y0, y - 12), yBottom = Math.min(y1, y + 12);
                int xLeft = Math.min(w - 1, x + 25), xRight = Math.min(w - 1, x + 245);
                for (int yy = yTop; yy <= yBottom; yy += 3) {
                    for (int xx = xLeft; xx <= xRight; xx += 3) {
                        int q = frame.getPixel(xx, yy);
                        int qr=(q>>16)&255, qg=(q>>8)&255, qb=q&255;
                        titleSamples++;
                        if (qr >= 205 && qg >= 165 && qb <= 155 && qr - qb >= 55) yellow++;
                    }
                }
                if (titleSamples == 0 || ((float)yellow / (float)titleSamples) < 0.35f) continue;

                int minX=x, maxX=x, minY=y, maxY=y, redCount=0;
                int sx0=Math.max(x0, x-35), sx1=Math.min(x1, x+55);
                int sy0=Math.max(y0, y-35), sy1=Math.min(y1, y+55);
                for (int yy=sy0; yy<=sy1; yy++) {
                    for (int xx=sx0; xx<=sx1; xx++) {
                        int q=frame.getPixel(xx,yy);
                        int qr=(q>>16)&255, qg=(q>>8)&255, qb=q&255;
                        if (qr >= 175 && qg <= 120 && qb <= 115 && qr - qg >= 65) {
                            minX=Math.min(minX,xx); maxX=Math.max(maxX,xx);
                            minY=Math.min(minY,yy); maxY=Math.max(maxY,yy);
                            redCount++;
                        }
                    }
                }
                int boxW = maxX - minX + 1, boxH = maxY - minY + 1;
                if (redCount >= 400 && boxW >= 20 && boxW <= 60 && boxH >= 20 && boxH <= 60) {
                    return new float[]{(minX+maxX)*0.5f, (minY+maxY)*0.5f};
                }
            }
        }
        return null;
    }

    private boolean closeBeeModalIfPresent(Bitmap frame, RevoAccessibilityService svc, long now, String phase) {
        float[] close = findClaimBeeModalClose(frame);
        if (close == null) return false;
        if (claimModalCloseAttempts >= 8) {
            fail("bee detail modal would not stay closed during cannon route");
            return true;
        }
        float closeX = close[0], closeY = close[1];
        boolean accepted = svc.tap(displayId, closeX, closeY, 80);
        claimModalCloseAttempts++;
        recordGesture(accepted, String.format(Locale.US,
                "mobile bee modal close phase=%s attempt=%d tap=(%.1f,%.1f)",
                phase, claimModalCloseAttempts, closeX, closeY));
        lastDecision = "closing-bee-modal:" + phase;
        nextActionAtMs = now + 450;
        return true;
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
            r.put("fieldRoute", c != null && isSunflower(c.field)
                    ? "cannon->black-bear->sunflower-tr"
                    : "cannon->pinetree-br->pinetree-center");
            r.put("fieldRouteActionCount", fieldRouteActionCount);
            r.put("blackBearCheckpointAttempts", blackBearCheckpointAttempts);
            r.put("currentYawSlot", currentYawSlot);
            r.put("claimModalCloseAttempts", claimModalCloseAttempts);
            r.put("claimModalGateDone", claimModalGateDone);
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

# Android 15 can occasionally drop an Accessibility screenshot consumer without
# invoking either callback (the API 35 emulator logged "ScreenCaptureListenerWrapper
# consumer not alive"). MacroEngine's in-flight latch would then remain set forever.
# Recover only that no-callback case; normal frame cadence and normal error handling
# remain unchanged. A generation token prevents a late abandoned callback from
# racing the replacement request.
macro_path = JAVA / 'MacroEngine.java'
if not macro_path.exists():
    raise SystemExit('reconstructed MacroEngine.java missing')

macro = macro_path.read_text(encoding='utf-8')
if 'CAPTURE_CALLBACK_TIMEOUT_MS' in macro:
    raise SystemExit('capture watchdog already present')

macro = replace_once(
    macro,
    '''    private final AtomicBoolean captureInFlight = new AtomicBoolean(false);
''',
    '''    private final AtomicBoolean captureInFlight = new AtomicBoolean(false);
    private final AtomicLong captureGeneration = new AtomicLong(0);
    private static final long CAPTURE_CALLBACK_TIMEOUT_MS = 2_000L;
    private volatile long captureStartedAtMs = 0;
''',
    'capture watchdog fields'
)

macro = replace_once(
    macro,
    '''        captureInFlight.set(false);
        status = "Stopped";
''',
    '''        captureGeneration.incrementAndGet();
        captureStartedAtMs = 0;
        captureInFlight.set(false);
        status = "Stopped";
''',
    'capture stop invalidation'
)

macro = replace_once(
    macro,
    '''        if (!captureInFlight.compareAndSet(false, true)) return;

        svc.screenshot(displayId, frame -> {
            try {
''',
    '''        long captureNowMs = SystemClock.elapsedRealtime();
        if (captureInFlight.get()) {
            long ageMs = captureStartedAtMs > 0
                    ? Math.max(0L, captureNowMs - captureStartedAtMs)
                    : CAPTURE_CALLBACK_TIMEOUT_MS;
            if (ageMs < CAPTURE_CALLBACK_TIMEOUT_MS) return;
            long abandonedGeneration = captureGeneration.incrementAndGet();
            captureStartedAtMs = 0;
            captureInFlight.set(false);
            lastError = "Screenshot callback timeout";
            android.util.Log.w("RevoCapture",
                    "watchdog recovered stalled screenshot display=" + displayId
                            + " ageMs=" + ageMs
                            + " generation=" + abandonedGeneration);
        }
        if (!captureInFlight.compareAndSet(false, true)) return;
        final long captureToken = captureGeneration.incrementAndGet();
        captureStartedAtMs = captureNowMs;

        svc.screenshot(displayId, frame -> {
            if (captureGeneration.get() != captureToken) {
                if (frame != null && !frame.isRecycled()) frame.recycle();
                return;
            }
            lastError = "";
            try {
''',
    'capture request watchdog'
)

macro = replace_once(
    macro,
    '''            } finally {
                captureInFlight.set(false);
            }
        }, errorCode -> {
            lastError = "Screenshot error " + errorCode;
            captureInFlight.set(false);
        });
''',
    '''            } finally {
                if (captureGeneration.get() == captureToken) {
                    captureStartedAtMs = 0;
                    captureInFlight.set(false);
                }
            }
        }, errorCode -> {
            if (captureGeneration.get() != captureToken) return;
            lastError = "Screenshot error " + errorCode;
            captureStartedAtMs = 0;
            captureInFlight.set(false);
        });
''',
    'capture callback generation guard'
)

macro = replace_once(
    macro,
    '''            o.put("lastError", lastError);
''',
    '''            o.put("lastError", lastError);
            o.put("captureInFlight", captureInFlight.get());
            o.put("captureAgeMs",
                    captureInFlight.get() && captureStartedAtMs > 0
                            ? Math.max(0L, SystemClock.elapsedRealtime() - captureStartedAtMs)
                            : 0L);
            o.put("captureGeneration", captureGeneration.get());
''',
    'capture watchdog diagnostics'
)
macro_path.write_text(macro, encoding='utf-8')

print('PASS: patched v0.2.12 source-grounded cannon -> Pine Tree/Sunflower -> Gather handoff + screenshot callback watchdog')

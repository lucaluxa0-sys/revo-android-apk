#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java")
s = p.read_text(encoding="utf-8")

MARKER = "v09c-edge203-hive3-cannon-low-v1"
if MARKER in s:
    raise SystemExit("v0.9c hive3 cannon patch already applied")

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit("v09c hive3 cannon anchor missing: " + label)
    s = s.replace(old, new, 1)

once(
"""        CLAIMED,
        CANNON_FORWARD,
""",
"""        CLAIMED,
        V09C_H3_BACK_2,
        V09C_H3_PARACHUTE_JUMP_1,
        V09C_H3_PARACHUTE_GLIDE_RIGHT,
        V09C_H3_RIGHT_4,
        V09C_H3_JUMP_CANNON_RIGHT_20,
        V09C_H3_JUMP_CANNON_RIGHT_8,
        V09C_H3_JUMP_CANNON_DIAG_6,
        V09C_H3_CANNON_PROBE,
        CANNON_FORWARD,
""",
"state enum")

once(
"""    private volatile int cannonSlotMoves = 0;
    private volatile int currentYawSlot = 0;
""",
"""    private volatile int cannonSlotMoves = 0;
    private volatile double v09cCannonProbeStuds = 0.0;
    private volatile int currentYawSlot = 0;
""",
"route fields")

once(
"""        cannonSlotMoves = 0; currentYawSlot = 0; fieldRouteActionCount = 0;
""",
"""        cannonSlotMoves = 0; v09cCannonProbeStuds = 0.0; currentYawSlot = 0; fieldRouteActionCount = 0;
""",
"onStart reset")

claimed_anchor = """                // Mobile spawns facing the hive wall. Back away from the hive
                // without rotating the camera, so the subsequent Right leg stays
                // on the cannon side of the hive row.
                if (move(frame, svc, c, Direction.BACKWARD, 12.0, "mobile GotoCannon: Backward 12 (preserve world-right)")) {
                    cannonSlotMoves = 0;
                    transitionAfterGesture(State.CANNON_FORWARD);
                }
                break;
"""
claimed_new = """                // Narrow source-grounded v0.9c-hotfix3 route edge 203:
                // hive3 -> cannon. The desktop edge begins Forward20, Back2.
                // Live Android QA established that the claimed-hive mobile camera
                // faces the opposite forward axis here (desktop Forward12 wedged
                // into the hive wall), so preserve the edge's world displacement
                // by mapping only this initial Forward/Backward pair accordingly.
                if (isSunflower(c.field) && claimedHive == 3) {
                    Log.i(TAG, "routeMarker=""" + MARKER + """ edge=203 alignment=low");
                    if (move(frame, svc, c, Direction.BACKWARD, 20.0,
                            "v0.9c edge203 Forward20 -> mobile Backward20")) {
                        v09cCannonProbeStuds = 0.0;
                        transitionAfterGesture(State.V09C_H3_BACK_2);
                    }
                    break;
                }

                // Existing generic route remains unchanged for every other field/hive.
                // Mobile spawns facing the hive wall. Back away from the hive
                // without rotating the camera, so the subsequent Right leg stays
                // on the cannon side of the hive row.
                if (move(frame, svc, c, Direction.BACKWARD, 12.0, "mobile GotoCannon: Backward 12 (preserve world-right)")) {
                    cannonSlotMoves = 0;
                    transitionAfterGesture(State.CANNON_FORWARD);
                }
                break;
"""
once(claimed_anchor, claimed_new, "CLAIMED branch")

cases = r'''            case V09C_H3_BACK_2:
                // Desktop edge203 Backward2 under the same claimed-hive mobile
                // orientation adaptation used for Forward20 above.
                if (move(frame, svc, c, Direction.FORWARD, 2.0,
                        "v0.9c edge203 Back2 -> mobile Forward2")) {
                    transitionAfterGesture(State.V09C_H3_PARACHUTE_JUMP_1);
                }
                break;
            case V09C_H3_PARACHUTE_JUMP_1: {
                // Exact simple Parachute(Direction.Right) timing recovered from
                // v0.9c-hotfix3 RevolutionMacro.exe:
                // Space down 100ms; second jump begins ~400ms after the first.
                float jumpX = (float)(frame.getWidth() * c.jumpX);
                float jumpY = (float)(frame.getHeight() * c.jumpY);
                boolean accepted = svc.tap(displayId, jumpX, jumpY, 100);
                recordGesture(accepted,
                        "v0.9c edge203 Parachute(Right): first Space 100ms");
                if (accepted) {
                    transitionDelay(State.V09C_H3_PARACHUTE_GLIDE_RIGHT, 400);
                } else {
                    nextActionAtMs = now + 180;
                }
                break;
            }
            case V09C_H3_PARACHUTE_GLIDE_RIGHT: {
                // At the second jump, Right begins and remains held through the
                // recovered ~750ms parachute glide. Android needs 35ms to acquire
                // the joystick; joystickWithTimedTaps deliberately fires the jump
                // immediately after that acquisition.
                float w = frame.getWidth(), h = frame.getHeight();
                float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY);
                float r = (float)(Math.min(w, h) * c.joyR);
                float jumpX = (float)(w * c.jumpX), jumpY = (float)(h * c.jumpY);
                boolean accepted = svc.joystickWithTimedTaps(
                        displayId, cx, cy, cx + r, cy,
                        850, jumpX, jumpY, 100, new long[]{0L});
                recordGesture(accepted,
                        "v0.9c edge203 Parachute(Right): second Space + Right glide 850ms");
                nextActionAtMs = now + 930;
                if (accepted) transitionKeepDeadline(State.V09C_H3_RIGHT_4);
                break;
            }
            case V09C_H3_RIGHT_4:
                if (move(frame, svc, c, Direction.RIGHT, 4.0,
                        "v0.9c edge203 low alignment: Walk Right 4")) {
                    transitionAfterGesture(State.V09C_H3_JUMP_CANNON_RIGHT_20);
                }
                break;
            case V09C_H3_JUMP_CANNON_RIGHT_20:
                // jump_cannon.lua: KeyDown(Right); SleepStuds(20)
                if (move(frame, svc, c, Direction.RIGHT, 20.0,
                        "v0.9c jump_cannon: Right 20")) {
                    transitionAfterGesture(State.V09C_H3_JUMP_CANNON_RIGHT_8);
                }
                break;
            case V09C_H3_JUMP_CANNON_RIGHT_8: {
                // jump_cannon.lua: Space 100ms, then continue Right for 8 studs.
                long duration = RevoMovementSpeed.durationMs(
                        8.0, c.baseMoveSpeed, c.msPerStud,
                        c.hasteStacks, c.hastePlus, c.coconutHaste, c.bearMorph, c.oil, c.superSmoothie,
                        MAX_GESTURE_MS);
                float w = frame.getWidth(), h = frame.getHeight();
                float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY);
                float r = (float)(Math.min(w, h) * c.joyR);
                float jumpX = (float)(w * c.jumpX), jumpY = (float)(h * c.jumpY);
                boolean accepted = svc.joystickWithTimedTaps(
                        displayId, cx, cy, cx + r, cy,
                        Math.max(180L, duration),
                        jumpX, jumpY, 100, new long[]{0L});
                recordGesture(accepted,
                        "v0.9c jump_cannon: Space100 + Right8 duration=" + duration + "ms");
                nextActionAtMs = now + Math.max(180L, duration) + 80L;
                if (accepted) transitionKeepDeadline(State.V09C_H3_JUMP_CANNON_DIAG_6);
                break;
            }
            case V09C_H3_JUMP_CANNON_DIAG_6:
                // jump_cannon.lua adds Forward for 6 studs while Right remains held.
                // Android cannot mutate one continuous joystick stroke in-place, so
                // preserve the geometry with a single Forward+Right diagonal segment.
                if (moveDiagonal(frame, svc, c, Direction.FORWARD, Direction.RIGHT, 6.0,
                        "v0.9c jump_cannon: Forward+Right 6")) {
                    v09cCannonProbeStuds = 0.0;
                    transitionAfterGesture(State.V09C_H3_CANNON_PROBE);
                }
                break;
            case V09C_H3_CANNON_PROBE: {
                // Android currently has the interaction template rather than the
                // desktop red_cannon/hive_side detector pair. Prefer a real Press-E
                // detection. On locked-cannon accounts, perform only a short bounded
                // source-direction probe; WGC QA decides whether this endpoint is kept.
                Match p = find(frame, "press_e", c, now);
                if (p != null) {
                    lastMatch = p;
                    transition(State.READY_AT_CANNON,
                            "v0.9c edge203 cannon interaction detected");
                    break;
                }
                if (v09cCannonProbeStuds < 8.0) {
                    if (moveMobileProbe(frame, svc, c, Direction.RIGHT, 1.0, 170,
                            "v0.9c jump_cannon: bounded Right detector probe")) {
                        v09cCannonProbeStuds += 1.0;
                    }
                    break;
                }
                Log.i(TAG, "routeMarker=v09c-edge203-hive3-cannon-low-v1"
                        + " promptAbsent=true boundedProbeStuds=" + v09cCannonProbeStuds);
                transition(State.READY_AT_CANNON,
                        "v0.9c edge203 bounded cannon endpoint; Press E unavailable");
                break;
            }
'''
once(
"""            case CANNON_FORWARD:
""",
cases + """            case CANNON_FORWARD:
""",
"insert edge203 states")

once(
"""            r.put("fieldRouteSource", "Revolution v0.9c-hotfix3 datasets/v8/patterns.bin");
""",
"""            r.put("v09cHive3CannonRoute", "v09c-edge203-hive3-cannon-low-v1");
            r.put("v09cCannonProbeStuds", v09cCannonProbeStuds);
            r.put("fieldRouteSource", "Revolution v0.9c-hotfix3 datasets/v8/patterns.bin");
""",
"state diagnostics")

p.write_text(s, encoding="utf-8")
print("PASS: installed " + MARKER)

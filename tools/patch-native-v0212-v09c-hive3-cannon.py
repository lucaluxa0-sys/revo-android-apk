#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java")
s = p.read_text(encoding="utf-8")

MARKER = "v09c-hive234-sunflower-no-parachute-v5-edge202-backward"
if MARKER in s:
    raise SystemExit("v0.9c hive3/hive4 cannon patch already applied")

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit("v09c hive3/hive4 cannon anchor missing: " + label)
    s = s.replace(old, new, 1)

once(
"""        CLAIMED,
        CANNON_FORWARD,
""",
"""        CLAIMED,
        V09C_H2_SPAWN_FORWARD_25,
        V09C_H2_TICKET_YAW_4,
        V09C_H2_TICKET_FORWARD_20,
        V09C_H2_TICKET_RIGHT_10,
        V09C_H2_TICKET_FORWARD_80,
        V09C_H2_TICKET_LEFT_10,
        V09C_H2_SUNFLOWER_YAW_4,
        V09C_H2_SUNFLOWER_LEFT_71,
        V09C_H2_SUNFLOWER_DIAG_71,
        V09C_H2_SUNFLOWER_ALIGN_LEFT_30,
        V09C_H2_SUNFLOWER_ALIGN_BACKWARD_30,
        V09C_H3_BACK_2,
        V09C_H3_ALIGN_RIGHT_80,
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
claimed_new = """                // This account has no parachute and the generic cannon fallback was
                // visually disproven for hive2. Use the shortest decoded v0.9c path
                // that contains neither a cannon node nor Parachute():
                // edge202 hive2->spawn, edge406 spawn->ticket, edge468 ticket->sunflower-tr.
                if (isSunflower(c.field) && claimedHive == 2) {
                    Log.i(TAG, "routeMarker=""" + MARKER + """ edges=202,406,468 cannon=disabled parachute=disabled");
                    // edge202 Medium: WalkAsync(Left,50) concurrently with Walk(Backward,75).
                    // Live WGC from hive2 showed the prior mobile Forward mapping drove directly
                    // into the hive honeycomb wall. Preserve desktop Backward for hive2
                    // while keeping the decoded horizontal Left component unchanged.
                    if (moveDiagonal(frame, svc, c, Direction.BACKWARD, Direction.LEFT, 50.0,
                            "v0.9c edge202 Medium: desktop Backward+Left50 -> mobile Backward+Left50")) {
                        transitionAfterGesture(State.V09C_H2_SPAWN_FORWARD_25);
                    }
                    break;
                }

                // Narrow source-grounded v0.9c-hotfix3 routes:
                // edge203 hive3 -> cannon and edge205 hive4 -> cannon.
                // Both desktop edges begin Forward20, Back2.
                // Live Android QA established that the claimed-hive mobile camera
                // faces the opposite forward axis here (desktop Forward12 wedged
                // into the hive wall), so preserve the edge's world displacement
                // by mapping only this initial Forward/Backward pair accordingly.
                if (isSunflower(c.field) && (claimedHive == 3 || claimedHive == 4)) {
                    int v09cEdge = claimedHive == 4 ? 205 : 203;
                    Log.i(TAG, "routeMarker=""" + MARKER + """ edge=" + v09cEdge
                            + " alignment=medium parachute=disabled");
                    if (move(frame, svc, c, Direction.BACKWARD, 20.0,
                            "v0.9c hive3/4 Forward20 -> mobile Backward20")) {
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

cases = r'''            case V09C_H2_SPAWN_FORWARD_25:
                // Finish edge202 Medium Backward75 after the concurrent first 50 studs.
                // Keep the same hive2 vertical mapping verified by the first edge202 leg.
                if (move(frame, svc, c, Direction.BACKWARD, 25.0,
                        "v0.9c edge202 Medium: desktop Backward remainder25 -> mobile Backward25")) {
                    transitionAfterGesture(State.V09C_H2_TICKET_YAW_4);
                }
                break;
            case V09C_H2_TICKET_YAW_4:
                // edge406 spawn.ticket
                if (setYaw(frame, svc, 4, 0, "v0.9c edge406 spawn.ticket: SetYaw(4)")) {
                    transitionAfterGesture(State.V09C_H2_TICKET_FORWARD_20);
                }
                break;
            case V09C_H2_TICKET_FORWARD_20:
                // Walk({[0]=Forward,[20]=Right,[30]=Forward,[110]=Left,[120]=End})
                if (moveField(frame, svc, c, Direction.FORWARD, 20.0,
                        "v0.9c edge406: Forward20")) {
                    transitionAfterGesture(State.V09C_H2_TICKET_RIGHT_10);
                }
                break;
            case V09C_H2_TICKET_RIGHT_10:
                if (moveField(frame, svc, c, Direction.RIGHT, 10.0,
                        "v0.9c edge406: Right10")) {
                    transitionAfterGesture(State.V09C_H2_TICKET_FORWARD_80);
                }
                break;
            case V09C_H2_TICKET_FORWARD_80:
                if (moveField(frame, svc, c, Direction.FORWARD, 80.0,
                        "v0.9c edge406: Forward80")) {
                    transitionAfterGesture(State.V09C_H2_TICKET_LEFT_10);
                }
                break;
            case V09C_H2_TICKET_LEFT_10:
                if (moveField(frame, svc, c, Direction.LEFT, 10.0,
                        "v0.9c edge406: Left10")) {
                    transitionAfterGesture(State.V09C_H2_SUNFLOWER_YAW_4);
                }
                break;
            case V09C_H2_SUNFLOWER_YAW_4:
                // edge468 ticket.sunflower-tr
                if (setYaw(frame, svc, 4, 0, "v0.9c edge468 ticket.sunflower-tr: SetYaw(4)")) {
                    transitionAfterGesture(State.V09C_H2_SUNFLOWER_LEFT_71);
                }
                break;
            case V09C_H2_SUNFLOWER_LEFT_71:
                // Walk({[0]=Left,[71]={Backward,Left},[142]=End})
                if (moveField(frame, svc, c, Direction.LEFT, 71.0,
                        "v0.9c edge468: Left71")) {
                    transitionAfterGesture(State.V09C_H2_SUNFLOWER_DIAG_71);
                }
                break;
            case V09C_H2_SUNFLOWER_DIAG_71:
                if (moveDiagonal(frame, svc, c, Direction.BACKWARD, Direction.LEFT, 71.0,
                        "v0.9c edge468: Backward+Left71")) {
                    transitionAfterGesture(State.V09C_H2_SUNFLOWER_ALIGN_LEFT_30);
                }
                break;
            case V09C_H2_SUNFLOWER_ALIGN_LEFT_30:
                // Walk({[0]={Left,Align},[30]={Backward,Align},[60]=End}).
                // Existing Android routes port WalkAlign as directional motion with
                // route timing, so preserve that same convention here.
                if (moveField(frame, svc, c, Direction.LEFT, 30.0,
                        "v0.9c edge468: WalkAlign Left30")) {
                    transitionAfterGesture(State.V09C_H2_SUNFLOWER_ALIGN_BACKWARD_30);
                }
                break;
            case V09C_H2_SUNFLOWER_ALIGN_BACKWARD_30:
                if (moveField(frame, svc, c, Direction.BACKWARD, 30.0,
                        "v0.9c edge468: WalkAlign Backward30")) {
                    // edge468 ends at sunflower-tr. Reuse the existing visually
                    // established mobile center correction before e_lol starts.
                    transitionAfterGesture(State.SUNFLOWER_ROUTE_CENTER_RIGHT);
                    Log.i(TAG, "DIRECT_FIELD_ROUTE_REACHED endpoint=sunflower-tr edges=202,406,468");
                }
                break;
            case V09C_H3_BACK_2:

                // Desktop edge203 Backward2 under the same claimed-hive mobile
                // orientation adaptation used for Forward20 above.
                if (move(frame, svc, c, Direction.FORWARD, 2.0,
                        "v0.9c edge203 Back2 -> mobile Forward2")) {
                    transitionAfterGesture(State.V09C_H3_ALIGN_RIGHT_80);
                }
                break;
            case V09C_H3_ALIGN_RIGHT_80: {
                // This account has no parachute. Use Revolution v0.9c's original
                // non-parachute ExecuteWithAlignment Medium branch. Decoded AST:
                // edge203 hive3 = 38*2+4 = Right80; edge205 hive4 = 38*3+4 = Right118.
                // Their Low branches require Parachute(Right), so they are intentionally
                // not used on this account.
                double v09cAlignStuds = claimedHive == 4 ? 118.0 : 80.0;
                int v09cEdge = claimedHive == 4 ? 205 : 203;
                if (move(frame, svc, c, Direction.RIGHT, v09cAlignStuds,
                        "v0.9c edge" + v09cEdge + " Medium alignment: Right"
                                + v09cAlignStuds + " (parachute disabled)")) {
                    transitionAfterGesture(State.V09C_H3_JUMP_CANNON_RIGHT_20);
                }
                break;
            }
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
                            "v0.9c hive3/4 cannon interaction detected");
                    break;
                }
                if (v09cCannonProbeStuds < 8.0) {
                    if (moveMobileProbe(frame, svc, c, Direction.RIGHT, 1.0, 170,
                            "v0.9c jump_cannon: bounded Right detector probe")) {
                        v09cCannonProbeStuds += 1.0;
                    }
                    break;
                }
                Log.i(TAG, "routeMarker=v09c-hive234-sunflower-no-parachute-v5-edge202-backward"
                        + " promptAbsent=true boundedProbeStuds=" + v09cCannonProbeStuds);
                transition(State.READY_AT_CANNON,
                        "v0.9c hive3/4 bounded cannon endpoint; Press E unavailable");
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
"""            r.put("v09cHive3CannonRoute", "v09c-hive234-sunflower-no-parachute-v5-edge202-backward");
            r.put("v09cHive2DirectRoute", "edges202-406-468:no-cannon:no-parachute");
            r.put("v09cCannonProbeStuds", v09cCannonProbeStuds);
            r.put("fieldRouteSource", "Revolution v0.9c-hotfix3 datasets/v8/patterns.bin");
""",
"state diagnostics")

p.write_text(s, encoding="utf-8")
print("PASS: installed " + MARKER)


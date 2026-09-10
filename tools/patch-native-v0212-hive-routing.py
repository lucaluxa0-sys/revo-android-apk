#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path('revo-android')
JAVA = ROOT / 'app/src/main/java/com/revolution/android'
ASSETS = ROOT / 'app/src/main/assets/revo-routing'
THIRD = Path('third_party/revolution-2025-gpl')

macro_path = JAVA / 'MacroEngine.java'
svc_path = JAVA / 'RevoAccessibilityService.java'
if not macro_path.exists() or not svc_path.exists():
    raise SystemExit('reconstructed Android source missing')
if not (THIRD / 'macro/routines/hive/claim_hive.go').exists():
    raise SystemExit('GPL Revolution source snapshot missing')

ASSETS.mkdir(parents=True, exist_ok=True)
for rel in [
    'bitmaps/hive/claimhive.png',
    'bitmaps/hive/sendtrade.png',
    'bitmaps/hive/tradedisabled.png',
    'bitmaps/hive/tradelocked.png',
    'bitmaps/interact/press_e.png',
]:
    src = THIRD / rel
    if not src.exists():
        raise SystemExit(f'missing recovered Revolution asset: {rel}')
    shutil.copy2(src, ASSETS / Path(rel).name)

router = r'''package com.revolution.android;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.SystemClock;
import android.util.Log;

import org.json.JSONObject;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Android adaptation of Revolution's GPL-3.0 ClaimHive + GotoCannon routines.
 *
 * Desktop source provenance:
 *   third_party/revolution-2025-gpl/macro/routines/hive/claim_hive.go
 *   third_party/revolution-2025-gpl/macro/routines/hive/goto_cannon.go
 *   third_party/revolution-2025-gpl/macro/routines/hive/images.go
 *
 * Source-grounded geometry/state transitions are preserved. Desktop keyboard
 * holds / E / Space are adapted to Android Accessibility joystick/touch input.
 * Field routing after the cannon is deliberately NOT faked here: this adapter
 * blocks Gather at READY_AT_CANNON until the real field-routing layer is ported.
 */
final class RevoPreGatherRouter {
    private static final String TAG = "RevoPreGatherRouter";
    private static final double DEFAULT_MS_PER_STUD = 62.5; // Android calibration, not desktop MoveSpeed detector.
    private static final long FRAME_SEARCH_INTERVAL_MS = 120;
    private static final long MAX_GESTURE_MS = 10_000;
    private static final double SEEK_CHUNK_STUDS = 1.25;
    private static final double SWEEP_CHUNK_STUDS = 0.85;
    private static final double CANNON_SEEK_CHUNK_STUDS = 0.85;
    private static final long SLOT_TIMEOUT_MS = 7_500;
    private static final long HIVE_SEEK_TIMEOUT_MS = 45_000;
    private static final long CANNON_SEEK_TIMEOUT_MS = 8_000;

    private enum Direction { FORWARD, BACKWARD, LEFT, RIGHT }
    private enum State {
        STOPPED,
        WAIT_ROBLOX,
        SEEK_HIVE_UI,
        BACK_OFF_INITIAL,
        CHECK_CENTER_HIVE,
        CLAIM_CENTER_WAIT,
        SWEEP_PREPARE,
        SWEEP_LEAVE_CURRENT,
        SWEEP_FIND_NEXT,
        CLAIM_SWEEP_WAIT,
        CLAIMED,
        CANNON_FORWARD,
        CANNON_SLOT_RIGHT,
        CANNON_DOUBLE_JUMP,
        CANNON_SEEK_PROMPT,
        READY_AT_CANNON,
        FAILED
    }

    private static final class Config {
        final String account;
        final String field;
        final double msPerStud;
        final double joyX, joyY, joyR;
        final double jumpX, jumpY;
        final double interactOffsetX, interactOffsetY;
        final int templateVariation;
        final boolean requireRoblox;
        Config(String account, String field, double msPerStud,
               double joyX, double joyY, double joyR,
               double jumpX, double jumpY,
               double interactOffsetX, double interactOffsetY,
               int templateVariation, boolean requireRoblox) {
            this.account = account; this.field = field; this.msPerStud = msPerStud;
            this.joyX = joyX; this.joyY = joyY; this.joyR = joyR;
            this.jumpX = jumpX; this.jumpY = jumpY;
            this.interactOffsetX = interactOffsetX; this.interactOffsetY = interactOffsetY;
            this.templateVariation = templateVariation; this.requireRoblox = requireRoblox;
        }
    }

    private static final class Template {
        final String name;
        final int width, height;
        final int[] pixels;
        final int[] opaqueIndexes;
        Template(String name, Bitmap bitmap) {
            this.name = name; width = bitmap.getWidth(); height = bitmap.getHeight();
            pixels = new int[width * height];
            bitmap.getPixels(pixels, 0, width, 0, 0, width, height);
            List<Integer> idx = new ArrayList<>();
            for (int i = 0; i < pixels.length; i++) if (((pixels[i] >>> 24) & 0xff) != 0) idx.add(i);
            opaqueIndexes = new int[idx.size()];
            for (int i = 0; i < idx.size(); i++) opaqueIndexes[i] = idx.get(i);
        }
    }

    private static final class Match {
        final String name; final int x, y, width, height;
        Match(String name, int x, int y, int width, int height) {
            this.name = name; this.x = x; this.y = y; this.width = width; this.height = height;
        }
        float centerX() { return x + width / 2f; }
        float centerY() { return y + height / 2f; }
    }

    private final int displayId;
    private final Map<String, Template> templates = new HashMap<>();
    private volatile Config config;
    private volatile State state = State.STOPPED;
    private volatile long stateSinceMs, nextActionAtMs, lastSearchAtMs, actionCount;
    private volatile int claimedHive = -1, checkingHive = 3, checkedHives = 0, checkDirection = -1, checkSkip = 0;
    private volatile int cannonSlotMoves = 0;
    private volatile boolean lastGestureAccepted;
    private volatile String lastDecision = "stopped", lastAction = "", lastError = "", lastTemplate = "";
    private volatile Match lastMatch;

    RevoPreGatherRouter(int displayId) { this.displayId = displayId; }

    synchronized void configure(String json) {
        try {
            JSONObject o = new JSONObject(json == null ? "{}" : json);
            double msPerStud = positiveOr(o.optDouble("msPerStud", 0), DEFAULT_MS_PER_STUD);
            config = new Config(
                    o.optString("account", "Default"),
                    o.optString("field", ""),
                    msPerStud,
                    ratioOr(o.optDouble("joystickCenterX", 0), 0.16),
                    ratioOr(o.optDouble("joystickCenterY", 0), 0.78),
                    ratioOr(o.optDouble("joystickRadius", 0), 0.085),
                    ratioOr(o.optDouble("jumpX", 0), 0.88),
                    ratioOr(o.optDouble("jumpY", 0), 0.78),
                    o.optDouble("interactionOffsetX", 0),
                    o.optDouble("interactionOffsetY", 0),
                    Math.max(0, Math.min(64, o.optInt("routingTemplateVariation", 12))),
                    o.optBoolean("requireRobloxForeground", true));
            lastDecision = "configured";
        } catch (Throwable t) {
            config = null;
            lastError = t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage());
            state = State.FAILED;
            lastDecision = "configure-failed";
        }
    }

    synchronized void onStart() {
        state = State.WAIT_ROBLOX;
        stateSinceMs = SystemClock.elapsedRealtime();
        nextActionAtMs = 0; lastSearchAtMs = 0; actionCount = 0;
        claimedHive = -1; checkingHive = 3; checkedHives = 0; checkDirection = -1; checkSkip = 0;
        cannonSlotMoves = 0; lastGestureAccepted = false; lastAction = ""; lastError = ""; lastTemplate = ""; lastMatch = null;
        lastDecision = "waiting:roblox";
        Log.i(TAG, "start source=GPL-Revolution-ClaimHive+GotoCannon androidAdaptation=v1");
    }

    void onPause(boolean paused) { if (paused) lastDecision = "paused"; }
    synchronized void onStop() { state = State.STOPPED; lastDecision = "stopped"; }

    /** Returns true only when a future field-router has actually put the player in the configured field. */
    boolean onFrame(Bitmap frame) {
        Config c = config;
        if (c == null) { lastDecision = "waiting:not-configured"; return false; }
        RevoAccessibilityService svc = RevoAccessibilityService.get();
        if (svc == null) { lastDecision = "waiting:accessibility"; return false; }
        if (c.requireRoblox && !svc.isRobloxForeground()) {
            lastDecision = "waiting:roblox-foreground:" + svc.activePackageName();
            return false;
        }
        ensureTemplates(svc);
        long now = SystemClock.elapsedRealtime();
        if (state == State.WAIT_ROBLOX) transition(State.SEEK_HIVE_UI, "roblox-foreground");
        if (now < nextActionAtMs) { lastDecision = "waiting:gesture:" + state; return false; }

        switch (state) {
            case SEEK_HIVE_UI: {
                if (elapsedState(now) > HIVE_SEEK_TIMEOUT_MS) return fail("timed out seeking hive UI");
                Match m = findAnyHive(frame, c, now);
                if (m != null) {
                    lastMatch = m;
                    if (move(frame, svc, c, Direction.BACKWARD, 2.0, "desktop ClaimHive: Backward 2")) {
                        transitionAfterGesture(State.BACK_OFF_INITIAL);
                    }
                } else {
                    move(frame, svc, c, Direction.FORWARD, SEEK_CHUNK_STUDS, "desktop ClaimHive: hold Forward (chunked Android)");
                }
                break;
            }
            case BACK_OFF_INITIAL:
                transition(State.CHECK_CENTER_HIVE, "backed-off-2");
                break;
            case CHECK_CENTER_HIVE: {
                Match claim = find(frame, "claimhive", c, now);
                if (claim != null) {
                    claimedHive = 3; lastMatch = claim;
                    if (tapInteraction(frame, svc, c, claim, "desktop KeyPress(E): claim center hive")) {
                        transitionDelay(State.CLAIM_CENTER_WAIT, 450);
                    }
                } else {
                    checkDirection = -1; checkedHives = 1; checkingHive = 3; checkSkip = 0;
                    transition(State.SWEEP_PREPARE, "center-hive-occupied");
                }
                break;
            }
            case CLAIM_CENTER_WAIT:
                if (move(frame, svc, c, Direction.BACKWARD, 4.0, "desktop ClaimHive center: Backward 4")) {
                    transitionAfterGesture(State.CLAIMED);
                }
                break;
            case SWEEP_PREPARE:
                if (claimedHive > 0) { transition(State.CLAIMED, "claimed-during-sweep"); break; }
                if (checkedHives >= 6) return fail("failed to claim hive after checking six slots");
                prepareNextHive();
                transition(State.SWEEP_LEAVE_CURRENT, "checking-hive-" + checkingHive);
                break;
            case SWEEP_LEAVE_CURRENT: {
                Match any = findAnyHive(frame, c, now);
                if (any == null) {
                    transition(State.SWEEP_FIND_NEXT, "left-current-hive-ui");
                } else {
                    move(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, "desktop MoveToNextHive: leave current prompt");
                }
                if (elapsedState(now) > SLOT_TIMEOUT_MS) return fail("timed out leaving hive " + checkingHive);
                break;
            }
            case SWEEP_FIND_NEXT: {
                Match prompt = findAny(frame, new String[]{"claimhive","sendtrade","tradedisabled","tradelocked"}, c, now);
                if (prompt != null && "claimhive".equals(prompt.name)) {
                    claimedHive = checkingHive; lastMatch = prompt;
                    if (tapInteraction(frame, svc, c, prompt, "desktop KeyPress(E): claim swept hive " + checkingHive)) {
                        transitionDelay(State.CLAIM_SWEEP_WAIT, 450);
                    }
                    break;
                }
                if (prompt != null) {
                    finishOccupiedHive();
                    transitionDelay(State.SWEEP_PREPARE, 100);
                    break;
                }
                move(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, "desktop MoveToNextHive: seek next prompt");
                if (elapsedState(now) > SLOT_TIMEOUT_MS) return fail("timed out seeking hive prompt " + checkingHive);
                break;
            }
            case CLAIM_SWEEP_WAIT:
                transition(State.CLAIMED, "claimed-hive-" + claimedHive);
                break;
            case CLAIMED:
                if (claimedHive <= 0) return fail("invalid claimed hive");
                Log.i(TAG, "Claimed Hive: " + claimedHive);
                if (move(frame, svc, c, Direction.FORWARD, 12.0, "desktop GotoCannon: Forward 12")) {
                    cannonSlotMoves = 0;
                    transitionAfterGesture(State.CANNON_FORWARD);
                }
                break;
            case CANNON_FORWARD:
                if (cannonSlotMoves >= claimedHive) { transition(State.CANNON_DOUBLE_JUMP, "cannon-slot-offset-complete"); break; }
                if (move(frame, svc, c, Direction.RIGHT, 37.0, "desktop GotoCannon: Right 37 slot " + (cannonSlotMoves + 1))) {
                    cannonSlotMoves++;
                    transitionAfterGesture(State.CANNON_SLOT_RIGHT);
                }
                break;
            case CANNON_SLOT_RIGHT:
                transition(State.CANNON_FORWARD, "cannon-slot-step-complete");
                break;
            case CANNON_DOUBLE_JUMP: {
                float w = frame.getWidth(), h = frame.getHeight();
                float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY);
                float r = (float)(Math.min(w, h) * c.joyR);
                float jumpX = (float)(w * c.jumpX), jumpY = (float)(h * c.jumpY);
                boolean accepted = svc.joystickWithDoubleTap(displayId, cx, cy, cx + r, cy,
                        1650, jumpX, jumpY, 70, 1300);
                recordGesture(accepted, "desktop GotoCannon: hold Right + Space, 1300ms, Space");
                nextActionAtMs = now + 1750;
                transitionKeepDeadline(State.CANNON_SEEK_PROMPT);
                break;
            }
            case CANNON_SEEK_PROMPT: {
                Match p = find(frame, "press_e", c, now);
                if (p != null) {
                    lastMatch = p;
                    transition(State.READY_AT_CANNON, "desktop PressEImage found");
                    Log.i(TAG, "Reached cannon prompt; field routing is the next unported desktop layer");
                    break;
                }
                move(frame, svc, c, Direction.RIGHT, CANNON_SEEK_CHUNK_STUDS, "desktop GotoCannon: continue Right seeking Press E");
                if (elapsedState(now) > CANNON_SEEK_TIMEOUT_MS) return fail("failed to goto cannon prompt");
                break;
            }
            case READY_AT_CANNON:
                lastDecision = "blocked:field-routing-not-yet-ported:" + c.field;
                break;
            case FAILED:
            case STOPPED:
            default:
                break;
        }
        return false;
    }

    private void prepareNextHive() {
        if (checkingHive == 1 && checkDirection == -1) {
            checkDirection = 1;
            checkSkip = checkedHives;
        }
        if (checkDirection == 1) checkingHive++;
        else checkingHive--;
    }

    private Direction sweepDirection() { return checkDirection == 1 ? Direction.LEFT : Direction.RIGHT; }

    private void finishOccupiedHive() {
        if (checkSkip == 0) checkedHives++;
        else checkSkip--;
    }

    private boolean move(Bitmap frame, RevoAccessibilityService svc, Config c, Direction d, double studs, String label) {
        long now = SystemClock.elapsedRealtime();
        long duration = Math.max(50, Math.min(MAX_GESTURE_MS, Math.round(studs * c.msPerStud)));
        float w = frame.getWidth(), h = frame.getHeight();
        float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY), r = (float)(Math.min(w, h) * c.joyR);
        float tx = cx, ty = cy;
        switch (d) {
            case FORWARD: ty -= r; break;
            case BACKWARD: ty += r; break;
            case LEFT: tx -= r; break;
            case RIGHT: tx += r; break;
        }
        boolean accepted = svc.joystick(displayId, cx, cy, tx, ty, duration);
        recordGesture(accepted, label + String.format(Locale.US, " %.2f studs %dms", studs, duration));
        nextActionAtMs = now + duration + 80;
        return accepted;
    }

    private boolean tapInteraction(Bitmap frame, RevoAccessibilityService svc, Config c, Match m, String label) {
        float x = (float)(m.centerX() + frame.getWidth() * c.interactOffsetX);
        float y = (float)(m.centerY() + frame.getHeight() * c.interactOffsetY);
        x = Math.max(1, Math.min(frame.getWidth() - 2, x));
        y = Math.max(1, Math.min(frame.getHeight() - 2, y));
        boolean accepted = svc.tap(displayId, x, y, 80);
        recordGesture(accepted, label + String.format(Locale.US, " tap=(%.1f,%.1f)", x, y));
        nextActionAtMs = SystemClock.elapsedRealtime() + 180;
        return accepted;
    }

    private void recordGesture(boolean accepted, String label) {
        lastGestureAccepted = accepted; actionCount++; lastAction = label;
        lastDecision = accepted ? "dispatched:" + state : "dispatch-rejected:" + state;
        if (!accepted) lastError = "Accessibility rejected gesture at " + state;
        Log.i(TAG, "action state=" + state + " accepted=" + accepted + " " + label);
    }

    private Match findAnyHive(Bitmap frame, Config c, long now) {
        return findAny(frame, new String[]{"claimhive","sendtrade","tradelocked","tradedisabled"}, c, now);
    }

    private Match find(Bitmap frame, String name, Config c, long now) { return findAny(frame, new String[]{name}, c, now); }

    private Match findAny(Bitmap frame, String[] names, Config c, long now) {
        if (now - lastSearchAtMs < FRAME_SEARCH_INTERVAL_MS) return null;
        lastSearchAtMs = now;
        int fw = frame.getWidth(), fh = frame.getHeight();
        int[] fp = new int[fw * fh];
        frame.getPixels(fp, 0, fw, 0, 0, fw, fh);
        for (String n : names) {
            Template t = templates.get(n);
            if (t == null || t.opaqueIndexes.length == 0 || t.width > fw || t.height > fh) continue;
            Match m = match(fp, fw, fh, t, c.templateVariation);
            if (m != null) {
                lastTemplate = n; lastMatch = m;
                Log.i(TAG, "template=" + n + " at=" + m.x + "," + m.y + " variation=" + c.templateVariation);
                return m;
            }
        }
        return null;
    }

    private static Match match(int[] frame, int fw, int fh, Template t, int variation) {
        int first = t.opaqueIndexes[0], fx = first % t.width, fy = first / t.width, expected = t.pixels[first];
        int maxX = fw - t.width, maxY = fh - t.height;
        for (int y = 0; y <= maxY; y++) {
            int row = (y + fy) * fw;
            for (int x = 0; x <= maxX; x++) {
                if (!rgbClose(frame[row + x + fx], expected, variation)) continue;
                boolean ok = true;
                for (int idx : t.opaqueIndexes) {
                    int tx = idx % t.width, ty = idx / t.width;
                    if (!rgbClose(frame[(y + ty) * fw + x + tx], t.pixels[idx], variation)) { ok = false; break; }
                }
                if (ok) return new Match(t.name, x, y, t.width, t.height);
            }
        }
        return null;
    }

    private static boolean rgbClose(int a, int b, int v) {
        return Math.abs(((a >> 16) & 255) - ((b >> 16) & 255)) <= v
                && Math.abs(((a >> 8) & 255) - ((b >> 8) & 255)) <= v
                && Math.abs((a & 255) - (b & 255)) <= v;
    }

    private void ensureTemplates(RevoAccessibilityService svc) {
        if (!templates.isEmpty()) return;
        synchronized (templates) {
            if (!templates.isEmpty()) return;
            load(svc, "claimhive"); load(svc, "sendtrade"); load(svc, "tradedisabled"); load(svc, "tradelocked"); load(svc, "press_e");
        }
    }

    private void load(RevoAccessibilityService svc, String name) {
        try (InputStream in = svc.getAssets().open("revo-routing/" + name + ".png")) {
            Bitmap b = BitmapFactory.decodeStream(in);
            if (b == null) throw new IllegalStateException("decode returned null");
            templates.put(name, new Template(name, b));
            b.recycle();
        } catch (Throwable t) {
            lastError = "template " + name + ": " + t.getMessage();
            Log.e(TAG, lastError, t);
        }
    }

    private void transition(State next, String why) {
        state = next; stateSinceMs = SystemClock.elapsedRealtime(); lastDecision = "state:" + next + ":" + why;
        Log.i(TAG, "state=" + next + " why=" + why);
    }
    private void transitionDelay(State next, long delayMs) { transition(next, "delay"); nextActionAtMs = SystemClock.elapsedRealtime() + delayMs; }
    private void transitionAfterGesture(State next) { long deadline = nextActionAtMs; transition(next, "gesture-dispatched"); nextActionAtMs = deadline; }
    private void transitionKeepDeadline(State next) { long deadline = nextActionAtMs; transition(next, "gesture-dispatched"); nextActionAtMs = deadline; }
    private long elapsedState(long now) { return Math.max(0, now - stateSinceMs); }
    private boolean fail(String message) {
        lastError = message; transition(State.FAILED, message); Log.e(TAG, message); return false;
    }

    void appendState(JSONObject o) {
        try {
            Config c = config;
            JSONObject r = new JSONObject();
            r.put("state", state.name());
            r.put("claimedHive", claimedHive);
            r.put("checkingHive", checkingHive);
            r.put("checkedHives", checkedHives);
            r.put("checkDirection", checkDirection);
            r.put("cannonSlotMoves", cannonSlotMoves);
            r.put("field", c == null ? "" : c.field);
            r.put("actionCount", actionCount);
            r.put("lastDecision", lastDecision);
            r.put("lastAction", lastAction);
            r.put("lastGestureAccepted", lastGestureAccepted);
            r.put("lastTemplate", lastTemplate);
            r.put("lastError", lastError);
            r.put("source", "GPL Revolution ClaimHive+GotoCannon 3f890744b55a");
            r.put("androidInputAdaptation", "accessibility-joystick-touch-v1");
            r.put("fieldRoutingPorted", false);
            if (lastMatch != null) {
                r.put("matchX", lastMatch.x); r.put("matchY", lastMatch.y);
                r.put("matchWidth", lastMatch.width); r.put("matchHeight", lastMatch.height);
            }
            o.put("routing", r);
        } catch (Throwable ignored) {}
    }

    private static double positiveOr(double v, double fallback) { return Double.isFinite(v) && v > 0 ? v : fallback; }
    private static double ratioOr(double v, double fallback) { return Double.isFinite(v) && v > 0 && v < 1 ? v : fallback; }
}
'''
(JAVA / 'RevoPreGatherRouter.java').write_text(router, encoding='utf-8')

macro = macro_path.read_text(encoding='utf-8')
repls = [
    ('    private final RevoGatherAdapter gather;\n', '    private final RevoPreGatherRouter routing;\n    private final RevoGatherAdapter gather;\n'),
    ('        this.displayId = displayId;\n        this.gather = new RevoGatherAdapter(displayId);\n', '        this.displayId = displayId;\n        this.routing = new RevoPreGatherRouter(displayId);\n        this.gather = new RevoGatherAdapter(displayId);\n'),
    ('    public synchronized String configure(String json) {\n        gather.configure(json);\n        return stateJson();\n    }\n', '    public synchronized String configure(String json) {\n        routing.configure(json);\n        gather.configure(json);\n        return stateJson();\n    }\n'),
    ('        gather.onStart();\n        status = "Starting";\n', '        routing.onStart();\n        gather.onStart();\n        status = "Starting";\n'),
    ('        gather.onPause(next);\n', '        routing.onPause(next);\n        gather.onPause(next);\n'),
    ('        status = "Stopped";\n        gather.onStop();\n', '        status = "Stopped";\n        routing.onStop();\n        gather.onStop();\n'),
    ('    private void onFrame(Bitmap frame) {\n        gather.onFrame(frame);\n    }\n', '    private void onFrame(Bitmap frame) {\n        if (routing.onFrame(frame)) gather.onFrame(frame);\n    }\n'),
    ('            o.put("lastError", lastError);\n            gather.appendState(o);\n', '            o.put("lastError", lastError);\n            routing.appendState(o);\n            gather.appendState(o);\n'),
]
for old, new in repls:
    if old not in macro:
        raise SystemExit('MacroEngine patch anchor missing: ' + old.splitlines()[0])
    macro = macro.replace(old, new, 1)
macro_path.write_text(macro, encoding='utf-8')

svc = svc_path.read_text(encoding='utf-8')
anchor = '''    public void screenshot(int displayId, Consumer<Bitmap> ok, Consumer<Integer> fail) {\n'''
method = r'''    /** Android adaptation of desktop Right-hold + Space, wait, Space. */
    public boolean joystickWithDoubleTap(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long secondTapDelayMs) {
        long safeHold = Math.max(secondTapDelayMs + tapDurationMs + 1, holdMs);
        Path joy = new Path(); joy.moveTo(centerX, centerY); joy.lineTo(targetX, targetY);
        Path tap1 = new Path(); tap1.moveTo(tapX, tapY);
        Path tap2 = new Path(); tap2.moveTo(tapX, tapY);
        GestureDescription.Builder b = new GestureDescription.Builder().setDisplayId(displayId);
        b.addStroke(new GestureDescription.StrokeDescription(joy, 0, Math.max(50, safeHold)));
        b.addStroke(new GestureDescription.StrokeDescription(tap1, 0, Math.max(1, tapDurationMs)));
        b.addStroke(new GestureDescription.StrokeDescription(tap2, Math.max(1, secondTapDelayMs), Math.max(1, tapDurationMs)));
        return dispatchGesture(b.build(), null, null);
    }

'''
if anchor not in svc:
    raise SystemExit('RevoAccessibilityService patch anchor missing')
svc = svc.replace(anchor, method + anchor, 1)
svc_path.write_text(svc, encoding='utf-8')

print('Patched v0.2.12 source-grounded hive routing adapter')
print('  Java:', JAVA / 'RevoPreGatherRouter.java')
print('  Assets:', ', '.join(p.name for p in sorted(ASSETS.glob('*.png'))))

#!/usr/bin/env python3
from pathlib import Path

JAVA = Path('revo-android/app/src/main/java/com/revolution/android')
router_path = JAVA / 'RevoPreGatherRouter.java'
if not router_path.exists():
    raise SystemExit('run v0.2.12 hive + field routing patches first')

router = router_path.read_text(encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit('movement-speed patch anchor missing: ' + label)
    return text.replace(old, new, 1)

# Keep the historical 62.5 value visible for diagnostic/source-guard compatibility,
# but it is no longer the production default. A positive msPerStud is now an explicit
# CI/calibration override only.
router = replace_once(
    router,
    '''    private static final double DEFAULT_MS_PER_STUD = 62.5; // Android calibration, not desktop MoveSpeed detector.\n''',
    '''    private static final double DEFAULT_MS_PER_STUD = 62.5; // Historical 16-stud/s diagnostic reference only.\n    private static final double DEFAULT_BASE_MOVE_SPEED = 24.0; // Revolution Settings.Player.MoveSpeed schema default.\n''',
    'timing constants'
)

router = replace_once(
    router,
    '''        final String account;\n        final String field;\n        final double msPerStud;\n        final double joyX, joyY, joyR;\n''',
    '''        final String account;\n        final String field;\n        final double baseMoveSpeed;\n        final double msPerStud;\n        final int hasteStacks;\n        final boolean hastePlus, coconutHaste, bearMorph, oil, superSmoothie;\n        final double joyX, joyY, joyR;\n''',
    'config fields'
)

router = replace_once(
    router,
    '''        Config(String account, String field, double msPerStud,\n               double joyX, double joyY, double joyR,\n               double jumpX, double jumpY,\n               double interactOffsetX, double interactOffsetY,\n               int templateVariation, boolean requireRoblox) {\n            this.account = account; this.field = field; this.msPerStud = msPerStud;\n            this.joyX = joyX; this.joyY = joyY; this.joyR = joyR;\n''',
    '''        Config(String account, String field, double baseMoveSpeed, double msPerStud,\n               int hasteStacks, boolean hastePlus, boolean coconutHaste, boolean bearMorph,\n               boolean oil, boolean superSmoothie,\n               double joyX, double joyY, double joyR,\n               double jumpX, double jumpY,\n               double interactOffsetX, double interactOffsetY,\n               int templateVariation, boolean requireRoblox) {\n            this.account = account; this.field = field;\n            this.baseMoveSpeed = baseMoveSpeed; this.msPerStud = msPerStud;\n            this.hasteStacks = hasteStacks; this.hastePlus = hastePlus;\n            this.coconutHaste = coconutHaste; this.bearMorph = bearMorph;\n            this.oil = oil; this.superSmoothie = superSmoothie;\n            this.joyX = joyX; this.joyY = joyY; this.joyR = joyR;\n''',
    'config constructor'
)

router = replace_once(
    router,
    '''            double msPerStud = positiveOr(o.optDouble("msPerStud", 0), DEFAULT_MS_PER_STUD);\n            config = new Config(\n                    o.optString("account", "Default"),\n                    o.optString("field", ""),\n                    msPerStud,\n                    ratioOr(o.optDouble("joystickCenterX", 0), 0.16),\n''',
    '''            double msPerStud = o.optDouble("msPerStud", 0);\n            if (!Double.isFinite(msPerStud) || msPerStud <= 0) msPerStud = 0;\n            double baseMoveSpeed = positiveOr(o.optDouble("baseMoveSpeed", 0), DEFAULT_BASE_MOVE_SPEED);\n            config = new Config(\n                    o.optString("account", "Default"),\n                    o.optString("field", ""),\n                    baseMoveSpeed,\n                    msPerStud,\n                    Math.max(0, Math.min(10, o.optInt("hasteStacks", 0))),\n                    o.optBoolean("hastePlus", false),\n                    o.optBoolean("coconutHaste", false),\n                    o.optBoolean("bearMorph", false),\n                    o.optBoolean("oil", false),\n                    o.optBoolean("superSmoothie", false),\n                    ratioOr(o.optDouble("joystickCenterX", 0), 0.16),\n''',
    'configure timing inputs'
)

# Both ordinary route moves and the field-routing diagonal helper must use the same
# desktop-effective-speed timing provider. Exactly two copies exist after field routing.
old_duration = '''        long duration = Math.max(50, Math.min(MAX_GESTURE_MS, Math.round(studs * c.msPerStud)));\n'''
count = router.count(old_duration)
if count != 2:
    raise SystemExit(f'movement-speed patch expected 2 fixed-duration anchors, found {count}')
router = router.replace(
    old_duration,
    '''        long duration = RevoMovementSpeed.durationMs(\n                studs, c.baseMoveSpeed, c.msPerStud,\n                c.hasteStacks, c.hastePlus, c.coconutHaste, c.bearMorph, c.oil, c.superSmoothie,\n                MAX_GESTURE_MS);\n''',
    2
)

state_anchor = '''            r.put("field", c == null ? "" : c.field);\n            r.put("actionCount", actionCount);\n'''
state_new = '''            r.put("field", c == null ? "" : c.field);\n            r.put("baseMoveSpeed", c == null ? 0 : c.baseMoveSpeed);\n            r.put("effectiveMoveSpeed", c == null ? 0 : RevoMovementSpeed.effectiveSpeed(\n                    c.baseMoveSpeed, c.hasteStacks, c.hastePlus, c.coconutHaste,\n                    c.bearMorph, c.oil, c.superSmoothie));\n            r.put("msPerStudOverride", c == null ? 0 : c.msPerStud);\n            r.put("movementTimingMode", c != null && c.msPerStud > 0\n                    ? "explicit-ms-per-stud-override"\n                    : "desktop-effective-speed-v1");\n            r.put("buffSpeedAdaptation", "formula-ported; mobile buff detector not yet validated");\n            r.put("actionCount", actionCount);\n'''
router = replace_once(router, state_anchor, state_new, 'state timing evidence')

router_path.write_text(router, encoding='utf-8')

speed = r'''package com.revolution.android;

/**
 * Source-grounded movement-speed math for Revolution v0.9c-hotfix3.
 *
 * Desktop binary evidence:
 *   speed = configuredMoveSpeed
 *   any bear-family buff => +4 once
 *   Coconut Haste => +10
 *   Haste => x(1 + 0.1 * min(stack, 10))
 *   Haste+ => x2
 *   Oil => x1.2
 *   Super Smoothie => x1.25
 *   duration = distance / effectiveSpeed
 *
 * A positive msPerStudOverride is deliberately reserved for CI / physical
 * calibration so accelerated fake-runtime tests do not alter production math.
 */
final class RevoMovementSpeed {
    private RevoMovementSpeed() {}

    static double effectiveSpeed(double configuredMoveSpeed, int hasteStacks,
                                 boolean hastePlus, boolean coconutHaste,
                                 boolean bearMorph, boolean oil,
                                 boolean superSmoothie) {
        double speed = Double.isFinite(configuredMoveSpeed) && configuredMoveSpeed > 0
                ? configuredMoveSpeed : 24.0;
        if (bearMorph) speed += 4.0;
        if (coconutHaste) speed += 10.0;
        int haste = Math.max(0, Math.min(10, hasteStacks));
        if (haste > 0) speed *= 1.0 + 0.1 * haste;
        if (hastePlus) speed *= 2.0;
        if (oil) speed *= 1.2;
        if (superSmoothie) speed *= 1.25;
        return speed;
    }

    static long durationMs(double studs, double configuredMoveSpeed, double msPerStudOverride,
                           int hasteStacks, boolean hastePlus, boolean coconutHaste,
                           boolean bearMorph, boolean oil, boolean superSmoothie,
                           long maxGestureMs) {
        double msPerStud;
        if (Double.isFinite(msPerStudOverride) && msPerStudOverride > 0) {
            msPerStud = msPerStudOverride;
        } else {
            msPerStud = 1000.0 / effectiveSpeed(
                    configuredMoveSpeed, hasteStacks, hastePlus, coconutHaste,
                    bearMorph, oil, superSmoothie);
        }
        long duration = Math.round(Math.max(0.0, studs) * msPerStud);
        return Math.max(50L, Math.min(maxGestureMs, duration));
    }
}
'''
(JAVA / 'RevoMovementSpeed.java').write_text(speed, encoding='utf-8')
print('PASS: patched source-grounded v0.9c MoveSpeed timing provider')
print('  Java:', JAVA / 'RevoMovementSpeed.java')

from pathlib import Path

P = Path('revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java')
if not P.exists():
    raise SystemExit('RevoPreGatherRouter.java missing; apply hive routing patches first')

s = P.read_text(encoding='utf-8')

old_layout = '''                    ratioOr(o.optDouble("joystickCenterX", 0), 0.16),
                    ratioOr(o.optDouble("joystickCenterY", 0), 0.78),
                    ratioOr(o.optDouble("joystickRadius", 0), 0.085),'''
new_layout = '''                    // landscape-joystick-calibration-v1: measured from live 960x540 Roblox mobile UI
                    ratioOr(o.optDouble("joystickCenterX", 0), 0.094),
                    ratioOr(o.optDouble("joystickCenterY", 0), 0.843),
                    ratioOr(o.optDouble("joystickRadius", 0), 0.085),'''
if s.count(old_layout) != 1:
    raise SystemExit('joystick layout anchor missing or duplicated')
s = s.replace(old_layout, new_layout, 1)

old_probe = '''        float probeR = r * deflectionScale;
        float tx = cx, ty = cy;'''
new_probe = '''        // Live 960x540 QA: ~10 px stays inside Roblox joystick deadzone, ~16 px moves.
        // Keep distance-preserving partial deflection, but never dispatch below 3% of
        // the short display dimension (~16.2 px at 960x540).
        float minimumProbeR = Math.max(1.0f, Math.min(w, h) * 0.03f);
        float probeR = Math.max(minimumProbeR, r * deflectionScale);
        float tx = cx, ty = cy;'''
if s.count(old_probe) != 1:
    raise SystemExit('mobile probe deflection anchor missing or duplicated')
s = s.replace(old_probe, new_probe, 1)

old_log = '''                " %.2f studs %dms nominal=%dms deflection=%.3f",
                studs, duration, nominalDuration, deflectionScale));'''
new_log = '''                " %.2f studs %dms nominal=%dms deflection=%.3f probePx=%.1f center=(%.1f,%.1f)",
                studs, duration, nominalDuration, deflectionScale, probeR, cx, cy));'''
if s.count(old_log) != 1:
    raise SystemExit('mobile probe diagnostic log anchor missing or duplicated')
s = s.replace(old_log, new_log, 1)

for marker in (
    'landscape-joystick-calibration-v1',
    '0.094',
    '0.843',
    'minimumProbeR',
    'probePx=%.1f center=(%.1f,%.1f)',
):
    if marker not in s:
        raise SystemExit('calibration marker missing after patch: ' + marker)

P.write_text(s, encoding='utf-8')
print('PASS: calibrated landscape joystick center and deadzone floor')

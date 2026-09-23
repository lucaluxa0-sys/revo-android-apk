#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java")
s = p.read_text()

old_double = '''    /** Android adaptation of desktop Right-hold + Space, wait, Space. */
    public boolean joystickWithDoubleTap(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long secondTapDelayMs) {
        long safeHold = Math.max(secondTapDelayMs + tapDurationMs + 1, holdMs);
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, safeHold,
                tapX, tapY, tapDurationMs,
                new long[]{0L, Math.max(1L, secondTapDelayMs)});
    }
'''
new_double = '''    /** Android adaptation of desktop Right-hold + Space, wait, Space. */
    public boolean joystickWithDoubleTap(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long secondTapDelayMs) {
        long safeHold = Math.max(secondTapDelayMs + tapDurationMs + 1, holdMs);
        long maxFirstTap = Math.max(1L, safeHold - tapDurationMs - 1L);
        long firstTapDelayMs = Math.max(1L, Math.min(JOYSTICK_ACQUIRE_MS, maxFirstTap));
        long secondTap = Math.max(firstTapDelayMs + 1L, secondTapDelayMs);
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, safeHold,
                tapX, tapY, tapDurationMs,
                new long[]{firstTapDelayMs, secondTap});
    }
'''
if old_double not in s:
    raise SystemExit("joystickWithDoubleTap marker missing")
s = s.replace(old_double, new_double, 1)

old_timed = '''    public boolean joystickWithTimedTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, holdMs,
                tapX, tapY, tapDurationMs, tapOffsetsMs);
    }
'''
new_timed = '''    public boolean joystickWithTimedTaps(int displayId, float centerX, float centerY,
                                         float targetX, float targetY, long holdMs,
                                         float tapX, float tapY, long tapDurationMs,
                                         long[] tapOffsetsMs) {
        long[] adjusted = tapOffsetsMs;
        if (tapOffsetsMs != null && tapOffsetsMs.length > 0 && tapOffsetsMs[0] == 0L) {
            adjusted = tapOffsetsMs.clone();
            long maxFirstTap = Math.max(1L, holdMs - tapDurationMs - 1L);
            adjusted[0] = Math.max(1L, Math.min(JOYSTICK_ACQUIRE_MS, maxFirstTap));
            if (adjusted.length > 1 && adjusted[0] >= adjusted[1]) {
                adjusted[0] = Math.max(1L, adjusted[1] - 1L);
            }
        }
        return joystickHoldWithTaps(
                displayId, centerX, centerY, targetX, targetY, holdMs,
                tapX, tapY, tapDurationMs, adjusted);
    }
'''
if old_timed not in s:
    raise SystemExit("joystickWithTimedTaps marker missing")
s = s.replace(old_timed, new_timed, 1)

p.write_text(s)
print("PASS: jump taps begin after joystick acquisition")

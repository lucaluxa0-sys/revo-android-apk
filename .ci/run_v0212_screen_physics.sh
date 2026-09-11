#!/usr/bin/env bash
set -euo pipefail

mkdir -p emulator-artifacts

adb install -r fake-physics/app/build/outputs/apk/debug/app-debug.apk
adb install -r revo-android/app/build/outputs/apk/debug/app-debug.apk
adb shell cmd appops set com.revolution.android ACCESS_RESTRICTED_SETTINGS allow
adb shell am start -W -n com.revolution.android/.MainActivity > emulator-artifacts/revo-start.txt
python3 .ci/enable_revo_accessibility.py
adb shell settings get secure enabled_accessibility_services > emulator-artifacts/enabled-setting.txt
grep -Fq 'com.revolution.android.RevoAccessibilityService' emulator-artifacts/enabled-setting.txt
adb shell dumpsys accessibility > emulator-artifacts/accessibility-dumpsys.txt

adb logcat -c
adb logcat -v time > emulator-artifacts/logcat.txt 2>&1 &
LPID=$!
cleanup() {
  kill "$LPID" 2>/dev/null || true
  wait "$LPID" 2>/dev/null || true
}
trap cleanup EXIT

adb shell am start -W -n com.roblox.client/.MainActivity > emulator-artifacts/receiver-start.txt
sleep 2

probe() {
  local id="$1"
  local mode="$2"
  local hold="$3"
  local pause="$4"

  adb shell am broadcast \
    -n com.roblox.client/.LabelReceiver \
    -a com.roblox.client.PHYSICS_LABEL \
    --es label "$id" >/dev/null
  sleep 0.15

  adb shell am broadcast \
    -n com.revolution.android/.RevoPhysicsProbeReceiver \
    -a com.revolution.android.PHYSICS_PROBE \
    --es id "$id" \
    --es mode "$mode" \
    --ei holdMs "$hold" \
    > "emulator-artifacts/broadcast-${id}.txt"
  sleep "$pause"
}

probe right_100 right 100 0.8
probe right_250 right 250 1.0
probe right_500 right 500 1.2
probe right_1000 right 1000 1.7
probe right_1650 right 1650 2.4
probe right_6050 right 6050 7.0
probe diag_1000 diag-forward-left 1000 1.7
probe double_1650 double-1650 1650 2.9
probe timed_6050 timed-6050 6050 8.0

cleanup
trap - EXIT

grep -E 'RevoPhysicsProbe|RevoPhysicsReceiver|RevoJoystickHold' \
  emulator-artifacts/logcat.txt > emulator-artifacts/physics-flow.txt || true
cat emulator-artifacts/physics-flow.txt

python3 .ci/verify_v0212_screen_physics.py \
  emulator-artifacts/physics-flow.txt \
  emulator-artifacts/screen-physics.json

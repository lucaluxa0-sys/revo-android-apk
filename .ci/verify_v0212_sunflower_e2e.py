#!/usr/bin/env python3
import json
import re
from pathlib import Path

text = Path('emulator-artifacts/logcat.txt').read_text(errors='replace')
lines = text.splitlines()

required = [
    'FAKE_ROBLOX_URI=roblox://placeId=1537690962',
    'FAKE_HIVE_PROMPT_VISIBLE',
    'template=claimhive',
    'desktop KeyPress(E): claim center hive',
    'FAKE_CLAIM_TAP',
    'Claimed Hive: 3',
    'desktop GotoCannon: Forward 12',
    'desktop GotoCannon: Right 37 slot 1',
    'desktop GotoCannon: Right 37 slot 2',
    'desktop GotoCannon: Right 37 slot 3',
    'desktop GotoCannon: hold Right + Space, 1300ms, Space',
    'template=press_e',
    'state=READY_AT_CANNON',
    'desktop cannon.black-bear: SetYaw(2)',
    'FAKE_SUNFLOWER_ROUTE_STARTED',
    'FAKE_BLACK_BEAR_PROMPT_VISIBLE',
    'desktop cannon.black-bear: Walk Forward 30 30.00 studs 360ms',
    'desktop cannon.black-bear: Walk Right 50 50.00 studs 600ms',
    'desktop cannon.black-bear Checkpoint WalkDetector interaction: Backward 10 10.00 studs 120ms',
    'desktop black-bear.sunflower-tr: SetYaw(0)',
    'desktop black-bear.sunflower-tr: Walk Left 30 30.00 studs 360ms',
    'desktop black-bear.sunflower-tr: Walk Backward 70 70.00 studs 840ms',
    'desktop black-bear.sunflower-tr: WalkAlign Right 35 35.00 studs 420ms',
    'desktop black-bear.sunflower-tr: Walk Forward 40 40.00 studs 480ms',
    'FIELD_ROUTE_READY route=cannon->black-bear->sunflower-tr',
    'configured pattern=e_lol steps=18',
    'action pattern=e_lol step=',
    'RevoMovementEvidence',
    'confirmed=true',
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('missing Sunflower runtime evidence: ' + repr(missing))

for forbidden in (
    'FAKE_CANNON_INTERACT_UNEXPECTED',
    'desktop cannon.pinetree-br:',
    'desktop pinetree-br.pinetree-center:',
    'FIELD_ROUTE_READY route=cannon->pinetree-br->pinetree-center',
):
    if forbidden in text:
        raise SystemExit('forbidden Sunflower-route evidence observed: ' + forbidden)

failed_joystick = [
    line for line in lines
    if 'RevoJoystickHold' in line
    and any(marker in line for marker in (
        'sequenceFailed=true', 'busyRejected=true', 'acquireCancelled=true',
        'holdCancelled=true', 'tapCancelled=true', 'acquireDispatchRejected=true',
        'continuationAccepted=false', 'tapAccepted=false',
    ))
]
if failed_joystick:
    raise SystemExit('joystick serialized full-deflection failure observed: ' + repr(failed_joystick[:8]))

ordered = [
    'FAKE_CLAIM_TAP',
    'state=READY_AT_CANNON',
    'desktop cannon.black-bear: SetYaw(2)',
    'desktop cannon.black-bear: Walk Forward 30',
    'desktop cannon.black-bear: Walk Right 50',
    'desktop cannon.black-bear Checkpoint WalkDetector interaction: Backward 10',
    'FAKE_BLACK_BEAR_PROMPT_VISIBLE',
    'desktop black-bear.sunflower-tr: SetYaw(0)',
    'desktop black-bear.sunflower-tr: Walk Left 30',
    'desktop black-bear.sunflower-tr: Walk Backward 70',
    'desktop black-bear.sunflower-tr: WalkAlign Right 35',
    'desktop black-bear.sunflower-tr: Walk Forward 40',
    'FIELD_ROUTE_READY route=cannon->black-bear->sunflower-tr',
    'RevoMovementEvidence',
]
pos = -1
for item in ordered:
    next_pos = text.find(item, pos + 1)
    if next_pos < 0:
        raise SystemExit('ordered Sunflower runtime evidence missing: ' + item)
    if next_pos <= pos:
        raise SystemExit('Sunflower runtime evidence out of order: ' + item)
    pos = next_pos

states = []
for line in lines:
    if 'RevoSunflowerState' not in line:
        continue
    match = re.search(r'RevoSunflowerState(?:\([^)]*\))?:\s*(\{.*\})\s*$', line)
    if not match:
        continue
    try:
        states.append(json.loads(match.group(1)))
    except Exception:
        pass
if not states:
    raise SystemExit('no parseable RevoSunflowerState JSON')

state = states[-1]
routing = state.get('routing') or {}
assert state.get('running') is True, state
assert state.get('routine') == 'gather', state
assert state.get('patternName') == 'e_lol', state
assert state.get('patternStepCount') == 18, state
assert routing.get('state') == 'FIELD_READY', routing
assert routing.get('claimedHive') == 3, routing
assert routing.get('cannonSlotMoves') == 3, routing
assert routing.get('fieldRoutingPorted') is True, routing
assert routing.get('fieldRoute') == 'cannon->black-bear->sunflower-tr', routing
assert routing.get('fieldRouteDatasetSha256') == 'c0a499ba9512b4282bc3f59bdf9daacedd6841b1d7a2008f90075e3d0c07859f', routing
assert routing.get('currentYawSlot') == 0, routing
assert (routing.get('fieldRouteActionCount') or 0) >= 9, routing
assert (routing.get('blackBearCheckpointAttempts') or 0) < 3, routing
assert routing.get('lastGestureAccepted') is True, routing
assert routing.get('androidInputAdaptation') == 'accessibility-joystick-hold-v2', routing
assert (state.get('actionCount') or 0) > 0, state
assert (state.get('visualMovementSamples') or 0) >= 1, state
assert (state.get('visualMovementConfirmedSamples') or 0) >= 1, state
assert state.get('activePackage') == 'com.roblox.client', state
assert not (state.get('routineLastError') or ''), state

print('PASS: real Start -> ClaimHive -> GotoCannon prompt -> decoded cannon->Black Bear->Sunflower route -> e_lol with confirmed world-view movement')

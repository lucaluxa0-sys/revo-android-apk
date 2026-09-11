#!/usr/bin/env python3
import json
import re
from pathlib import Path

text = Path('emulator-artifacts/logcat.txt').read_text(errors='replace')

required = [
    'FAKE_ROBLOX_URI=roblox://placeId=1537690962',
    'FAKE_HIVE_PROMPT_VISIBLE',
    'template=claimhive',
    'desktop ClaimHive: Backward 2',
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
    'desktop cannon.pinetree-br: SetYaw(4)',
    'desktop cannon.pinetree-br: KeyPress(E)',
    'FAKE_CANNON_INTERACT',
    'desktop cannon.pinetree-br: Forward+Left 6050ms + Space@0,850,5670',
    'desktop cannon.pinetree-br: WalkAsync Left 77.5 + WalkAlign Forward',
    'desktop cannon.pinetree-br: WalkAlign Forward remainder',
    'desktop pinetree-br.pinetree-center: SetYaw(2)',
    'desktop pinetree-br.pinetree-center: Backward+Left 70',
    'desktop pinetree-br.pinetree-center: Left 20',
    'FIELD_ROUTE_READY route=cannon->pinetree-br->pinetree-center',
    'configured pattern=e_lol steps=18',
    'action pattern=e_lol step=',
    'RevoMovementEvidence',
    'confirmed=true',
]

missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('missing runtime evidence: ' + repr(missing))

lines = text.splitlines()

# Android Accessibility cannot safely inject an intermittent second pointer into
# an already-continued joystick stream: API 35 cancelled that mixed continuation
# in the real runtime. The mobile adapter therefore preserves the recovered
# desktop movement offsets in full-deflection-distance time: move to each jump
# offset, release, tap, reacquire full deflection, and continue. This gate proves
# that the complete requested movement duration and every recovered jump offset
# actually completed; merely dispatching the first segment is not sufficient.
def has_hold_line(hold_ms, *needles):
    return any(
        'RevoJoystickHold' in line
        and f'holdMs={hold_ms}' in line
        and all(needle in line for needle in needles)
        for line in lines
    )


def has_logical_hold_line(hold_ms, *needles):
    return any(
        'RevoJoystickHold' in line
        and f'logicalHoldMs={hold_ms}' in line
        and all(needle in line for needle in needles)
        for line in lines
    )


# GotoCannon: Right is held for 1650 ms with Space at movement offsets 0 and 1300.
if not has_hold_line(1650, 'sequenceStarted=true', 'tapCount=2'):
    raise SystemExit('no serialized 1650ms GotoCannon joystick sequence start')
if not has_hold_line(1650, 'sequenceCompleted=true', 'fullDeflectionMs=1650', 'tapCount=2'):
    raise SystemExit('no completed 1650ms GotoCannon full-deflection sequence')
for tap_index, offset in enumerate((0, 1300)):
    if not has_logical_hold_line(
            1650, 'tapCompleted=true', f'tapIndex={tap_index}', f'offsetMs={offset}'):
        raise SystemExit(f'GotoCannon jump tap {tap_index} at movement offset {offset}ms did not complete')
for segment_index, (segment_ms, movement_done_ms) in enumerate(((1300, 1300), (350, 1650))):
    if not has_logical_hold_line(
            1650, 'segmentCompleted=true', f'segmentIndex={segment_index}',
            f'segmentMs={segment_ms}', f'movementDoneMs={movement_done_ms}'):
        raise SystemExit(
            f'GotoCannon full-deflection segment {segment_index} '
            f'({segment_ms}ms -> {movement_done_ms}ms) did not complete')

# Decoded cannon.pinetree-br: Forward+Left full deflection totals exactly 6050 ms,
# with Space at movement offsets 0, 850 and 5670 ms. Segments are therefore
# 850 + 4820 + 380 = 6050 ms; require every one plus all three jump taps.
if not has_hold_line(6050, 'sequenceStarted=true', 'tapCount=3'):
    raise SystemExit('no serialized 6050ms cannon-to-Pine joystick sequence start')
if not has_hold_line(6050, 'sequenceCompleted=true', 'fullDeflectionMs=6050', 'tapCount=3'):
    raise SystemExit('no completed 6050ms cannon-to-Pine full-deflection sequence')
for tap_index, offset in enumerate((0, 850, 5670)):
    if not has_logical_hold_line(
            6050, 'tapCompleted=true', f'tapIndex={tap_index}', f'offsetMs={offset}'):
        raise SystemExit(f'cannon-to-Pine jump tap {tap_index} at movement offset {offset}ms did not complete')
for segment_index, (segment_ms, movement_done_ms) in enumerate(
        ((850, 850), (4820, 5670), (380, 6050))):
    if not has_logical_hold_line(
            6050, 'segmentCompleted=true', f'segmentIndex={segment_index}',
            f'segmentMs={segment_ms}', f'movementDoneMs={movement_done_ms}'):
        raise SystemExit(
            f'cannon-to-Pine full-deflection segment {segment_index} '
            f'({segment_ms}ms -> {movement_done_ms}ms) did not complete')

# Fail closed on any Accessibility cancellation/rejection. This is intentionally
# broader than the old verifier because a segmented movement must prove every
# acquire, continuation and tap dispatch, not only the aggregate completion log.
failed_joystick = [
    line for line in lines
    if 'RevoJoystickHold' in line
    and any(marker in line for marker in (
        'sequenceFailed=true',
        'busyRejected=true',
        'acquireCancelled=true',
        'holdCancelled=true',
        'tapCancelled=true',
        'acquireDispatchRejected=true',
        'continuationAccepted=false',
        'tapAccepted=false',
    ))
]
if failed_joystick:
    raise SystemExit('joystick serialized full-deflection failure observed: ' + repr(failed_joystick[:8]))

# Enforce the real causal order rather than accepting the same markers out of sequence.
ordered = [
    'FAKE_CLAIM_TAP',
    'state=READY_AT_CANNON',
    'desktop cannon.pinetree-br: SetYaw(4)',
    'FAKE_CANNON_INTERACT',
    'desktop cannon.pinetree-br: Forward+Left 6050ms + Space@0,850,5670',
    'FIELD_ROUTE_READY route=cannon->pinetree-br->pinetree-center',
    'RevoMovementEvidence',
]
pos = -1
for item in ordered:
    next_pos = text.find(item, pos + 1)
    if next_pos < 0:
        raise SystemExit('ordered runtime evidence missing: ' + item)
    if next_pos <= pos:
        raise SystemExit('runtime evidence out of order: ' + item)
    pos = next_pos

confirmed_evidence = [
    line for line in lines
    if 'RevoMovementEvidence' in line and 'confirmed=true' in line
]
if not confirmed_evidence:
    raise SystemExit('no confirmed Roblox world-view movement sample after Gather action')

states = []
for line in lines:
    if 'RevoElolState' not in line:
        continue
    match = re.search(r'RevoElolState(?:\([^)]*\))?:\s*(\{.*\})\s*$', line)
    if not match:
        continue
    try:
        states.append(json.loads(match.group(1)))
    except Exception:
        pass

if not states:
    raise SystemExit('no parseable RevoElolState JSON')

state = states[-1]
routing = state.get('routing') or {}
assert state.get('running') is True, state
# engineConfig normalizes the desktop preset's gatherPattern key to patternName.
# Validate the authoritative running engine schema instead of a stale frontend key name.
assert state.get('routine') == 'gather', state
assert state.get('patternName') == 'e_lol', state
assert state.get('patternStepCount') == 18, state
assert routing.get('state') == 'FIELD_READY', routing
assert routing.get('claimedHive') == 3, routing
assert routing.get('cannonSlotMoves') == 3, routing
assert routing.get('fieldRoutingPorted') is True, routing
assert routing.get('fieldRoute') == 'cannon->pinetree-br->pinetree-center', routing
assert routing.get('fieldRouteDatasetSha256') == 'c0a499ba9512b4282bc3f59bdf9daacedd6841b1d7a2008f90075e3d0c07859f', routing
assert routing.get('currentYawSlot') == 2, routing
assert (routing.get('fieldRouteActionCount') or 0) >= 8, routing
assert routing.get('lastGestureAccepted') is True, routing
assert routing.get('androidInputAdaptation') == 'accessibility-joystick-hold-v2', routing
assert (state.get('actionCount') or 0) > 0, state
assert (state.get('visualMovementSamples') or 0) >= 1, state
assert (state.get('visualMovementConfirmedSamples') or 0) >= 1, state
assert state.get('activePackage') == 'com.roblox.client', state
assert not (state.get('routineLastError') or ''), state

print('PASS: real Start -> Bee Swarm -> ClaimHive -> GotoCannon -> decoded Pine Tree route -> serialized full-deflection Android movement+jumps -> e_lol with confirmed world-view movement')

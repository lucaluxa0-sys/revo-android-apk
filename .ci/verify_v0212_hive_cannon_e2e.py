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
    '"gatherPattern":"e_lol"',
    'RevoMovementEvidence',
    'confirmed=true',
]

missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('missing runtime evidence: ' + repr(missing))

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
    line for line in text.splitlines()
    if 'RevoMovementEvidence' in line and 'confirmed=true' in line
]
if not confirmed_evidence:
    raise SystemExit('no confirmed Roblox world-view movement sample after Gather action')

states = []
for line in text.splitlines():
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
assert routing.get('state') == 'FIELD_READY', routing
assert routing.get('claimedHive') == 3, routing
assert routing.get('cannonSlotMoves') == 3, routing
assert routing.get('fieldRoutingPorted') is True, routing
assert routing.get('fieldRoute') == 'cannon->pinetree-br->pinetree-center', routing
assert routing.get('fieldRouteDatasetSha256') == 'c0a499ba9512b4282bc3f59bdf9daacedd6841b1d7a2008f90075e3d0c07859f', routing
assert routing.get('currentYawSlot') == 2, routing
assert (routing.get('fieldRouteActionCount') or 0) >= 8, routing
assert routing.get('lastGestureAccepted') is True, routing
assert (state.get('actionCount') or 0) > 0, state
assert (state.get('visualMovementSamples') or 0) >= 1, state
assert (state.get('visualMovementConfirmedSamples') or 0) >= 1, state
assert state.get('activePackage') == 'com.roblox.client', state
assert not (state.get('routineLastError') or ''), state

print('PASS: real Start -> Bee Swarm -> ClaimHive -> GotoCannon -> decoded Pine Tree route -> e_lol with confirmed world-view movement')
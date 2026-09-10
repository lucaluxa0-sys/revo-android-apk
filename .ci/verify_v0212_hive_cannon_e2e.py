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
]

missing = [item for item in required if item not in text]
if missing:
    raise SystemExit('missing runtime evidence: ' + repr(missing))

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
assert routing.get('state') == 'READY_AT_CANNON', routing
assert routing.get('claimedHive') == 3, routing
assert routing.get('cannonSlotMoves') == 3, routing
assert routing.get('fieldRoutingPorted') is False, routing
assert routing.get('lastGestureAccepted') is True, routing
assert (state.get('actionCount') or 0) == 0, state  # Gather remains blocked until field routing exists.

print('PASS: real Start -> Bee Swarm URI -> source-grounded ClaimHive -> GotoCannon reached READY_AT_CANNON')

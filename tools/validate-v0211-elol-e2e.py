#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'emulator-artifacts')
log = (root / 'logcat.txt').read_text(errors='replace')
activities = (root / 'activities.txt').read_text(errors='replace')

checks = [
    ('prepared e_lol config', 'RevoElolPrepared' in log and '"patternName":"e_lol"' in log),
    ('real Start button found', 'RevoElolStartButton' in log and '"text":"Start"' in log),
    ('native engine configured for e_lol', '[android-engine] configured' in log and '"patternName":"e_lol"' in log),
    ('Bee Swarm direct URI launched', 'Launching Bee Swarm via roblox://placeId=1537690962 package=com.roblox.client' in log),
    ('Roblox receiver got Bee Swarm URI', 'FAKE_ROBLOX_URI=roblox://placeId=1537690962' in log),
    ('recovered e_lol program has 18 steps', 'configured pattern=e_lol steps=18' in log),
    ('e_lol movement action dispatched', 'action pattern=e_lol' in log),
    ('foreground Roblox received Accessibility touch', 'FAKE_ROBLOX_TOUCH count=' in log),
    ('visual movement confirmation observed', 'RevoMovementEvidence' in log and 'confirmed=true' in log),
    ('Roblox receiver remained foreground', bool(re.search(r'(?:topResumedActivity|mResumedActivity).*com\.roblox\.client', activities))),
]

failed = False
for name, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + name)
    failed |= not ok

state_lines = [line for line in log.splitlines() if 'RevoElolState' in line and '{' in line]
if not state_lines:
    print('FAIL: final RevoElolState JSON missing')
    sys.exit(1)
state_line = state_lines[-1]
m = re.search(r'RevoElolState.*?(\{.*\})', state_line)
if not m:
    print('FAIL: unable to parse RevoElolState line: ' + state_line)
    sys.exit(1)
state = json.loads(m.group(1))
(root / 'state.json').write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')

state_checks = [
    ('engine running', state.get('running') is True),
    ('routine gather', state.get('routine') == 'gather'),
    ('pattern e_lol', state.get('patternName') == 'e_lol'),
    ('pattern step count 18', state.get('patternStepCount') == 18),
    ('multiple movement actions', int(state.get('actionCount') or 0) >= 2),
    ('last Accessibility gesture accepted', state.get('lastGestureAccepted') is True),
    ('Roblox foreground required', state.get('requireRobloxForeground') is True),
    ('Roblox package foreground', state.get('activePackage') == 'com.roblox.client'),
    ('visual evidence mode active', state.get('movementEvidenceMode') == 'roblox-foreground-frame-delta-v1'),
    ('visual movement sampled', int(state.get('visualMovementSamples') or 0) >= 1),
    ('visual movement confirmed', int(state.get('visualMovementConfirmedSamples') or 0) >= 1),
]
for name, ok in state_checks:
    print(('PASS' if ok else 'FAIL') + ': ' + name)
    failed |= not ok

print('FINAL_STATE=' + json.dumps(state, sort_keys=True))
if failed:
    raise SystemExit('FAIL: e_lol end-to-end gate requirements were not all met')
print('PASS: real Start -> Bee Swarm URI -> e_lol 18-step adapter -> Accessibility movement -> visual response on Android 15')

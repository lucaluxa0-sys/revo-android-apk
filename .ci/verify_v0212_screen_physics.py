#!/usr/bin/env python3
import json
import math
import re
import sys
from pathlib import Path

if len(sys.argv) not in (1, 3):
    raise SystemExit('usage: verify_v0212_screen_physics.py [physics-flow.txt screen-physics.json]')

src = Path(sys.argv[1] if len(sys.argv) == 3 else 'emulator-artifacts/physics-flow.txt')
out = Path(sys.argv[2] if len(sys.argv) == 3 else 'emulator-artifacts/screen-physics.json')
text = src.read_text(errors='replace')
lines = text.splitlines()

bad = [
    line for line in lines
    if 'RevoJoystickHold' in line and any(marker in line for marker in (
        'sequenceFailed=true',
        'Cancelled=true',
        'DispatchRejected=true',
        'busyRejected=true',
    ))
]
if bad:
    raise SystemExit('joystick service failure: ' + repr(bad[:10]))

dispatch_re = re.compile(
    r'PHYSICS_DISPATCH id=(\S+) mode=(\S+) holdMs=(\d+).*?'
    r'cx=([\d.\-]+) cy=([\d.\-]+) r=([\d.\-]+) '
    r'tx=([\d.\-]+) ty=([\d.\-]+) jumpX=([\d.\-]+) jumpY=([\d.\-]+)'
)
event_re = re.compile(
    r'PHYSICS_EVENT label=(\S+) action=(\S+) eventMs=(\d+).*?'
    r'p0x=([\d.\-]+) p0y=([\d.\-]+)'
)

dispatch = {}
events = {}
for line in lines:
    match = dispatch_re.search(line)
    if match:
        dispatch[match.group(1)] = {
            'mode': match.group(2),
            'holdMs': int(match.group(3)),
            'cx': float(match.group(4)),
            'cy': float(match.group(5)),
            'r': float(match.group(6)),
            'tx': float(match.group(7)),
            'ty': float(match.group(8)),
            'jumpX': float(match.group(9)),
            'jumpY': float(match.group(10)),
        }
    match = event_re.search(line)
    if match:
        events.setdefault(match.group(1), []).append({
            'action': match.group(2),
            't': int(match.group(3)),
            'x': float(match.group(4)),
            'y': float(match.group(5)),
        })


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


report = {
    'claim': 'screen-space gesture physics only; no Roblox stud calibration claimed',
    'ordinary': {},
    'route_sequences': {},
}

ordinary_ids = [
    'right_100',
    'right_250',
    'right_500',
    'right_1000',
    'right_1650',
    'right_6050',
    'diag_1000',
]
for ident in ordinary_ids:
    d = dispatch.get(ident)
    ev = events.get(ident, [])
    if not d or not ev:
        raise SystemExit('missing ordinary evidence: ' + ident)
    if any(e['action'] == 'CANCEL' for e in ev):
        raise SystemExit('ACTION_CANCEL: ' + ident)

    downs = [e for e in ev if e['action'] == 'DOWN']
    ups = [e for e in ev if e['action'] == 'UP']
    if len(downs) != 1 or len(ups) != 1:
        raise SystemExit(
            f'unexpected pointer lifecycle {ident}: down={len(downs)} up={len(ups)}'
        )

    down, up = downs[0], ups[-1]
    if dist(down['x'], down['y'], d['cx'], d['cy']) > 4.0:
        raise SystemExit('bad joystick center: ' + ident)

    endpoint_candidates = [
        e for e in ev if dist(e['x'], e['y'], d['tx'], d['ty']) <= 4.0
    ]
    if not endpoint_candidates:
        raise SystemExit('joystick never reached endpoint: ' + ident)

    endpoint = endpoint_candidates[0]
    acquire = endpoint['t'] - down['t']
    if acquire < 0 or acquire > 120:
        raise SystemExit(f'slow/invalid joystick acquisition {ident}: {acquire}ms')

    full = up['t'] - endpoint['t']
    tolerance = max(55, round(d['holdMs'] * 0.03))
    if abs(full - d['holdMs']) > tolerance:
        raise SystemExit(
            f'full-deflection timing drift {ident}: measured={full} '
            f'requested={d["holdMs"]} tol={tolerance}'
        )

    tail = [e for e in ev if endpoint['t'] <= e['t'] <= up['t']]
    drift = max(dist(e['x'], e['y'], d['tx'], d['ty']) for e in tail)
    if drift > 4.0:
        raise SystemExit(f'endpoint drift {ident}: {drift:.2f}px')

    actual_radius = dist(down['x'], down['y'], endpoint['x'], endpoint['y'])
    if abs(actual_radius - d['r']) > 4.0:
        raise SystemExit(
            f'radius mismatch {ident}: actual={actual_radius:.2f} requested={d["r"]:.2f}'
        )

    completions = [
        line for line in lines
        if 'RevoJoystickHold' in line
        and 'holdCompleted=true' in line
        and 'sequenceCompleted=true' in line
        and f'holdMs={d["holdMs"]}' in line
        and f'fullDeflectionMs={d["holdMs"]}' in line
        and 'tapCount=0' in line
    ]
    if not completions:
        raise SystemExit('missing authoritative ordinary completion: ' + ident)

    report['ordinary'][ident] = {
        'requestedHoldMs': d['holdMs'],
        'acquireMs': acquire,
        'measuredFullDeflectionMs': full,
        'timingErrorMs': full - d['holdMs'],
        'endpointDriftPx': drift,
        'requestedRadiusPx': d['r'],
        'measuredRadiusPx': actual_radius,
    }

route_specs = [
    ('double_1650', 1650, 2, 2),
    ('timed_6050', 6050, 3, 3),
]
for ident, expected_hold, expected_taps, expected_segments in route_specs:
    d = dispatch.get(ident)
    ev = events.get(ident, [])
    if not d or not ev:
        raise SystemExit('missing route evidence: ' + ident)
    if any(e['action'] == 'CANCEL' for e in ev):
        raise SystemExit('ACTION_CANCEL: ' + ident)

    jumps = [
        e for e in ev
        if e['action'] == 'DOWN'
        and dist(e['x'], e['y'], d['jumpX'], d['jumpY']) <= 5.0
    ]
    moves = [
        e for e in ev
        if e['action'] == 'DOWN'
        and dist(e['x'], e['y'], d['cx'], d['cy']) <= 5.0
    ]
    if len(jumps) != expected_taps:
        raise SystemExit(f'jump count mismatch {ident}: {len(jumps)}')
    if len(moves) != expected_segments:
        raise SystemExit(f'movement segment count mismatch {ident}: {len(moves)}')

    completion = [
        line for line in lines
        if 'RevoJoystickHold' in line
        and 'holdCompleted=true' in line
        and 'sequenceCompleted=true' in line
        and f'holdMs={expected_hold}' in line
        and f'fullDeflectionMs={expected_hold}' in line
        and f'tapCount={expected_taps}' in line
    ]
    if not completion:
        raise SystemExit('missing authoritative sequence completion: ' + ident)

    wall = max(e['t'] for e in ev) - min(e['t'] for e in ev)
    report['route_sequences'][ident] = {
        'fullDeflectionMs': expected_hold,
        'jumpCount': len(jumps),
        'movementSegments': len(moves),
        'receiverWallClockMs': wall,
        'serializedOverheadMs': wall - expected_hold,
    }

out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print('PASS: API35 screen-space joystick geometry/timing measured; Roblox stud calibration intentionally not claimed')

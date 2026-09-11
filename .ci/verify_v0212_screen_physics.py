#!/usr/bin/env python3
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

if len(sys.argv) not in (1, 3):
    raise SystemExit('usage: verify_v0212_screen_physics.py [physics-flow.txt screen-physics.json]')

src = Path(sys.argv[1] if len(sys.argv) == 3 else 'emulator-artifacts/physics-flow.txt')
out = Path(sys.argv[2] if len(sys.argv) == 3 else 'emulator-artifacts/screen-physics.json')
text = src.read_text(errors='replace')
lines = text.splitlines()

failure_markers = (
    'sequenceFailed=true',
    'acquireCancelled=true',
    'holdCancelled=true',
    'tapCancelled=true',
    'acquireDispatchRejected=true',
    'holdDispatchRejected=true',
    'tapDispatchRejected=true',
    'busyRejected=true',
)
bad = [line for line in lines if 'RevoJoystickHold' in line and any(m in line for m in failure_markers)]
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
accepted_re = re.compile(r'PHYSICS_ACCEPTED id=(\S+) accepted=(true|false)')
completion_re = re.compile(
    r'holdCompleted=true sequenceCompleted=true display=\d+ holdMs=(\d+) '
    r'fullDeflectionMs=(\d+) tapCount=(\d+)'
)

dispatch = {}
events = {}
accepted = {}
completions = []
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
    match = accepted_re.search(line)
    if match:
        accepted[match.group(1)] = match.group(2) == 'true'
    match = completion_re.search(line)
    if match:
        completions.append(tuple(map(int, match.groups())))


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def direction(d):
    dx = d['tx'] - d['cx']
    dy = d['ty'] - d['cy']
    mag = math.hypot(dx, dy)
    if mag <= 0:
        raise SystemExit('zero-length requested joystick direction')
    if abs(mag - d['r']) > 0.25:
        raise SystemExit(f'dispatch radius mismatch: vector={mag:.3f} advertised={d["r"]:.3f}')
    return dx / mag, dy / mag


def projection_from(event, origin, ux, uy):
    vx = event['x'] - origin['x']
    vy = event['y'] - origin['y']
    return vx * ux + vy * uy, abs(vx * uy - vy * ux)


def saturated(event, origin, d, ux, uy):
    projection, cross = projection_from(event, origin, ux, uy)
    cross_limit = max(4.0, d['r'] * 0.06)
    return (
        0.95 * d['r'] <= projection <= 1.08 * d['r']
        and cross <= cross_limit
    )


def hold_tolerance(ms):
    # Deliberately unchanged from the original strict screen-physics budget.
    return max(55, round(ms * 0.03))


def validate_movement_cycle(ident, d, cycle, logical_ms):
    if not cycle or cycle[0]['action'] != 'DOWN' or cycle[-1]['action'] != 'UP':
        raise SystemExit(f'incomplete movement pointer lifecycle: {ident}')
    if any(e['action'] == 'CANCEL' for e in cycle):
        raise SystemExit('ACTION_CANCEL: ' + ident)

    down = cycle[0]
    up = cycle[-1]
    if dist(down['x'], down['y'], d['cx'], d['cy']) > 4.0:
        raise SystemExit('bad joystick center: ' + ident)

    ux, uy = direction(d)
    saturation = [e for e in cycle if e['action'] == 'MOVE' and saturated(e, down, d, ux, uy)]
    if not saturation:
        raise SystemExit('joystick never reached directional saturation: ' + ident)
    first = saturation[0]
    acquire = first['t'] - down['t']
    if acquire < 20 or acquire > 60:
        raise SystemExit(f'slow/invalid joystick acquisition {ident}: {acquire}ms')

    terminal_projection, terminal_cross = projection_from(up, down, ux, uy)
    terminal_cross_limit = max(4.0, d['r'] * 0.06)
    if not (0.95 * d['r'] <= terminal_projection <= 1.05 * d['r']):
        raise SystemExit(
            f'bad terminal joystick projection {ident}: {terminal_projection:.2f}px '
            f'for radius={d["r"]:.2f}px'
        )
    if terminal_cross > terminal_cross_limit:
        raise SystemExit(f'bad terminal joystick cross-track {ident}: {terminal_cross:.2f}px')

    observed_hold = up['t'] - first['t']
    tolerance = hold_tolerance(logical_ms)
    timing_error = observed_hold - logical_ms
    if abs(timing_error) > tolerance:
        raise SystemExit(
            f'screen hold timing drift {ident}: observed={observed_hold} '
            f'requested={logical_ms} tol={tolerance}'
        )

    sat_projection, sat_cross = projection_from(first, down, ux, uy)
    return {
        'requestedHoldMs': logical_ms,
        'acquireMs': acquire,
        'observedSaturatedHoldMs': observed_hold,
        'timingErrorMs': timing_error,
        'timingToleranceMs': tolerance,
        'requestedRadiusPx': d['r'],
        'firstSaturatedProjectionPx': sat_projection,
        'firstSaturatedCrossTrackPx': sat_cross,
        'terminalProjectionPx': terminal_projection,
        'terminalCrossTrackPx': terminal_cross,
    }


def pointer_cycles(ev):
    cycles = []
    current = None
    for event in ev:
        if event['action'] == 'DOWN':
            if current is not None:
                raise SystemExit('nested DOWN in pointer lifecycle')
            current = [event]
        elif current is not None:
            current.append(event)
            if event['action'] in ('UP', 'CANCEL'):
                cycles.append(current)
                current = None
    if current is not None:
        raise SystemExit('unterminated pointer lifecycle')
    return cycles


expected_ids = [
    'warmup_250',
    'right_50_a',
    'right_50_b',
    'right_100',
    'right_250',
    'right_500',
    'right_1000',
    'right_1650',
    'right_6050',
    'diag_1000',
    'double_1650',
    'timed_6050',
]
for ident in expected_ids:
    if ident not in dispatch or ident not in events:
        raise SystemExit('missing probe evidence: ' + ident)
    if accepted.get(ident) is not True:
        raise SystemExit('probe dispatch not accepted: ' + ident)

report = {
    'claim': 'screen-space Accessibility gesture physics only; no Roblox stud calibration claimed',
    'timingBudget': 'absolute error <= max(55ms, 3% of logical hold); unchanged from original diagnostic',
    'warmup': {},
    'ordinary': {},
    'routeSequences': {},
}

ordinary_ids = [
    'warmup_250',
    'right_50_a',
    'right_50_b',
    'right_100',
    'right_250',
    'right_500',
    'right_1000',
    'right_1650',
    'right_6050',
    'diag_1000',
]
for ident in ordinary_ids:
    ev = events[ident]
    if any(e['action'] == 'CANCEL' for e in ev):
        raise SystemExit('ACTION_CANCEL: ' + ident)
    cycles = pointer_cycles(ev)
    if len(cycles) != 1:
        raise SystemExit(f'unexpected ordinary pointer cycle count {ident}: {len(cycles)}')
    result = validate_movement_cycle(ident, dispatch[ident], cycles[0], dispatch[ident]['holdMs'])
    if ident == 'warmup_250':
        report['warmup'][ident] = result
    else:
        report['ordinary'][ident] = result

# Authoritative Accessibility callbacks must prove every ordinary logical hold exactly.
expected_ordinary_completion_counts = Counter((dispatch[i]['holdMs'], dispatch[i]['holdMs'], 0) for i in ordinary_ids)
actual_completion_counts = Counter(completions)
for key, count in expected_ordinary_completion_counts.items():
    if actual_completion_counts[key] < count:
        raise SystemExit(f'missing authoritative ordinary completions {key}: expected={count} actual={actual_completion_counts[key]}')

route_specs = {
    'double_1650': {
        'logicalHoldMs': 1650,
        'tapCount': 2,
        'tapOffsets': [0, 1300],
        'segmentMs': [1300, 350],
        'movementDoneMs': [1300, 1650],
    },
    'timed_6050': {
        'logicalHoldMs': 6050,
        'tapCount': 3,
        'tapOffsets': [0, 850, 5670],
        'segmentMs': [850, 4820, 380],
        'movementDoneMs': [850, 5670, 6050],
    },
}
for ident, spec in route_specs.items():
    d = dispatch[ident]
    ev = events[ident]
    if any(e['action'] == 'CANCEL' for e in ev):
        raise SystemExit('ACTION_CANCEL: ' + ident)
    cycles = pointer_cycles(ev)
    expected_cycle_count = spec['tapCount'] * 2
    if len(cycles) != expected_cycle_count:
        raise SystemExit(f'pointer cycle count mismatch {ident}: {len(cycles)} != {expected_cycle_count}')

    movement_results = []
    jump_results = []
    expected_order = []
    for _ in range(spec['tapCount']):
        expected_order.extend(['jump', 'movement'])

    movement_index = 0
    for cycle_index, (cycle, expected_kind) in enumerate(zip(cycles, expected_order)):
        down, up = cycle[0], cycle[-1]
        if expected_kind == 'jump':
            if dist(down['x'], down['y'], d['jumpX'], d['jumpY']) > 5.0:
                raise SystemExit(f'jump coordinate mismatch {ident} cycle={cycle_index}')
            if any(e['action'] not in ('DOWN', 'UP') for e in cycle):
                raise SystemExit(f'unexpected jump pointer event {ident} cycle={cycle_index}')
            duration = up['t'] - down['t']
            if abs(duration - 70) > 20:
                raise SystemExit(f'jump duration drift {ident} cycle={cycle_index}: {duration}ms')
            jump_results.append({'durationMs': duration})
        else:
            logical_segment = spec['segmentMs'][movement_index]
            movement_results.append(
                validate_movement_cycle(
                    f'{ident}.segment{movement_index}', d, cycle, logical_segment
                )
            )
            movement_index += 1

    if (spec['logicalHoldMs'], spec['logicalHoldMs'], spec['tapCount']) not in actual_completion_counts:
        raise SystemExit('missing authoritative route completion: ' + ident)

    for tap_index, (offset, movement_done) in enumerate(zip(spec['tapOffsets'], [0] + spec['movementDoneMs'][:-1])):
        marker = (
            f'tapAccepted=true display=0 logicalHoldMs={spec["logicalHoldMs"]} '
            f'tapIndex={tap_index} offsetMs={offset} movementDoneMs={movement_done}'
        )
        if marker not in text:
            raise SystemExit('missing exact serialized tap marker: ' + marker)

    for segment_index, (segment_ms, movement_done) in enumerate(zip(spec['segmentMs'], spec['movementDoneMs'])):
        marker = (
            f'segmentCompleted=true display=0 logicalHoldMs={spec["logicalHoldMs"]} '
            f'segmentIndex={segment_index} segmentMs={segment_ms} movementDoneMs={movement_done}'
        )
        if marker not in text:
            raise SystemExit('missing exact movement segment marker: ' + marker)

    receiver_wall = max(e['t'] for e in ev) - min(e['t'] for e in ev)
    report['routeSequences'][ident] = {
        'logicalFullDeflectionMs': spec['logicalHoldMs'],
        'tapOffsetsMs': spec['tapOffsets'],
        'jumpDurationsMs': [x['durationMs'] for x in jump_results],
        'movementSegments': movement_results,
        'receiverWallClockMs': receiver_wall,
        'serializedWallClockOverheadMs': receiver_wall - spec['logicalHoldMs'],
    }

out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print('PASS: API35 screen-space joystick geometry/timing measured under unchanged strict budget; Roblox stud calibration intentionally not claimed')

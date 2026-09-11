#!/usr/bin/env python3
from pathlib import Path
from runpy import run_path

TOOLS = Path(__file__).resolve().parent

# Preserve the already-proven template matcher + real-phone foreground patch,
# then apply the isolated joystick serializer, callback-thread scheduling,
# prequeued continuation timing, and desktop MoveSpeed parity stages.
# The rejected same-GestureDescription atomic continuation experiment remains
# in tools for provenance but is intentionally not part of this pipeline.
for script in (
    TOOLS / 'patch-native-v0212-template-core.py',
    TOOLS / 'patch-native-v0212-joystick-hold.py',
    TOOLS / 'patch-native-v0212-joystick-callback-thread.py',
    TOOLS / 'patch-native-v0212-joystick-prequeue-continuation.py',
    TOOLS / 'patch-native-v0212-movement-speed.py',
):
    if not script.exists():
        raise SystemExit(f'missing v0.2.12 patch stage: {script}')
    run_path(str(script), run_name='__main__')

print('PASS: applied v0.2.12 template/foreground, full-deflection joystick, dedicated callbacks, prequeued continuation timing, and desktop MoveSpeed stages')

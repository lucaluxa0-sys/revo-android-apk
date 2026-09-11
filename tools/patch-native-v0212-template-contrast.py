#!/usr/bin/env python3
from pathlib import Path
from runpy import run_path

TOOLS = Path(__file__).resolve().parent

# Preserve the already-proven template matcher + real-phone foreground patch,
# then apply the isolated joystick serializer, callback-thread scheduling, and
# desktop MoveSpeed parity stages. The atomic same-gesture continuation experiment
# remains in tools for provenance, but is intentionally excluded: API 35 cancelled
# every movement segment when the original and continued strokes shared one gesture.
for script in (
    TOOLS / 'patch-native-v0212-template-core.py',
    TOOLS / 'patch-native-v0212-joystick-hold.py',
    TOOLS / 'patch-native-v0212-joystick-callback-thread.py',
    TOOLS / 'patch-native-v0212-movement-speed.py',
):
    if not script.exists():
        raise SystemExit(f'missing v0.2.12 patch stage: {script}')
    run_path(str(script), run_name='__main__')

print('PASS: applied v0.2.12 template/foreground, full-deflection joystick, dedicated gesture callbacks, and desktop MoveSpeed timing stages')

#!/usr/bin/env python3
from pathlib import Path
from runpy import run_path

TOOLS = Path(__file__).resolve().parent

# Preserve the already-proven template matcher + real-phone foreground patch
# byte-for-byte, then apply the isolated Android joystick parity correction.
for script in (
    TOOLS / 'patch-native-v0212-template-core.py',
    TOOLS / 'patch-native-v0212-joystick-hold.py',
):
    if not script.exists():
        raise SystemExit(f'missing v0.2.12 patch stage: {script}')
    run_path(str(script), run_name='__main__')

print('PASS: applied v0.2.12 template/foreground core plus full-deflection joystick hold')

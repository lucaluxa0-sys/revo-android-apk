#!/usr/bin/env python3
import re
from pathlib import Path

JAVA = Path('revo-android/app/src/main/java/com/revolution/android')
MANIFEST = Path('revo-android/app/src/main/AndroidManifest.xml')
SERVICE = JAVA / 'RevoAccessibilityService.java'
RECEIVER = JAVA / 'RevoPhysicsProbeReceiver.java'
BACKEND = Path('patches/android-backend-v0.2.9.js')

for path in (MANIFEST, SERVICE, BACKEND):
    if not path.exists():
        raise SystemExit(f'missing production input: {path}')

svc = SERVICE.read_text(encoding='utf-8')
for marker in ('runJoystickTapSequence', 'fullDeflectionMs=', 'joystickWithTimedTaps'):
    if marker not in svc:
        raise SystemExit(f'production joystick adaptation missing marker: {marker}')

backend = BACKEND.read_text(encoding='utf-8')

def production_default(prop, storage_key):
    pattern = re.compile(
        rf"{re.escape(prop)}\s*:\s*localNumber\(\s*'{re.escape(storage_key)}'\s*,\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*\)"
    )
    matches = pattern.findall(backend)
    if len(matches) != 1:
        raise SystemExit(
            f'expected exactly one production default for {prop}/{storage_key}, got {matches!r}'
        )
    return matches[0]

geometry = {
    '__JOY_X__': production_default('joystickCenterX', 'revo.android.joystickCenterX'),
    '__JOY_Y__': production_default('joystickCenterY', 'revo.android.joystickCenterY'),
    '__JOY_R__': production_default('joystickRadius', 'revo.android.joystickRadius'),
    '__JUMP_X__': production_default('jumpX', 'revo.android.jumpX'),
    '__JUMP_Y__': production_default('jumpY', 'revo.android.jumpY'),
}

if RECEIVER.exists():
    raise SystemExit('CI physics receiver already exists')

receiver = r'''package com.revolution.android;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.graphics.Point;
import android.util.Log;
import android.view.Display;
import android.view.WindowManager;

/** CI-only entry point that calls the real production Accessibility joystick adapter. */
public final class RevoPhysicsProbeReceiver extends BroadcastReceiver {
    private static final String TAG = "RevoPhysicsProbe";
    private static final String GEOMETRY_SOURCE = "android-backend-v0.2.9.js";

    @Override public void onReceive(Context context, Intent intent) {
        RevoAccessibilityService svc = RevoAccessibilityService.get();
        String id = intent == null ? "" : intent.getStringExtra("id");
        String mode = intent == null ? "" : intent.getStringExtra("mode");
        int holdMs = intent == null ? 0 : intent.getIntExtra("holdMs", 0);
        if (id == null) id = "";
        if (mode == null) mode = "";
        if (svc == null) {
            Log.e(TAG, "PHYSICS_DISPATCH id=" + id + " serviceMissing=true");
            return;
        }

        WindowManager wm = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
        Display display = wm.getDefaultDisplay();
        Point size = new Point();
        display.getRealSize(size);
        int displayId = display.getDisplayId();
        float w = size.x, h = size.y;
        // These literals are generated from the production Android backend defaults.
        // Radius follows the production native adapter: normalized against min(width,height).
        float cx = w * __JOY_X__f, cy = h * __JOY_Y__f;
        float r = Math.min(w, h) * __JOY_R__f;
        float jumpX = w * __JUMP_X__f, jumpY = h * __JUMP_Y__f;
        float tx, ty;
        boolean accepted;

        if ("right".equals(mode) || "double-1650".equals(mode)) {
            tx = cx + r; ty = cy;
        } else {
            float q = (float)(r / Math.sqrt(2.0));
            tx = cx - q; ty = cy - q;
        }

        Log.i(TAG, "PHYSICS_DISPATCH id=" + id
                + " mode=" + mode + " holdMs=" + holdMs
                + " display=" + displayId + " w=" + size.x + " h=" + size.y
                + " geometrySource=" + GEOMETRY_SOURCE
                + " cx=" + cx + " cy=" + cy + " r=" + r
                + " tx=" + tx + " ty=" + ty
                + " jumpX=" + jumpX + " jumpY=" + jumpY);

        if ("right".equals(mode) || "diag-forward-left".equals(mode)) {
            accepted = svc.joystick(displayId, cx, cy, tx, ty, holdMs);
        } else if ("double-1650".equals(mode)) {
            accepted = svc.joystickWithDoubleTap(
                    displayId, cx, cy, tx, ty, 1650,
                    jumpX, jumpY, 70, 1300);
        } else if ("timed-6050".equals(mode)) {
            accepted = svc.joystickWithTimedTaps(
                    displayId, cx, cy, tx, ty, 6050,
                    jumpX, jumpY, 70, new long[]{0L, 850L, 5670L});
        } else {
            Log.e(TAG, "PHYSICS_DISPATCH id=" + id + " unknownMode=" + mode);
            return;
        }
        Log.i(TAG, "PHYSICS_ACCEPTED id=" + id + " accepted=" + accepted);
    }
}
'''
for placeholder, value in geometry.items():
    receiver = receiver.replace(placeholder, value)
if '__JOY_' in receiver or '__JUMP_' in receiver:
    raise SystemExit('unresolved production geometry placeholder in CI receiver')
RECEIVER.write_text(receiver, encoding='utf-8')

text = MANIFEST.read_text(encoding='utf-8')
if 'RevoPhysicsProbeReceiver' in text:
    raise SystemExit('CI physics receiver manifest entry already exists')
marker = '</application>'
if text.count(marker) != 1:
    raise SystemExit('unexpected AndroidManifest application count')
entry = '''        <receiver android:name=".RevoPhysicsProbeReceiver" android:exported="true">\n            <intent-filter><action android:name="com.revolution.android.PHYSICS_PROBE" /></intent-filter>\n        </receiver>\n'''
MANIFEST.write_text(text.replace(marker, entry + marker, 1), encoding='utf-8')
print('Injected CI-only v0.2.12 joystick screen-physics receiver')
print('Production geometry source:', BACKEND)
print('Production geometry defaults:', geometry)

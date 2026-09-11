#!/usr/bin/env python3
from pathlib import Path

SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')

if not SERVICE.exists():
    raise SystemExit('RevoAccessibilityService.java missing; apply joystick hold patch first')

svc = SERVICE.read_text(encoding='utf-8')

if 'JOYSTICK_CALLBACK_HANDLER' in svc:
    raise SystemExit('dedicated joystick callback handler already present')

anchor = '    private static final long JOYSTICK_ACQUIRE_MS = 35L;\n'
insert = r'''    private static final long JOYSTICK_ACQUIRE_MS = 35L;
    private static final android.os.HandlerThread JOYSTICK_CALLBACK_THREAD =
            createJoystickCallbackThread();
    private static final android.os.Handler JOYSTICK_CALLBACK_HANDLER =
            new android.os.Handler(JOYSTICK_CALLBACK_THREAD.getLooper());

    private static android.os.HandlerThread createJoystickCallbackThread() {
        android.os.HandlerThread thread = new android.os.HandlerThread(
                "RevoJoystickCallbacks", android.os.Process.THREAD_PRIORITY_DISPLAY);
        thread.start();
        return thread;
    }
'''
if svc.count(anchor) != 1:
    raise SystemExit('joystick callback-thread insertion anchor missing or duplicated')
svc = svc.replace(anchor, insert, 1)

start_marker = '    private boolean dispatchJoystickSegment('
end_marker = '    /**\n     * Continue a desktop movement/tap command'
start = svc.find(start_marker)
end = svc.find(end_marker, start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('joystick callback dispatch region missing')
region = svc[start:end]

null_callbacks = region.count('                }, null);')
if null_callbacks != 3:
    raise SystemExit(f'expected exactly 3 main-thread joystick callback handlers, found {null_callbacks}')
region = region.replace('                }, null);', '                }, JOYSTICK_CALLBACK_HANDLER);')
svc = svc[:start] + region + svc[end:]

log_anchor = '                        + " tapAdaptation=serialized-between-full-deflection-segments-v1");'
log_replacement = '''                        + " tapAdaptation=serialized-between-full-deflection-segments-v1"
                        + " callbackHandler=dedicated-handler-thread-v1");'''
if svc.count(log_anchor) != 1:
    raise SystemExit('joystick callback-thread diagnostic log anchor missing or duplicated')
svc = svc.replace(log_anchor, log_replacement, 1)

required = (
    'JOYSTICK_CALLBACK_THREAD',
    'JOYSTICK_CALLBACK_HANDLER',
    'RevoJoystickCallbacks',
    'THREAD_PRIORITY_DISPLAY',
    'callbackHandler=dedicated-handler-thread-v1',
)
missing = [item for item in required if item not in svc]
if missing:
    raise SystemExit('joystick callback-thread patch incomplete: ' + repr(missing))

post_start = svc.find(start_marker)
post_end = svc.find(end_marker, post_start)
post_region = svc[post_start:post_end]
if post_region.count('JOYSTICK_CALLBACK_HANDLER);') != 3:
    raise SystemExit('not all joystick result callbacks use dedicated handler')
if '}, null);' in post_region:
    raise SystemExit('joystick callback region still contains a main-thread result callback')

SERVICE.write_text(svc, encoding='utf-8')
print('PASS: moved v0.2.12 joystick gesture-result callbacks off the Accessibility main looper')

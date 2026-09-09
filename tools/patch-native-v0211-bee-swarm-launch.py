#!/usr/bin/env python3
from pathlib import Path
import re

p = Path('revo-android/app/src/main/java/com/revolution/android/AndroidRevoBridge.java')
s = p.read_text()

start_pat = re.compile(
    r'@JavascriptInterface public boolean startMacroAndRoblox\(String account\) \{\s*'
    r'engine\(\)\.start\(\);\s*'
    r'return launchRoblox\(\);\s*'
    r'\}',
    re.S,
)
start_repl = '''@JavascriptInterface public boolean startMacroAndRoblox(String account) {
        boolean launched = launchRoblox();
        if (launched) engine().start();
        return launched;
    }'''
s, n = start_pat.subn(start_repl, s)
if n != 1:
    raise SystemExit(f'expected exactly one startMacroAndRoblox replacement, got {n}')

launch_pat = re.compile(
    r'@JavascriptInterface public boolean launchRoblox\(\) \{.*?\n    \}\n\n    @JavascriptInterface public boolean tap',
    re.S,
)
launch_repl = '''@JavascriptInterface public boolean launchRoblox() {
        final String beeSwarmUri = "roblox://placeId=1537690962";
        String[] packages = new String[]{"com.roblox.client", "com.roblox.client.samsunggalaxy"};
        for (String pkg : packages) {
            // Keep the existing package-presence probe, but launch the actual Bee Swarm
            // place instead of Roblox's generic launcher activity.
            Intent installed = activity.getPackageManager().getLaunchIntentForPackage(pkg);
            if (installed == null) continue;

            Intent launch = new Intent(Intent.ACTION_VIEW, android.net.Uri.parse(beeSwarmUri));
            launch.setPackage(pkg);
            launch.addCategory(Intent.CATEGORY_BROWSABLE);
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            int displayId = getDisplayId();
            activity.runOnUiThread(() -> {
                ActivityOptions options = ActivityOptions.makeBasic();
                options.setLaunchDisplayId(displayId);
                android.util.Log.i("RevoAndroid", "Launching Bee Swarm via " + beeSwarmUri + " package=" + pkg + " display=" + displayId);
                activity.startActivity(launch, options.toBundle());
            });
            return true;
        }
        android.util.Log.e("RevoAndroid", "Roblox package not installed; Bee Swarm launch aborted");
        return false;
    }

    @JavascriptInterface public boolean tap'''
s, n = launch_pat.subn(launch_repl, s)
if n != 1:
    raise SystemExit(f'expected exactly one launchRoblox replacement, got {n}')

if 'roblox://placeId=1537690962' not in s:
    raise SystemExit('Bee Swarm URI missing after patch')
if 'getLaunchIntentForPackage(pkg);' not in s:
    raise SystemExit('package presence probe unexpectedly missing')

p.write_text(s)
print('PASS: patched AndroidRevoBridge Start -> Bee Swarm direct deep link')

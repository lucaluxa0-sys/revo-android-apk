#!/usr/bin/env python3
from pathlib import Path

gradle = Path("revo-android/app/build.gradle.kts")
manifest = Path("revo-android/app/src/main/AndroidManifest.xml")
agent = Path("revo-android/app/src/main/java/com/revolution/android/RevoRemoteAgent.java")

g = gradle.read_text(encoding="utf-8")
old = 'applicationId = "com.revolution.android"'
new = 'applicationId = "com.revolution.android.route203test"'
if old not in g:
    raise SystemExit("test package applicationId anchor missing")
gradle.write_text(g.replace(old, new, 1), encoding="utf-8")

m = manifest.read_text(encoding="utf-8")
old = 'android:label="Revolution Macro"'
new = 'android:label="Revolution Macro Route203 Test"'
if old not in m:
    raise SystemExit("test package label anchor missing")
manifest.write_text(m.replace(old, new, 1), encoding="utf-8")

s = agent.read_text(encoding="utf-8")
old = "public static final int PORT = 38421;"
new = "public static final int PORT = 38422;"
if old not in s:
    raise SystemExit("test remote port anchor missing")
s = s.replace(old, new, 1)

old = '''        }
    }

    public boolean isPaired() {
'''
new = '''        }
        Log.i(TAG, "ROUTE203_TEST_PAIR_CODE=" + pairingCode);
    }

    public boolean isPaired() {
'''
if old not in s:
    raise SystemExit("test pair log anchor missing")
s = s.replace(old, new, 1)
agent.write_text(s, encoding="utf-8")

print("PASS: route203 side-by-side test package com.revolution.android.route203test port=38422")

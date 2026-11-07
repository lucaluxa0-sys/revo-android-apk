#!/usr/bin/env python3
"""Create clearly distinct research APK resources in disposable reconstructed source."""
import argparse
import re
import shutil
from pathlib import Path

def replace_once(text, old, new, name):
    if text.count(old) != 1:
        raise ValueError(f'{name} source anchor missing/duplicated')
    return text.replace(old, new, 1)

def prepare(root: Path):
    root=root.resolve()
    app=root/'app'
    java=app/'src/main/java/com/revolution/android/MainActivity.java'
    manifest=app/'src/main/AndroidManifest.xml'
    strings=app/'src/main/res/values/strings.xml'
    gradle=app/'build.gradle.kts'
    for f in (java,manifest,strings,gradle):
        if not f.is_file():raise ValueError(f'reconstructed native source missing: {f}')
    project=Path(__file__).resolve().parent.parent
    www=app/'src/main/assets/www'
    www.mkdir(parents=True,exist_ok=True)
    for name in ('index.android.html','research-ui.js','research-ui.css'):
        shutil.copy2(project/'ui'/name,www/name)
    plan=www/'revo-plans/e_lol.json'
    plan.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(project/'plans/e_lol.json',plan)
    js=java.read_text(encoding='utf-8')
    js=replace_once(js,
        '''        if (getIntent() != null && getIntent().getBooleanExtra("autostart", false)) {
            autostartWhenReady(0);
        }''',
        '        // Research build: never autostart from an activity intent.',
        'research autoplay guard')
    js=replace_once(js,'        remoteAgent.start();',
        '        // Research build: remote-agent listener intentionally disabled.',
        'remote agent startup guard')
    js=replace_once(js,
        '''        if (!remoteAgent.isPaired() && remoteAgent.getPairingCode() != null) {
            android.widget.Toast.makeText(this,
                    "Revo remote pairing code: " + remoteAgent.getPairingCode() + " (10 min)",
                    android.widget.Toast.LENGTH_LONG).show();
        }''',
        '        // Research build: no remote pairing or toast is exposed.',
        'remote pairing toast')
    java.write_text(js,encoding='utf-8')
    text=manifest.read_text(encoding='utf-8')
    text=replace_once(text,'android:label="Revolution Macro"',
        'android:label="Revo REA Research"','research app label')
    manifest.write_text(text,encoding='utf-8')
    text=strings.read_text(encoding='utf-8')
    text=replace_once(text,'<string name="app_name">Revolution Macro</string>',
        '<string name="app_name">Revo REA Research</string>',
        'research app name')
    strings.write_text(text,encoding='utf-8')
    text=gradle.read_text(encoding='utf-8')
    text=replace_once(text,'applicationId = "com.revolution.android"',
        'applicationId = "com.revolution.android.rearesearch"',
        'isolated research package ID')
    text,count=re.subn(r'versionName\s*=\s*"[^"]+"',
        'versionName = "0.2.12-rea-research"',text,count=1)
    if count!=1:raise ValueError('missing research version stamp')
    gradle.write_text(text,encoding='utf-8')
    print('PASS: research preview UI, distinct package, no auto-start or remote listener')
    print('PACKAGE com.revolution.android.rearesearch')
    print('FRONTEND',www)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--android-root',required=True)
    args=ap.parse_args()
    prepare(Path(args.android_root))

if __name__=='__main__':
    main()

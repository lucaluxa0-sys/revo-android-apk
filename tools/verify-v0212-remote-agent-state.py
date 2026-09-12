#!/usr/bin/env python3
import ast
import pathlib
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-v0212-remote-agent-state.py <patch-native-v0212-remote-agent.py>')

patch = pathlib.Path(sys.argv[1])
source = patch.read_text()
module = ast.parse(source, filename=str(patch))
agent = None
for node in module.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'agent_source' for t in node.targets):
        agent = ast.literal_eval(node.value)
        break
if not isinstance(agent, str):
    raise SystemExit('FAIL: agent_source string not found')

def require(needle, message):
    if needle not in agent:
        raise SystemExit(f'FAIL: {message}: missing {needle!r}')

def forbid(needle, message):
    if needle in agent:
        raise SystemExit(f'FAIL: {message}: found {needle!r}')

forbid('private volatile boolean remoteRunActive;', 'remote liveness must not be a stale standalone boolean')
require('import org.json.JSONObject;', 'agent must parse authoritative bridge JSON')
require('private EngineSnapshot readEngineSnapshot()', 'authoritative engine snapshot reader required')
require('if (!json.has("running"))', 'running field must be required before commands trust state')
require('private static final long COMMAND_TRANSITION_MS = 25L * 1000L;', 'async Start lock must cover UI retry window')
require('if (!state.known)', 'Start/Sunflower must fail closed when engine state is unknown')
require('respond(s, 503, json("error", "engine_state_unavailable"));', 'unknown state must return 503')
require('if (state.running && !state.paused)', 'generic Start must reject an already-running non-paused engine')
require('if (state.running) {', 'Sunflower must reject every active run, including paused runs')
require('if ("stopping".equals(remoteTransition))', 'duplicate Stop must be idempotent')
require('beginTransition("stopping");', 'Stop must supersede a settling Start/unknown state')
require('return (state.known && state.running) || "starting".equals(remoteTransition);', 'compat remoteRunActive status must be derived, not stored')
require('code == 503 ? "Service Unavailable"', '503 reason phrase must be emitted')
require('\\"engineKnown\\"', 'status must expose engine authority')
require('\\"engineRunning\\"', 'status must expose actual running state')
require('\\"enginePaused\\"', 'status must expose actual pause state')
require('\\"transition\\"', 'status must expose pending command transition')

javac = shutil.which('javac')
if not javac:
    raise SystemExit('FAIL: javac not found; Java compile is part of this regression gate')

with tempfile.TemporaryDirectory(prefix='revo-remote-agent-') as td:
    root = pathlib.Path(td) / 'src'
    files = {
        'com/revolution/android/RevoRemoteAgent.java': agent,
        'android/content/Context.java': '''package android.content; public class Context { public static final int MODE_PRIVATE=0; public Context getApplicationContext(){return this;} public SharedPreferences getSharedPreferences(String n,int m){return new SharedPreferences();} }''',
        'android/content/SharedPreferences.java': '''package android.content; public class SharedPreferences { public String getString(String k,String d){return d;} public Editor edit(){return new Editor();} public static class Editor { public Editor putString(String k,String v){return this;} public void apply(){} } }''',
        'android/util/Base64.java': '''package android.util; public class Base64 { public static final int URL_SAFE=8,NO_WRAP=2,NO_PADDING=1; public static String encodeToString(byte[] b,int f){return "token";} }''',
        'android/util/Log.java': '''package android.util; public class Log { public static int i(String t,String m){return 0;} public static int w(String t,String m){return 0;} public static int w(String t,String m,Throwable x){return 0;} public static int e(String t,String m,Throwable x){return 0;} }''',
        'org/json/JSONObject.java': '''package org.json; public class JSONObject { public JSONObject(String s){} public boolean has(String k){return true;} public boolean optBoolean(String k,boolean d){return d;} public String optString(String k,String d){return d;} }''',
    }
    java_files = []
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        java_files.append(str(p))
    out = pathlib.Path(td) / 'out'
    out.mkdir()
    proc = subprocess.run([javac, '-d', str(out), *java_files], text=True, capture_output=True)
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit('FAIL: generated RevoRemoteAgent.java did not compile')

print('PASS: remote agent derives liveness from engine JSON, fail-closes Start, permits safe Stop, and generated Java compiles')

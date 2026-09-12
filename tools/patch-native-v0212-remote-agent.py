#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path('revo-android')
MAIN = ROOT / 'app/src/main/java/com/revolution/android/MainActivity.java'
MANIFEST = ROOT / 'app/src/main/AndroidManifest.xml'
AGENT = ROOT / 'app/src/main/java/com/revolution/android/RevoRemoteAgent.java'

if not MAIN.exists():
    raise SystemExit(f'MainActivity missing: {MAIN}')
if not MANIFEST.exists():
    raise SystemExit(f'AndroidManifest missing: {MANIFEST}')

agent_source = r'''package com.revolution.android;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Base64;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Narrow, authenticated control surface for physical-phone regression tests.
 * Deliberately exposes no shell, filesystem, package-install, or arbitrary-code endpoint.
 */
public final class RevoRemoteAgent {
    public interface Hooks {
        String status();
        void start();
        void stop();
        void sunflower();
    }

    private static final String TAG = "RevoRemoteAgent";
    public static final int PORT = 38421;
    private static final long PAIR_WINDOW_MS = 10L * 60L * 1000L;
    // startRemoteMacroWhenReady retries for up to ~20 seconds. Keep the remote
    // transition locked slightly longer so two HTTP commands cannot stack while
    // the UI bridge is still looking for a usable Start button.
    private static final long COMMAND_TRANSITION_MS = 25L * 1000L;
    private static final String PREFS = "revo_remote_agent";
    private static final String TOKEN_KEY = "bearer_token_v1";

    private final Context context;
    private final Hooks hooks;
    private final SharedPreferences prefs;
    private final SecureRandom random = new SecureRandom();
    private final Object commandLock = new Object();
    private volatile boolean alive;
    private volatile String remoteTransition = ""; // "starting" | "stopping" | ""
    private volatile long remoteTransitionSince;
    private ServerSocket server;
    private final String pairingCode;
    private final long pairExpiresAt;

    private static final class EngineSnapshot {
        final boolean known;
        final boolean running;
        final boolean paused;
        final String status;
        final String raw;

        EngineSnapshot(boolean known, boolean running, boolean paused, String status, String raw) {
            this.known = known;
            this.running = running;
            this.paused = paused;
            this.status = status == null ? "" : status;
            this.raw = raw == null ? "" : raw;
        }
    }

    public RevoRemoteAgent(Context context, Hooks hooks) {
        this.context = context.getApplicationContext();
        this.hooks = hooks;
        this.prefs = this.context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (isPaired()) {
            pairingCode = null;
            pairExpiresAt = 0L;
        } else {
            pairingCode = String.format(Locale.US, "%06d", random.nextInt(1_000_000));
            pairExpiresAt = System.currentTimeMillis() + PAIR_WINDOW_MS;
        }
    }

    public boolean isPaired() {
        return !prefs.getString(TOKEN_KEY, "").isEmpty();
    }

    public String getPairingCode() {
        return pairingCode;
    }

    public void start() {
        if (alive) return;
        alive = true;
        Thread thread = new Thread(this::serve, "revo-remote-agent");
        thread.setDaemon(true);
        thread.start();
    }

    public void close() {
        alive = false;
        try { if (server != null) server.close(); } catch (Exception ignored) {}
    }

    private EngineSnapshot readEngineSnapshot() {
        String raw;
        try {
            raw = hooks.status();
        } catch (Exception e) {
            return new EngineSnapshot(false, false, false, "ERROR:" + e.getClass().getSimpleName(), "");
        }
        if (raw == null || raw.trim().isEmpty() || "BRIDGE_NOT_READY".equals(raw)) {
            return new EngineSnapshot(false, false, false, "BRIDGE_NOT_READY", raw);
        }
        try {
            JSONObject json = new JSONObject(raw);
            if (!json.has("running")) {
                return new EngineSnapshot(false, false, false, "ENGINE_STATE_MISSING_RUNNING", raw);
            }
            boolean running = json.optBoolean("running", false);
            boolean paused = json.optBoolean("paused", false);
            String status = json.optString("status", running ? "Running" : "Stopped");
            return new EngineSnapshot(true, running, paused, status, raw);
        } catch (Exception e) {
            return new EngineSnapshot(false, false, false, "ENGINE_STATE_PARSE_ERROR", raw);
        }
    }

    private void beginTransition(String transition) {
        remoteTransition = transition;
        remoteTransitionSince = System.currentTimeMillis();
    }

    private void clearTransition() {
        remoteTransition = "";
        remoteTransitionSince = 0L;
    }

    private void reconcileTransition(EngineSnapshot state) {
        String transition = remoteTransition;
        if (transition.isEmpty()) return;
        long age = Math.max(0L, System.currentTimeMillis() - remoteTransitionSince);
        if ("starting".equals(transition) && state.known && state.running) {
            clearTransition();
            return;
        }
        if ("stopping".equals(transition) && state.known && !state.running) {
            clearTransition();
            return;
        }
        if (age >= COMMAND_TRANSITION_MS) {
            Log.w(TAG, "clearing stale remote transition=" + transition + " ageMs=" + age +
                    " engineKnown=" + state.known + " running=" + state.running);
            clearTransition();
        }
    }

    private boolean remoteActive(EngineSnapshot state) {
        return (state.known && state.running) || "starting".equals(remoteTransition);
    }

    private void serve() {
        try {
            server = new ServerSocket();
            server.setReuseAddress(true);
            server.bind(new InetSocketAddress("0.0.0.0", PORT));
            Log.i(TAG, "listening on port " + PORT + "; paired=" + isPaired());
            while (alive) {
                final Socket socket = server.accept();
                Thread worker = new Thread(() -> handle(socket), "revo-agent-client");
                worker.setDaemon(true);
                worker.start();
            }
        } catch (Exception e) {
            if (alive) Log.e(TAG, "server failed", e);
        } finally {
            try { if (server != null) server.close(); } catch (Exception ignored) {}
            server = null;
        }
    }

    private void handle(Socket socket) {
        try (Socket s = socket) {
            s.setSoTimeout(5000);
            BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
            String requestLine = in.readLine();
            if (requestLine == null) return;
            String[] first = requestLine.split(" ");
            if (first.length < 2) {
                respond(s, 400, json("error", "bad_request"));
                return;
            }
            String method = first[0];
            String path = first[1].split("\\?", 2)[0];
            Map<String, String> headers = new HashMap<>();
            String line;
            while ((line = in.readLine()) != null && !line.isEmpty()) {
                int colon = line.indexOf(':');
                if (colon > 0) {
                    headers.put(line.substring(0, colon).trim().toLowerCase(Locale.US), line.substring(colon + 1).trim());
                }
            }

            if ("GET".equals(method) && "/v1/ping".equals(path)) {
                respond(s, 200, "{\"agent\":\"revo-physical-v1\",\"paired\":" + isPaired() + ",\"port\":" + PORT + "}");
                return;
            }
            if ("POST".equals(method) && "/v1/pair".equals(path)) {
                handlePair(s, headers);
                return;
            }
            if (!authorized(headers)) {
                respond(s, 401, json("error", "unauthorized"));
                return;
            }
            if ("GET".equals(method) && "/v1/status".equals(path)) {
                EngineSnapshot state;
                synchronized (commandLock) {
                    state = readEngineSnapshot();
                    reconcileTransition(state);
                }
                respond(s, 200, "{\"remoteRunActive\":" + remoteActive(state) +
                        ",\"engineKnown\":" + state.known +
                        ",\"engineRunning\":" + state.running +
                        ",\"enginePaused\":" + state.paused +
                        ",\"transition\":\"" + escape(remoteTransition) + "\"" +
                        ",\"engineStatus\":\"" + escape(state.status) + "\"" +
                        ",\"engineState\":\"" + escape(state.raw) + "\"}");
                return;
            }
            if ("POST".equals(method) && "/v1/start".equals(path)) {
                synchronized (commandLock) {
                    EngineSnapshot state = readEngineSnapshot();
                    reconcileTransition(state);
                    if (!state.known) {
                        respond(s, 503, json("error", "engine_state_unavailable"));
                        return;
                    }
                    if (!remoteTransition.isEmpty()) {
                        respond(s, 409, json("error", "command_in_progress"));
                        return;
                    }
                    if (state.running && !state.paused) {
                        respond(s, 409, json("error", "already_running"));
                        return;
                    }
                    beginTransition("starting");
                    try {
                        hooks.start();
                    } catch (Exception e) {
                        clearTransition();
                        respond(s, 500, json("error", "start_failed"));
                        return;
                    }
                }
                respond(s, 202, json("accepted", "start"));
                return;
            }
            if ("POST".equals(method) && "/v1/sunflower-e2e".equals(path)) {
                synchronized (commandLock) {
                    EngineSnapshot state = readEngineSnapshot();
                    reconcileTransition(state);
                    if (!state.known) {
                        respond(s, 503, json("error", "engine_state_unavailable"));
                        return;
                    }
                    if (!remoteTransition.isEmpty()) {
                        respond(s, 409, json("error", "command_in_progress"));
                        return;
                    }
                    // The bounded Sunflower run mutates the active pattern before
                    // pressing Start, so do not apply it on top of even a paused run.
                    if (state.running) {
                        respond(s, 409, json("error", "already_running"));
                        return;
                    }
                    beginTransition("starting");
                    try {
                        hooks.sunflower();
                    } catch (Exception e) {
                        clearTransition();
                        respond(s, 500, json("error", "sunflower_start_failed"));
                        return;
                    }
                }
                respond(s, 202, json("accepted", "sunflower-e2e"));
                return;
            }
            if ("POST".equals(method) && "/v1/stop".equals(path)) {
                synchronized (commandLock) {
                    EngineSnapshot state = readEngineSnapshot();
                    reconcileTransition(state);
                    if ("stopping".equals(remoteTransition)) {
                        respond(s, 202, json("accepted", "stop-pending"));
                        return;
                    }
                    if (state.known && !state.running && !"starting".equals(remoteTransition)) {
                        clearTransition();
                        respond(s, 200, json("status", "already_stopped"));
                        return;
                    }
                    // Stop is intentionally allowed when engine state is unknown or
                    // while Start is still settling: it only reduces control activity.
                    beginTransition("stopping");
                    try {
                        hooks.stop();
                    } catch (Exception e) {
                        clearTransition();
                        respond(s, 500, json("error", "stop_failed"));
                        return;
                    }
                }
                respond(s, 202, json("accepted", "stop"));
                return;
            }
            respond(s, 404, json("error", "not_found"));
        } catch (Exception e) {
            Log.w(TAG, "request failed", e);
        }
    }

    private void handlePair(Socket s, Map<String, String> headers) throws Exception {
        if (isPaired()) {
            respond(s, 409, json("error", "already_paired"));
            return;
        }
        if (pairingCode == null || System.currentTimeMillis() > pairExpiresAt) {
            respond(s, 410, json("error", "pairing_window_expired"));
            return;
        }
        String supplied = headers.getOrDefault("x-revo-pair-code", "");
        if (!constantTime(pairingCode, supplied)) {
            respond(s, 403, json("error", "bad_pair_code"));
            return;
        }
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        String token = Base64.encodeToString(bytes, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
        prefs.edit().putString(TOKEN_KEY, token).apply();
        respond(s, 200, "{\"token\":\"" + token + "\"}");
        Log.i(TAG, "paired successfully");
    }

    private boolean authorized(Map<String, String> headers) {
        String token = prefs.getString(TOKEN_KEY, "");
        if (token.isEmpty()) return false;
        String auth = headers.getOrDefault("authorization", "");
        String prefix = "Bearer ";
        if (!auth.startsWith(prefix)) return false;
        return constantTime(token, auth.substring(prefix.length()));
    }

    private static boolean constantTime(String a, String b) {
        return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    private static String escape(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", "\\r").replace("\n", "\\n");
    }

    private static String json(String key, String value) {
        return "{\"" + escape(key) + "\":\"" + escape(value) + "\"}";
    }

    private static void respond(Socket socket, int code, String body) throws Exception {
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        String reason = code == 200 ? "OK" : code == 202 ? "Accepted" : code == 400 ? "Bad Request" :
                code == 401 ? "Unauthorized" : code == 403 ? "Forbidden" : code == 404 ? "Not Found" :
                code == 409 ? "Conflict" : code == 410 ? "Gone" : code == 500 ? "Internal Server Error" :
                code == 503 ? "Service Unavailable" : "Error";
        String head = "HTTP/1.1 " + code + " " + reason + "\r\n" +
                "Content-Type: application/json; charset=utf-8\r\n" +
                "Content-Length: " + payload.length + "\r\n" +
                "Connection: close\r\n" +
                "Cache-Control: no-store\r\n\r\n";
        OutputStream out = socket.getOutputStream();
        out.write(head.getBytes(StandardCharsets.US_ASCII));
        out.write(payload);
        out.flush();
    }
}
'''

AGENT.parent.mkdir(parents=True, exist_ok=True)
AGENT.write_text(agent_source)

manifest = MANIFEST.read_text()
if 'android.permission.INTERNET' not in manifest:
    manifest = re.sub(
        r'(<manifest[^>]*>)',
        r'\1\n    <uses-permission android:name="android.permission.INTERNET" />',
        manifest,
        count=1,
    )
MANIFEST.write_text(manifest)

s = MAIN.read_text()
if 'RevoRemoteAgent remoteAgent' not in s:
    class_anchor = re.search(r'(public\s+(?:final\s+)?class\s+MainActivity\b[^\{]*\{)', s)
    if not class_anchor:
        raise SystemExit('MainActivity class anchor missing')
    insert_at = class_anchor.end()
    s = s[:insert_at] + '\n    private RevoRemoteAgent remoteAgent;\n' + s[insert_at:]

marker = '''        if (getIntent() != null && getIntent().getBooleanExtra("autostart", false)) {
            autostartWhenReady(0);
        }'''
if marker not in s:
    raise SystemExit('MainActivity autostart marker missing')

install = marker + r'''

        remoteAgent = new RevoRemoteAgent(this, new RevoRemoteAgent.Hooks() {
            @Override public String status() {
                return bridge == null ? "BRIDGE_NOT_READY" : bridge.getEngineState();
            }

            @Override public void start() {
                runOnUiThread(() -> startRemoteMacroWhenReady(false, 0));
            }

            @Override public void stop() {
                runOnUiThread(() -> {
                    if (web == null) return;
                    web.evaluateJavascript("(()=>{try{if(window.AndroidRevo&&typeof window.AndroidRevo.stopAll==='function'){window.AndroidRevo.stopAll();return 'stopped';}if(window.AndroidRevo&&typeof window.AndroidRevo.stopMacro==='function'){window.AndroidRevo.stopMacro();return 'stopped';}return 'bridge-not-ready';}catch(e){return 'error:'+String(e)}})()", null);
                });
            }

            @Override public void sunflower() {
                runOnUiThread(() -> startRemoteMacroWhenReady(true, 0));
            }
        });
        remoteAgent.start();
        if (!remoteAgent.isPaired() && remoteAgent.getPairingCode() != null) {
            android.widget.Toast.makeText(this,
                    "Revo remote pairing code: " + remoteAgent.getPairingCode() + " (10 min)",
                    android.widget.Toast.LENGTH_LONG).show();
        }'''
s = s.replace(marker, install, 1)

remote_method = r'''
    private void startRemoteMacroWhenReady(boolean sunflower, int attempt) {
        if (isFinishing() || web == null) return;
        String script;
        if (sunflower) {
            script = "(()=>{try{" +
                    "const rt=window.dataRuntime;" +
                    "if(!rt||typeof rt.presetObject!=='function'||!window.AndroidRevo)return 'retry';" +
                    "const preset=rt.presetObject(rt.preset||rt.defaultPreset||'Default');if(!preset)return 'retry';" +
                    "const active=preset.Object('patterns').List('active');active.keyField='id';active.primitive=false;" +
                    "let row=active.Object('android-sunflower-physical');if(!row)row=active.Append('android-sunflower-physical');" +
                    "row.Set('order',-100);row.Set('field','sunflower');const c=row.Object('config');" +
                    "c.Set('gatherPattern','e_lol');c.Set('seconds',900);c.Set('backpackPercent',90);c.Set('walkReturn',true);" +
                    "c.Set('invertFB',false);c.Set('invertLR',false);c.Set('shiftLock',false);c.Set('zoom',0);" +
                    "c.Set('length',8);c.Set('width',2);c.Set('distance',0);c.Set('alignment',0);c.Set('repetitions',0);" +
                    "c.Set('driftComp',true);c.Set('position','center');c.Set('yaw',0);c.Set('pitch',0);" +
                    "const buttons=[...document.querySelectorAll('button')];" +
                    "const start=buttons.find(x=>(x.innerText||x.textContent||'').trim()==='Start'&&!x.disabled);" +
                    "if(!start)return 'retry';start.click();return 'clicked';" +
                    "}catch(e){return 'error:'+String(e)}})()";
        } else {
            script = "(()=>{try{if(!window.AndroidRevo)return 'retry';const buttons=[...document.querySelectorAll('button')];const start=buttons.find(x=>(x.innerText||x.textContent||'').trim()==='Start'&&!x.disabled);if(!start)return 'retry';start.click();return 'clicked';}catch(e){return 'error:'+String(e)}})()";
        }
        web.evaluateJavascript(script, value -> {
            String result = String.valueOf(value);
            android.util.Log.i("RevoRemoteAgent", "start result=" + result + " sunflower=" + sunflower + " attempt=" + attempt);
            if (result.contains("retry") && attempt < 80) {
                new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(
                        () -> startRemoteMacroWhenReady(sunflower, attempt + 1), 250);
            }
        });
    }
'''

stop_marker = '    // Deliberately DO NOT stop MacroEngine here.'
if stop_marker not in s:
    raise SystemExit('MainActivity class insertion marker missing')
if 'private void startRemoteMacroWhenReady' not in s:
    s = s.replace(stop_marker, remote_method + '\n' + stop_marker, 1)

MAIN.write_text(s)
print('PASS: installed authenticated RevoRemoteAgent on port 38421 with authoritative engine-state gating and paired status/start/stop/Sunflower controls')

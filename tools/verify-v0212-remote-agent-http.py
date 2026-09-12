#!/usr/bin/env python3
"""Compile the generated RevoRemoteAgent and exercise its real localhost HTTP contract."""
from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-v0212-remote-agent-http.py <patch-native-v0212-remote-agent.py>")

patch = pathlib.Path(sys.argv[1])
module = ast.parse(patch.read_text(), filename=str(patch))
agent = None
for node in module.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "agent_source" for t in node.targets):
        agent = ast.literal_eval(node.value)
        break
if not isinstance(agent, str):
    raise SystemExit("FAIL: agent_source string not found")

javac = shutil.which("javac")
java = shutil.which("java")
if not javac or not java:
    raise SystemExit("FAIL: java and javac are required")

context_java = r'''package android.content;
public class Context {
    public static final int MODE_PRIVATE = 0;
    private final SharedPreferences prefs = new SharedPreferences();
    public Context getApplicationContext(){ return this; }
    public SharedPreferences getSharedPreferences(String name, int mode){ return prefs; }
}
'''

prefs_java = r'''package android.content;
import java.util.concurrent.ConcurrentHashMap;
public class SharedPreferences {
    private final ConcurrentHashMap<String,String> values = new ConcurrentHashMap<>();
    public String getString(String key, String def){ return values.getOrDefault(key, def); }
    public Editor edit(){ return new Editor(); }
    public final class Editor {
        private String key;
        private String value;
        public Editor putString(String k, String v){ key=k; value=v; return this; }
        public void apply(){ if(key != null) values.put(key, value); }
    }
}
'''

base64_java = r'''package android.util;
public class Base64 {
    public static final int URL_SAFE=8, NO_WRAP=2, NO_PADDING=1;
    public static String encodeToString(byte[] bytes, int flags){
        return java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
'''

log_java = r'''package android.util;
public class Log {
    public static int i(String t,String m){ return 0; }
    public static int w(String t,String m){ return 0; }
    public static int w(String t,String m,Throwable x){ return 0; }
    public static int e(String t,String m,Throwable x){ x.printStackTrace(); return 0; }
}
'''

json_java = r'''package org.json;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
public class JSONObject {
    private final String raw;
    public JSONObject(String s){ raw=s == null ? "" : s; }
    public boolean has(String key){ return raw.contains("\"" + key + "\""); }
    public boolean optBoolean(String key, boolean def){
        Matcher m=Pattern.compile("\\\""+Pattern.quote(key)+"\\\"\\s*:\\s*(true|false)").matcher(raw);
        return m.find() ? Boolean.parseBoolean(m.group(1)) : def;
    }
    public String optString(String key, String def){
        Matcher m=Pattern.compile("\\\""+Pattern.quote(key)+"\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"").matcher(raw);
        return m.find() ? m.group(1) : def;
    }
}
'''

harness_java = r'''package com.revolution.android;

import android.content.Context;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class RemoteAgentHttpHarness {
    private static final class Hooks implements RevoRemoteAgent.Hooks {
        volatile boolean known=true;
        volatile boolean running=false;
        volatile boolean paused=false;
        volatile boolean autoStart=true;
        int starts=0, stops=0, sunflowers=0;
        public synchronized String status(){
            if(!known) return "BRIDGE_NOT_READY";
            return "{\"running\":"+running+",\"paused\":"+paused+",\"status\":\""+(running?(paused?"Paused":"Running"):"Stopped")+"\"}";
        }
        public synchronized void start(){ starts++; if(autoStart){ running=true; paused=false; } }
        public synchronized void stop(){ stops++; running=false; paused=false; }
        public synchronized void sunflower(){ sunflowers++; running=true; paused=false; }
    }

    private record Resp(int code, String body) {}

    private static Resp request(String method, String path, Map<String,String> headers) throws Exception {
        try(Socket socket=new Socket()){
            socket.connect(new InetSocketAddress("127.0.0.1", RevoRemoteAgent.PORT), 1500);
            socket.setSoTimeout(2500);
            OutputStream out=socket.getOutputStream();
            StringBuilder req=new StringBuilder(method+" "+path+" HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n");
            for(var e:headers.entrySet()) req.append(e.getKey()).append(": ").append(e.getValue()).append("\r\n");
            req.append("Content-Length: 0\r\n\r\n");
            out.write(req.toString().getBytes(StandardCharsets.US_ASCII)); out.flush();
            BufferedReader br=new BufferedReader(new InputStreamReader(socket.getInputStream(),StandardCharsets.UTF_8));
            String first=br.readLine(); if(first==null) throw new AssertionError("empty HTTP response");
            int code=Integer.parseInt(first.split(" ")[1]);
            int len=0; String line;
            while((line=br.readLine())!=null && !line.isEmpty()){
                int colon=line.indexOf(':');
                if(colon>0 && line.substring(0,colon).equalsIgnoreCase("Content-Length")) len=Integer.parseInt(line.substring(colon+1).trim());
            }
            char[] chars=new char[len]; int off=0;
            while(off<len){ int n=br.read(chars,off,len-off); if(n<0) break; off+=n; }
            return new Resp(code,new String(chars,0,off));
        }
    }
    private static Resp get(String path, String token) throws Exception { return request("GET",path, token==null?Map.of():Map.of("Authorization","Bearer "+token)); }
    private static Resp post(String path, String token) throws Exception { return request("POST",path, token==null?Map.of():Map.of("Authorization","Bearer "+token)); }
    private static void expect(int expected, Resp r, String label){ if(r.code()!=expected) throw new AssertionError(label+" expected HTTP "+expected+" got "+r.code()+" body="+r.body()); }
    private static void contains(Resp r,String needle,String label){ if(!r.body().contains(needle)) throw new AssertionError(label+" missing "+needle+" body="+r.body()); }
    private static String tokenFrom(Resp r){
        String mark="\"token\":\""; int s=r.body().indexOf(mark); if(s<0) throw new AssertionError("pair response missing token: "+r.body());
        s+=mark.length(); int e=r.body().indexOf('"',s); if(e<0) throw new AssertionError("bad token response"); return r.body().substring(s,e);
    }

    public static void main(String[] args) throws Exception {
        Hooks hooks=new Hooks();
        RevoRemoteAgent agent=new RevoRemoteAgent(new Context(), hooks);
        String code=agent.getPairingCode(); if(code==null || code.length()!=6) throw new AssertionError("missing six-digit pairing code");
        agent.start();
        Resp ping=null;
        for(int i=0;i<40;i++){
            try { ping=get("/v1/ping",null); break; } catch(Exception e){ Thread.sleep(25); }
        }
        if(ping==null) throw new AssertionError("agent never accepted connections");
        expect(200,ping,"ping"); contains(ping,"\"paired\":false","initial ping");
        expect(401,get("/v1/status",null),"unauthorized status");
        expect(403,request("POST","/v1/pair",Map.of("X-Revo-Pair-Code","000000".equals(code)?"999999":"000000")),"bad pair");
        Resp paired=request("POST","/v1/pair",Map.of("X-Revo-Pair-Code",code)); expect(200,paired,"pair");
        String token=tokenFrom(paired);
        expect(409,request("POST","/v1/pair",Map.of("X-Revo-Pair-Code",code)),"repeat pair");

        Resp status=get("/v1/status",token); expect(200,status,"initial status"); contains(status,"\"engineKnown\":true","known status"); contains(status,"\"engineRunning\":false","stopped status");
        expect(202,post("/v1/start",token),"start");
        status=get("/v1/status",token); contains(status,"\"engineRunning\":true","started status"); contains(status,"\"transition\":\"\"","start settled");
        expect(409,post("/v1/start",token),"duplicate start");
        expect(202,post("/v1/stop",token),"stop");
        status=get("/v1/status",token); contains(status,"\"engineRunning\":false","stopped status"); contains(status,"\"transition\":\"\"","stop settled");
        expect(200,post("/v1/stop",token),"already stopped");

        hooks.running=true; hooks.paused=true;
        expect(202,post("/v1/start",token),"paused resume");
        status=get("/v1/status",token); contains(status,"\"enginePaused\":false","resume cleared pause");
        expect(202,post("/v1/stop",token),"stop after resume"); get("/v1/status",token);

        hooks.running=true; hooks.paused=true;
        int beforeSun=hooks.sunflowers;
        expect(409,post("/v1/sunflower-e2e",token),"sunflower over paused run");
        if(hooks.sunflowers!=beforeSun) throw new AssertionError("Sunflower hook ran over paused engine");
        hooks.running=false; hooks.paused=false;
        expect(202,post("/v1/sunflower-e2e",token),"sunflower clean start");
        status=get("/v1/status",token); contains(status,"\"engineRunning\":true","sunflower running");
        expect(202,post("/v1/stop",token),"stop sunflower"); get("/v1/status",token);

        hooks.autoStart=false; hooks.running=false; hooks.paused=false;
        expect(202,post("/v1/start",token),"settling start");
        Resp busy=post("/v1/start",token); expect(409,busy,"command in progress"); contains(busy,"command_in_progress","busy reason");
        expect(202,post("/v1/stop",token),"stop supersedes settling start");
        hooks.autoStart=true; get("/v1/status",token);

        hooks.known=false;
        Resp unknown=post("/v1/start",token); expect(503,unknown,"unknown-state start"); contains(unknown,"engine_state_unavailable","unknown reason");
        int stopsBefore=hooks.stops;
        expect(202,post("/v1/stop",token),"unknown-state stop");
        if(hooks.stops!=stopsBefore+1) throw new AssertionError("Stop hook not called while engine state unknown");
        hooks.known=true; hooks.running=false; hooks.paused=false; get("/v1/status",token);

        if(hooks.starts < 3) throw new AssertionError("expected start hook coverage");
        if(hooks.sunflowers < 1) throw new AssertionError("expected sunflower hook coverage");
        if(hooks.stops < 4) throw new AssertionError("expected stop hook coverage");
        agent.close();
        System.out.println("PASS: authenticated remote-agent HTTP contract exercised ping/pair/auth/start/resume/duplicate/stop/sunflower/unknown-state paths");
    }
}
'''

with tempfile.TemporaryDirectory(prefix="revo-remote-agent-http-") as td:
    root = pathlib.Path(td) / "src"
    files = {
        "com/revolution/android/RevoRemoteAgent.java": agent,
        "com/revolution/android/RemoteAgentHttpHarness.java": harness_java,
        "android/content/Context.java": context_java,
        "android/content/SharedPreferences.java": prefs_java,
        "android/util/Base64.java": base64_java,
        "android/util/Log.java": log_java,
        "org/json/JSONObject.java": json_java,
    }
    java_files = []
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        java_files.append(str(p))
    out = pathlib.Path(td) / "out"
    out.mkdir()
    compiled = subprocess.run([javac, "-d", str(out), *java_files], text=True, capture_output=True)
    if compiled.returncode:
        sys.stderr.write(compiled.stdout)
        sys.stderr.write(compiled.stderr)
        raise SystemExit("FAIL: HTTP harness or generated RevoRemoteAgent.java did not compile")
    ran = subprocess.run([java, "-cp", str(out), "com.revolution.android.RemoteAgentHttpHarness"], text=True, capture_output=True, timeout=20)
    sys.stdout.write(ran.stdout)
    sys.stderr.write(ran.stderr)
    if ran.returncode:
        raise SystemExit(f"FAIL: remote-agent HTTP contract harness exited {ran.returncode}")

print("PASS: generated remote agent passed localhost authenticated HTTP integration regression")

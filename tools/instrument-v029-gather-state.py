#!/usr/bin/env python3
"""Instrument MainActivity with a one-shot Revo Gather runtime probe.

Keeping this logic in a normal Python file avoids brittle giant inline YAML/heredoc
strings and makes the diagnostic reproducible outside GitHub Actions.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: instrument-v029-gather-state.py <MainActivity.java>")

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

if "import android.webkit.ConsoleMessage;" not in s:
    s = s.replace(
        "import android.webkit.WebChromeClient;",
        "import android.webkit.WebChromeClient;\nimport android.webkit.ConsoleMessage;\nimport android.util.Log;",
        1,
    )

old_chrome = "web.setWebChromeClient(new WebChromeClient());"
new_chrome = '''WebView.setWebContentsDebuggingEnabled(true);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage cm) {
                Log.e("RevoWeb", cm.message() + " @" + cm.sourceId() + ":" + cm.lineNumber());
                return true;
            }
        });'''
if old_chrome in s:
    s = s.replace(old_chrome, new_chrome, 1)
elif "RevoWeb" not in s:
    raise SystemExit("WebChromeClient marker missing")

marker = 'web.loadUrl("https://revo.local/index.android.html");'
if marker not in s:
    raise SystemExit("loadUrl marker missing")

# Java source containing a JS IIFE. Keep it a single Java string literal so the
# generated source is boring and deterministic.
js = r'''(()=>{try{
const rt=window.dataRuntime;if(!rt)return 'missing-dataRuntime';
const out={};
const safe=(o,k)=>{try{return o&&typeof o.Concrete==='function'?o.Concrete(k):undefined}catch(e){return 'ERR:'+e}};
const state=rt.Object('state');
const config=state.Object('config');
const avail=config.List('availablePatterns');
out.backend=window.RevoAndroidDebug&&window.RevoAndroidDebug.backendVersion;
out.availablePatterns={primitive:!!avail.primitive,keyField:String(avail.keyField||''),count:Array.isArray(avail.values)?avail.values.length:-1,values:Array.isArray(avail.values)?avail.values.slice(0,40).map(v=>{try{return v&&typeof v.Value==='function'?v.Value():v}catch(e){return String(v)}}):[]};
const preset=rt.Preset();
out.presetName=rt.preset||rt.defaultPreset||'';
const active=preset.Object('patterns').List('active');
out.activeMeta={primitive:!!active.primitive,keyField:String(active.keyField||''),count:Array.isArray(active.values)?active.values.length:-1};
const keys=['gatherPattern','seconds','backpackPercent','walkReturn','invertFB','invertLR','shiftLock','zoom','length','width','distance','alignment','repetitions','driftComp','position','yaw','pitch'];
out.active=[];
if(Array.isArray(active.values)){
  for(let i=0;i<Math.min(active.values.length,12);i++){
    const row=active.values[i];if(!row)continue;
    const obj=row.object||row;
    const item={index:i,key:String(row.key||''),field:safe(obj,'field'),order:safe(obj,'order')};
    try{const c=obj.Object('config');item.config={};for(const k of keys)item.config[k]=safe(c,k)}catch(e){item.configError=String(e)}
    out.active.push(item);
  }
}
out.runtimeDisconnected=!!rt.disconnected;
out.engine=window.RevoAndroidDebug&&window.RevoAndroidDebug.state?window.RevoAndroidDebug.state():null;
console.error('RevoV029GatherState '+JSON.stringify(out));
return 'ok';
}catch(e){console.error('RevoV029GatherState ERROR '+String(e)+' '+(e&&e.stack||''));return 'error'}})()'''

java_js = (
    js.replace('\\', '\\\\')
      .replace('"', '\\"')
      .replace('\r', '')
      .replace('\n', '')
)

injected = f'''{marker}
        Handler v029Probe = new Handler(Looper.getMainLooper());
        v029Probe.postDelayed(() -> web.evaluateJavascript(
            "{java_js}",
            value -> Log.e("RevoV029Gate", String.valueOf(value))), 17000);'''

s = s.replace(marker, injected, 1)
p.write_text(s, encoding="utf-8")
print("PASS: instrumented MainActivity with v0.2.9 Gather runtime probe")

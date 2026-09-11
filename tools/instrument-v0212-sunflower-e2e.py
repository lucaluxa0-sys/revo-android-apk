#!/usr/bin/env python3
from pathlib import Path

p = Path('revo-android/app/src/main/java/com/revolution/android/MainActivity.java')
s = p.read_text()

if 'import android.webkit.ConsoleMessage;' not in s:
    s = s.replace(
        'import android.webkit.WebChromeClient;',
        'import android.webkit.WebChromeClient;\nimport android.webkit.ConsoleMessage;'
    )
if 'import android.util.Log;' not in s:
    anchor = 'import android.webkit.ConsoleMessage;'
    if anchor not in s:
        raise SystemExit('ConsoleMessage import anchor missing')
    s = s.replace(anchor, anchor + '\nimport android.util.Log;')

old_chrome = 'web.setWebChromeClient(new WebChromeClient());'
new_chrome = '''WebView.setWebContentsDebuggingEnabled(true);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage cm) {
                Log.e("RevoWeb", cm.message() + " @" + cm.sourceId() + ":" + cm.lineNumber());
                return true;
            }
        });'''
if old_chrome not in s:
    raise SystemExit('WebChromeClient anchor missing')
s = s.replace(old_chrome, new_chrome, 1)

marker = '''        if (getIntent() != null && getIntent().getBooleanExtra("autostart", false)) {
            autostartWhenReady(0);
        }'''
receiver = marker + '''
        android.content.IntentFilter sunflowerGateFilter = new android.content.IntentFilter("com.revolution.android.START_SUNFLOWER_GATE");
        registerReceiver(new android.content.BroadcastReceiver() {
            @Override public void onReceive(android.content.Context context, android.content.Intent intent) {
                Log.e("RevoSunflowerGate", "broadcast received");
                startSunflowerGateWhenReady(0);
            }
        }, sunflowerGateFilter, android.content.Context.RECEIVER_EXPORTED);
        Log.e("RevoSunflowerGate", "receiver registered");'''
if marker not in s:
    raise SystemExit('onCreate autostart marker missing')
s = s.replace(marker, receiver, 1)

method = r'''
    private void startSunflowerGateWhenReady(int attempt) {
        if (isFinishing() || web == null) return;
        String script = "(()=>{try{" +
                "const rt=window.dataRuntime;" +
                "if(!rt||typeof rt.presetObject!=='function'||!window.go||!window.go.cmd||!window.go.cmd.Macro||!window.AndroidRevo)return 'retry';" +
                "const preset=rt.presetObject(rt.preset||rt.defaultPreset||'Default');if(!preset)return 'retry';" +
                "const active=preset.Object('patterns').List('active');active.keyField='id';active.primitive=false;" +
                "let row=active.Object('android-sunflower-e2e');if(!row)row=active.Append('android-sunflower-e2e');" +
                "row.Set('order',-100);row.Set('field','sunflower');const c=row.Object('config');" +
                "c.Set('gatherPattern','e_lol');c.Set('seconds',900);c.Set('backpackPercent',90);c.Set('walkReturn',true);" +
                "c.Set('invertFB',false);c.Set('invertLR',false);c.Set('shiftLock',false);c.Set('zoom',0);" +
                "c.Set('length',8);c.Set('width',2);c.Set('distance',0);c.Set('alignment',0);c.Set('repetitions',0);" +
                "c.Set('driftComp',true);c.Set('position','center');c.Set('yaw',0);c.Set('pitch',0);" +
                "localStorage.setItem('revo.android.msPerStud','12');localStorage.setItem('revo.android.joystickCenterX','0.09583333333333334');" +
                "localStorage.setItem('revo.android.joystickCenterY','0.8657407407407407');localStorage.setItem('revo.android.joystickRadius','0.08333333333333333');" +
                "localStorage.setItem('revo.android.jumpX','0.90375');localStorage.setItem('revo.android.jumpY','0.8648148148148148');" +
                "const cfg=window.RevoAndroidDebug&&window.RevoAndroidDebug.engineConfig?window.RevoAndroidDebug.engineConfig('Default'):null;" +
                "console.error('RevoSunflowerPrepared '+JSON.stringify(cfg));" +
                "const buttons=[...document.querySelectorAll('button')];" +
                "const disable=buttons.find(x=>(x.innerText||x.textContent||'').trim()==='Disable');if(disable){disable.click();return 'retry';}" +
                "const start=buttons.find(x=>(x.innerText||x.textContent||'').trim()==='Start'&&!x.disabled);" +
                "if(!start){console.error('RevoSunflowerStartButton NOT_FOUND');return 'retry';}" +
                "console.error('RevoSunflowerStartButton '+JSON.stringify({text:(start.innerText||start.textContent||'').trim(),disabled:!!start.disabled,cls:String(start.className||'')}));" +
                "start.click();return 'clicked';" +
                "}catch(e){console.error('RevoSunflowerGate ERROR '+String(e));return 'error';}})()";
        web.evaluateJavascript(script, value -> {
            Log.e("RevoSunflowerGateResult", String.valueOf(value));
            if (String.valueOf(value).contains("retry") && attempt < 80) {
                new Handler(Looper.getMainLooper()).postDelayed(() -> startSunflowerGateWhenReady(attempt + 1), 250);
                return;
            }
            if (String.valueOf(value).contains("clicked")) {
                Handler h = new Handler(Looper.getMainLooper());
                h.postDelayed(() -> Log.e("RevoSunflowerState", bridge.getEngineState()), 12000);
                h.postDelayed(() -> Log.e("RevoSunflowerState", bridge.getEngineState()), 30000);
                h.postDelayed(() -> Log.e("RevoSunflowerState", bridge.getEngineState()), 45000);
            }
        });
    }
'''

stop_marker = '    // Deliberately DO NOT stop MacroEngine here.'
if stop_marker not in s:
    raise SystemExit('class insertion marker missing')
s = s.replace(stop_marker, method + '\n' + stop_marker, 1)

p.write_text(s)
print('PASS: instrumented real frontend Sunflower row + real Start button gate + staged state evidence')

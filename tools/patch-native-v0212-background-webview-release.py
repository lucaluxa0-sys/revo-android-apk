#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/MainActivity.java")
if not p.exists():
    raise SystemExit(f"MainActivity.java missing: {p}")

s = p.read_text(encoding="utf-8")
marker = "background-webview-release-v1"
if marker in s:
    print("PASS: background WebView release already present")
    raise SystemExit(0)

old_setup = '''        bridge = new AndroidRevoBridge(this);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new LocalAssetWebViewClient(this));
        web.addJavascriptInterface(bridge, "AndroidRevo");
        setContentView(web);
        web.loadUrl("https://revo.local/index.android.html");
'''
new_setup = '''        bridge = new AndroidRevoBridge(this);
        createWebUi();
'''
if old_setup not in s:
    raise SystemExit("MainActivity WebView setup anchor missing")
s = s.replace(old_setup, new_setup, 1)

old_stop_hook = '''            @Override public void stop() {
                runOnUiThread(() -> {
                    if (web == null) return;
                    web.evaluateJavascript("(()=>{try{if(window.AndroidRevo&&typeof window.AndroidRevo.stopAll==='function'){window.AndroidRevo.stopAll();return 'stopped';}if(window.AndroidRevo&&typeof window.AndroidRevo.stopMacro==='function'){window.AndroidRevo.stopMacro();return 'stopped';}return 'bridge-not-ready';}catch(e){return 'error:'+String(e)}})()", null);
                });
            }
'''
new_stop_hook = '''            @Override public void stop() {
                // The macro engine is Java-owned. Do not require the background
                // WebView merely to stop a run.
                MacroEngineRegistry.stopAll();
            }
'''
if old_stop_hook not in s:
    raise SystemExit("remote stop hook anchor missing")
s = s.replace(old_stop_hook, new_stop_hook, 1)

insert_anchor = '''    private void startRemoteMacroWhenReady(boolean sunflower, int attempt) {
'''
helper = r'''    /** background-webview-release-v1
     *  Roblox owns the foreground during a macro run. Keeping Revo's full
     *  Chromium renderer alive in the background costs ~70 MB in the tested
     *  BlueStacks instance and can trigger guest LMK pressure. Release only
     *  the UI renderer when this Activity stops; MacroEngine and the
     *  Accessibility service remain in the Java app process.
     */
    private void createWebUi() {
        if (web != null || isFinishing()) return;
        web = new WebView(this);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new LocalAssetWebViewClient(this));
        web.addJavascriptInterface(bridge, "AndroidRevo");
        setContentView(web);
        web.loadUrl("https://revo.local/index.android.html");
        android.util.Log.i("RevoWebView", "ui-created");
    }

    private void releaseWebUi(String reason) {
        final WebView old = web;
        if (old == null) return;
        web = null;
        try {
            android.view.ViewParent parent = old.getParent();
            if (parent instanceof android.view.ViewGroup) {
                ((android.view.ViewGroup) parent).removeView(old);
            }
            old.stopLoading();
            old.removeJavascriptInterface("AndroidRevo");
            old.destroy();
            android.util.Log.i("RevoWebView", "ui-released reason=" + reason);
        } catch (Throwable t) {
            android.util.Log.w("RevoWebView", "ui-release failed reason=" + reason, t);
        }
    }

    @Override protected void onResume() {
        super.onResume();
        if (web == null) createWebUi();
    }

    @Override protected void onStop() {
        // Android calls onStop after Roblox becomes foreground. Releasing the
        // WebView here is safe because the running macro is service/Java-owned.
        releaseWebUi("activity-stop");
        super.onStop();
    }

'''
if insert_anchor not in s:
    raise SystemExit("startRemoteMacroWhenReady anchor missing")
s = s.replace(insert_anchor, helper + insert_anchor, 1)

p.write_text(s, encoding="utf-8")
print("PASS: release background Revo WebView + Java-direct remote stop")

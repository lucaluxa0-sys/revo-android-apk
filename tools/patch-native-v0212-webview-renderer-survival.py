#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/LocalAssetWebViewClient.java")
if not p.exists():
    raise SystemExit(f"LocalAssetWebViewClient.java missing: {p}")

s = p.read_text(encoding="utf-8")
marker = "webview-renderer-survival-v1"
if marker in s:
    print("PASS: WebView renderer survival handler already present")
    raise SystemExit(0)

old_import = "import android.webkit.WebView;\nimport android.webkit.WebViewClient;\n"
new_import = "import android.webkit.WebView;\nimport android.webkit.WebViewClient;\nimport android.webkit.RenderProcessGoneDetail;\n"
if old_import not in s:
    raise SystemExit("WebView imports anchor missing")
s = s.replace(old_import, new_import, 1)

old = """    private static String mime(String p) {
"""
new = """    /** webview-renderer-survival-v1
     *  The macro engine and remote/accessibility services live in the app
     *  process, while Chromium's WebView renderer is a separate child process.
     *  Under tight BlueStacks memory the renderer may be killed first. Handle
     *  that explicitly so Chromium does not terminate the whole Revo process.
     */
    @Override public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
        android.util.Log.w("RevoWebView",
                "renderer-gone handled=true didCrash=" + detail.didCrash()
                        + " priorityAtExit=" + detail.rendererPriorityAtExit());
        try {
            android.view.ViewParent parent = view.getParent();
            if (parent instanceof android.view.ViewGroup) {
                ((android.view.ViewGroup) parent).removeView(view);
            }
            view.destroy();
        } catch (Throwable t) {
            android.util.Log.w("RevoWebView", "renderer cleanup failed", t);
        }
        return true;
    }

    private static String mime(String p) {
"""
if old not in s:
    raise SystemExit("mime anchor missing")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("PASS: installed WebView renderer OOM survival handler")

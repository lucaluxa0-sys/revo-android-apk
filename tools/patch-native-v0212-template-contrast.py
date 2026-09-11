#!/usr/bin/env python3
from pathlib import Path

ROUTER = Path('revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java')
SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')
MACRO = Path('revo-android/app/src/main/java/com/revolution/android/MacroEngine.java')

for path in (ROUTER, SERVICE, MACRO):
    if not path.exists():
        raise SystemExit(f'{path.name} missing; apply the v0.2.12 native patch sequence first')

text = ROUTER.read_text(encoding='utf-8')

old = r'''    private static Match match(int[] frame, int fw, int fh, Template t, int variation) {
        int first = t.opaqueIndexes[0], fx = first % t.width, fy = first / t.width, expected = t.pixels[first];
        int maxX = fw - t.width, maxY = fh - t.height;
        for (int y = 0; y <= maxY; y++) {
            int row = (y + fy) * fw;
            for (int x = 0; x <= maxX; x++) {
                if (!rgbClose(frame[row + x + fx], expected, variation)) continue;
                boolean ok = true;
                for (int idx : t.opaqueIndexes) {
                    int tx = idx % t.width, ty = idx / t.width;
                    if (!rgbClose(frame[(y + ty) * fw + x + tx], t.pixels[idx], variation)) { ok = false; break; }
                }
                if (ok) return new Match(t.name, x, y, t.width, t.height);
            }
        }
        return null;
    }
'''

new = r'''    private static Match match(int[] frame, int fw, int fh, Template t, int variation) {
        int first = t.opaqueIndexes[0], fx = first % t.width, fy = first / t.width, expected = t.pixels[first];
        int maxX = fw - t.width, maxY = fh - t.height;
        Match best = null;
        long bestError = Long.MAX_VALUE;
        for (int y = 0; y <= maxY; y++) {
            int row = (y + fy) * fw;
            for (int x = 0; x <= maxX; x++) {
                if (!rgbClose(frame[row + x + fx], expected, variation)) continue;

                // Revolution's recovered UI bitmaps are alpha-masked glyphs. Checking only
                // opaque pixels lets a uniform launch/splash frame impersonate a glyph (the
                // API-35 gate demonstrated claimhive falsely matching at 0,0 on such a frame).
                // Require observable contrast at a transparent part of the mask before doing
                // the full opaque-pixel comparison. This keeps the original template pixels
                // and variation tolerance intact while rejecting featureless candidates.
                if (!maskedBackgroundHasContrast(frame, fw, x, y, t, expected, variation)) continue;

                // Do not let the first raster-order candidate win merely because every opaque
                // pixel is inside Revolution's variation tolerance. The full v0.2.12 gate
                // demonstrated a tolerated bright system glyph winning before the genuine
                // recovered claimhive bitmap. Rank tolerated candidates by total opaque RGB
                // error and prefer the highest-fidelity one. An exact recovered bitmap has
                // zero error, so it can be returned immediately without scanning the rest of
                // the frame. No screen coordinates or route-specific geometry are assumed.
                boolean ok = true;
                long error = 0;
                for (int idx : t.opaqueIndexes) {
                    int tx = idx % t.width, ty = idx / t.width;
                    int actual = frame[(y + ty) * fw + x + tx];
                    int target = t.pixels[idx];
                    int dr = Math.abs(((actual >> 16) & 255) - ((target >> 16) & 255));
                    int dg = Math.abs(((actual >> 8) & 255) - ((target >> 8) & 255));
                    int db = Math.abs((actual & 255) - (target & 255));
                    if (dr > variation || dg > variation || db > variation) { ok = false; break; }
                    error += dr + dg + db;
                    if (error >= bestError) { ok = false; break; }
                }
                if (!ok) continue;
                best = new Match(t.name, x, y, t.width, t.height);
                bestError = error;
                if (bestError == 0) return best;
            }
        }
        return best;
    }

    private static boolean maskedBackgroundHasContrast(int[] frame, int fw, int x, int y,
                                                        Template t, int foreground, int variation) {
        int w = t.width, h = t.height;
        int[] probes = new int[]{
                0,
                w - 1,
                (h - 1) * w,
                h * w - 1,
                w / 2,
                (h - 1) * w + w / 2,
                (h / 2) * w,
                (h / 2) * w + w - 1,
                (h / 2) * w + w / 2
        };
        int transparentProbes = 0;
        int backgroundTolerance = Math.max(24, variation * 2);
        for (int idx : probes) {
            if (idx < 0 || idx >= t.pixels.length) continue;
            if (((t.pixels[idx] >>> 24) & 0xff) != 0) continue;
            transparentProbes++;
            int tx = idx % w, ty = idx / w;
            if (!rgbClose(frame[(y + ty) * fw + x + tx], foreground, backgroundTolerance)) {
                return true;
            }
        }
        // Fully opaque templates have no alpha-mask background to validate.
        return transparentProbes == 0;
    }
'''

if text.count(old) != 1:
    raise SystemExit('template matcher anchor missing or duplicated')
text = text.replace(old, new, 1)

status_anchor = '''    void appendState(JSONObject o) {\n'''
status_method = '''    String statusSummary() {\n        return state.name() + "/" + lastDecision;\n    }\n\n'''
if text.count(status_anchor) != 1:
    raise SystemExit('router status anchor missing or duplicated')
text = text.replace(status_anchor, status_method + status_anchor, 1)
ROUTER.write_text(text, encoding='utf-8')

if 'maskedBackgroundHasContrast' not in text or 'bestError' not in text or 'String statusSummary()' not in text:
    raise SystemExit('router matcher/status diagnostics were not installed')

svc = SERVICE.read_text(encoding='utf-8')
old_foreground = r'''    public String activePackageName() {
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root != null && root.getPackageName() != null) {
                String pkg = String.valueOf(root.getPackageName());
                if (!pkg.isEmpty()) activePackageName = pkg;
            }
        } catch (Throwable ignored) {}
        return activePackageName == null ? "" : activePackageName;
    }

    public boolean isRobloxForeground() {
        String pkg = activePackageName();
        return "com.roblox.client".equals(pkg) || "com.roblox.client.samsunggalaxy".equals(pkg);
    }
'''
new_foreground = r'''    private static boolean isRobloxPackageName(String pkg) {
        return pkg != null && ("com.roblox.client".equals(pkg)
                || "com.roblox.client.samsunggalaxy".equals(pkg)
                || pkg.startsWith("com.roblox."));
    }

    public String activePackageName() {
        String fallback = "";
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root != null && root.getPackageName() != null) {
                String pkg = String.valueOf(root.getPackageName());
                if (!pkg.isEmpty()) {
                    activePackageName = pkg;
                    if (isRobloxPackageName(pkg)) return pkg;
                    fallback = pkg;
                }
            }
        } catch (Throwable ignored) {}

        // Real Roblox can be a mostly rendered surface and occasionally gives
        // Accessibility no useful active root even while its window is focused.
        // The service already requests FLAG_RETRIEVE_INTERACTIVE_WINDOWS, so use
        // active/focused Accessibility windows as a second source. We deliberately
        // do NOT accept an arbitrary background Roblox window: the foreground
        // safety gate remains intact before any macro gesture is dispatched.
        try {
            java.util.List<android.view.accessibility.AccessibilityWindowInfo> windows = getWindows();
            if (windows != null) {
                for (android.view.accessibility.AccessibilityWindowInfo window : windows) {
                    if (window == null || !(window.isActive() || window.isFocused())) continue;
                    AccessibilityNodeInfo root = window.getRoot();
                    if (root == null || root.getPackageName() == null) continue;
                    String pkg = String.valueOf(root.getPackageName());
                    if (pkg.isEmpty()) continue;
                    if (isRobloxPackageName(pkg)) {
                        activePackageName = pkg;
                        return pkg;
                    }
                    if (fallback.isEmpty()) fallback = pkg;
                }
            }
        } catch (Throwable ignored) {}

        if (!fallback.isEmpty()) activePackageName = fallback;
        return activePackageName == null ? "" : activePackageName;
    }

    public boolean isRobloxForeground() {
        return isRobloxPackageName(activePackageName());
    }
'''
if svc.count(old_foreground) != 1:
    raise SystemExit('Accessibility foreground anchor missing or duplicated')
svc = svc.replace(old_foreground, new_foreground, 1)
SERVICE.write_text(svc, encoding='utf-8')

macro = MACRO.read_text(encoding='utf-8')
old_status = '        status = String.format(java.util.Locale.US, "Running • display %d • %.1f fps", displayId, fps);\n'
new_status = '''        RevoAccessibilityService svc = RevoAccessibilityService.get();\n        String pkg = svc == null ? "" : svc.activePackageName();\n        if (pkg.isEmpty()) pkg = "<none>";\n        status = String.format(java.util.Locale.US,\n                "Running • display %d • %.1f fps • pkg=%s • route=%s",\n                displayId, fps, pkg, routing.statusSummary());\n'''
if macro.count(old_status) != 1:
    raise SystemExit('MacroEngine running-status anchor missing or duplicated')
macro = macro.replace(old_status, new_status, 1)
MACRO.write_text(macro, encoding='utf-8')

if 'getWindows()' not in svc or 'isRobloxPackageName' not in svc:
    raise SystemExit('Accessibility real-phone foreground fallback was not installed')
if 'pkg=%s • route=%s' not in macro:
    raise SystemExit('visible real-phone routing diagnostics were not installed')

print('Patched v0.2.12 template matcher plus real-phone foreground/router diagnostics')

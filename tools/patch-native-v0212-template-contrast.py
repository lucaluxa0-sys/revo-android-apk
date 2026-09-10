#!/usr/bin/env python3
from pathlib import Path

ROUTER = Path('revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java')

if not ROUTER.exists():
    raise SystemExit('RevoPreGatherRouter.java missing; run patch-native-v0212-hive-routing.py first')

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
ROUTER.write_text(text, encoding='utf-8')

if 'maskedBackgroundHasContrast' not in text:
    raise SystemExit('template contrast guard was not installed')

print('Patched v0.2.12 template matcher to reject uniform alpha-mask false positives')

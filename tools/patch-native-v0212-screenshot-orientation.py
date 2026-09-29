#!/usr/bin/env python3
from pathlib import Path

SERVICE = Path('revo-android/app/src/main/java/com/revolution/android/RevoAccessibilityService.java')
if not SERVICE.exists():
    raise SystemExit('RevoAccessibilityService.java missing; reconstruct/apply earlier v0.2.12 patches first')

src = SERVICE.read_text(encoding='utf-8')
marker = 'screenshot-orientation-normalize-v1'
if marker in src:
    print('PASS: screenshot orientation normalization already present')
    raise SystemExit(0)

old_imports = '''import android.graphics.Bitmap;
import android.graphics.ColorSpace;
import android.graphics.Path;
import android.hardware.HardwareBuffer;
'''
new_imports = '''import android.graphics.Bitmap;
import android.graphics.ColorSpace;
import android.graphics.Matrix;
import android.graphics.Path;
import android.graphics.Point;
import android.hardware.HardwareBuffer;
import android.hardware.display.DisplayManager;
import android.util.Log;
import android.view.Display;
'''
if old_imports not in src:
    raise SystemExit('orientation import anchor missing')
src = src.replace(old_imports, new_imports, 1)

old_delivery = '''                    Bitmap copy = hardware.copy(Bitmap.Config.ARGB_8888, false);
                    if (copy == null) fail.accept(ERROR_TAKE_SCREENSHOT_INTERNAL_ERROR);
                    else ok.accept(copy);
'''
new_delivery = '''                    Bitmap copy = hardware.copy(Bitmap.Config.ARGB_8888, false);
                    if (copy == null) {
                        fail.accept(ERROR_TAKE_SCREENSHOT_INTERNAL_ERROR);
                    } else {
                        ok.accept(normalizeScreenshotForDisplay(displayId, copy));
                    }
'''
if old_delivery not in src:
    raise SystemExit('screenshot delivery anchor missing')
src = src.replace(old_delivery, new_delivery, 1)

anchor = '''    public void screenshot(int displayId, Consumer<Bitmap> ok, Consumer<Integer> fail) {
'''
helper = r'''    /**
     * BlueStacks/Android can return Accessibility screenshot buffers in the
     * display's natural portrait orientation even while the logical display is
     * landscape. All Revo vision/input geometry is display-scoped, so normalize
     * the bitmap once at the capture boundary instead of special-casing every
     * detector and route.
     *
     * screenshot-orientation-normalize-v1
     */
    private Bitmap normalizeScreenshotForDisplay(int displayId, Bitmap source) {
        try {
            DisplayManager dm = (DisplayManager) getSystemService(DISPLAY_SERVICE);
            Display display = dm == null ? null : dm.getDisplay(displayId);
            if (display == null) return source;

            Point target = new Point();
            display.getRealSize(target);
            boolean targetLandscape = target.x > target.y;
            boolean targetPortrait = target.y > target.x;
            boolean sourceLandscape = source.getWidth() > source.getHeight();
            boolean sourcePortrait = source.getHeight() > source.getWidth();

            if ((targetLandscape && sourcePortrait) || (targetPortrait && sourceLandscape)) {
                Matrix matrix = new Matrix();
                matrix.postRotate(targetLandscape ? 90f : -90f);
                Bitmap rotated = Bitmap.createBitmap(
                        source, 0, 0, source.getWidth(), source.getHeight(), matrix, true);
                if (rotated != source) source.recycle();
                Log.i("RevoAccessibility",
                        "screenshot normalized display=" + displayId
                                + " target=" + target.x + "x" + target.y
                                + " output=" + rotated.getWidth() + "x" + rotated.getHeight());
                return rotated;
            }
        } catch (Throwable t) {
            Log.w("RevoAccessibility", "screenshot orientation normalization failed", t);
        }
        return source;
    }

'''
if anchor not in src:
    raise SystemExit('screenshot method anchor missing')
src = src.replace(anchor, helper + anchor, 1)

SERVICE.write_text(src, encoding='utf-8')
print('PASS: added display-scoped Accessibility screenshot orientation normalization')

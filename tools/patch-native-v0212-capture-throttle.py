from pathlib import Path

ENGINE = Path("revo-android/app/src/main/java/com/revolution/android/MacroEngine.java")

old = "private static final long FRAME_INTERVAL_MS = 50; // target <=20 capture requests/sec"
new = "private static final long FRAME_INTERVAL_MS = 350; // AccessibilityService.takeScreenshot requires >333 ms between requests"

if not ENGINE.is_file():
    raise SystemExit(f"MacroEngine.java missing: {ENGINE}")

text = ENGINE.read_text(encoding="utf-8")
count = text.count(old)
if count != 1:
    raise SystemExit(f"capture interval patch anchor count={count}, expected 1")

ENGINE.write_text(text.replace(old, new, 1), encoding="utf-8")

verify = ENGINE.read_text(encoding="utf-8")
assert new in verify
assert old not in verify
print("patched MacroEngine screenshot interval 50ms -> 350ms")

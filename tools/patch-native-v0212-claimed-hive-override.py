#!/usr/bin/env python3
from pathlib import Path

p = Path("revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java")
s = p.read_text()

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"missing marker: {label}")
    s = s.replace(old, new, 1)

once(
"""        final int templateVariation;
        final boolean requireRoblox;
""",
"""        final int templateVariation;
        // Test-only escape hatch: 0 preserves normal hive claiming.
        final int claimedHiveOverride;
        final boolean requireRoblox;
""",
"config fields")

once(
"""               double interactOffsetX, double interactOffsetY,
               int templateVariation, boolean requireRoblox) {
""",
"""               double interactOffsetX, double interactOffsetY,
               int templateVariation, int claimedHiveOverride, boolean requireRoblox) {
""",
"config ctor args")

once(
"""            this.interactOffsetX = interactOffsetX; this.interactOffsetY = interactOffsetY;
            this.templateVariation = templateVariation; this.requireRoblox = requireRoblox;
""",
"""            this.interactOffsetX = interactOffsetX; this.interactOffsetY = interactOffsetY;
            this.templateVariation = templateVariation;
            this.claimedHiveOverride = claimedHiveOverride;
            this.requireRoblox = requireRoblox;
""",
"config ctor body")

once(
"""                    Math.max(0, Math.min(64, o.optInt("routingTemplateVariation", 12))),
                    o.optBoolean("requireRobloxForeground", true));
""",
"""                    Math.max(0, Math.min(64, o.optInt("routingTemplateVariation", 12))),
                    Math.max(0, Math.min(6, o.optInt("claimedHiveOverride", 0))),
                    o.optBoolean("requireRobloxForeground", true));
""",
"config parse")

once(
"""    synchronized void onStart() {
        state = State.WAIT_ROBLOX;
        stateSinceMs = SystemClock.elapsedRealtime();
        nextActionAtMs = 0; lastSearchAtMs = 0; actionCount = 0;
        claimedHive = -1; checkingHive = 3; checkedHives = 0; checkDirection = -1; checkSkip = 0;
""",
"""    synchronized void onStart() {
        final int override = config == null ? 0 : config.claimedHiveOverride;
        state = override > 0 ? State.CLAIMED : State.WAIT_ROBLOX;
        stateSinceMs = SystemClock.elapsedRealtime();
        nextActionAtMs = 0; lastSearchAtMs = 0; actionCount = 0;
        claimedHive = override > 0 ? override : -1; checkingHive = 3; checkedHives = 0; checkDirection = -1; checkSkip = 0;
""",
"onStart state")

once(
"""        lastDecision = "waiting:roblox";
        Log.i(TAG, "start source=GPL-Revolution-ClaimHive+GotoCannon androidAdaptation=v1");
""",
"""        lastDecision = override > 0 ? "debug:claimed-hive-override:" + override : "waiting:roblox";
        Log.i(TAG, "start source=GPL-Revolution-ClaimHive+GotoCannon androidAdaptation=v1 claimedHiveOverride=" + override);
""",
"onStart diagnostics")

p.write_text(s)
print("PASS: installed temporary claimedHiveOverride test hook (0=normal, 1..6=skip claim stage)")

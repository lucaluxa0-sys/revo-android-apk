#!/usr/bin/env python3
from pathlib import Path

P = Path("revo-android/app/src/main/java/com/revolution/android/RevoGatherAdapter.java")
if not P.exists():
    raise SystemExit(f"RevoGatherAdapter.java missing: {P}")

s = P.read_text(encoding="utf-8")
marker = "sunflower-mobile-footprint-v1"
if marker in s:
    print("PASS: Sunflower mobile gather footprint already present")
    raise SystemExit(0)

old_field = '''            String patternName = o.optString("patternName", "");
            double width = positiveOr(o.optDouble("width", 0), 2.0);
            double length = positiveOr(o.optDouble("length", 0), 8.0);
'''
new_field = '''            String patternName = o.optString("patternName", "");
            String field = o.optString("field", "");
            double width = positiveOr(o.optDouble("width", 0), 2.0);
            double length = positiveOr(o.optDouble("length", 0), 8.0);
            // sunflower-mobile-footprint-v1:
            // 60s live WGC QA on BlueStacks proved desktop e_lol length=8
            // accumulates collision drift out of Sunflower after ~20s. Keeping
            // width=2 but capping only the Sunflower long axis at 4 survived
            // 6+ complete cycles / 114 confirmed movement samples in-field.
            // Preserve the configured value for every other field.
            double physicalPatternLength = length;
            if ("sunflower".equalsIgnoreCase(field)
                    && "elol".equals(normalize(patternName))) {
                physicalPatternLength = Math.min(length, 4.0);
            }
'''
if s.count(old_field) != 1:
    raise SystemExit("Sunflower footprint configure anchor missing or duplicated")
s = s.replace(old_field, new_field, 1)

old_build = '''            if ("gather".equalsIgnoreCase(routine)) buildRecoveredPattern(patternName, width, length, steps);
'''
new_build = '''            if ("gather".equalsIgnoreCase(routine)) {
                buildRecoveredPattern(patternName, width, physicalPatternLength, steps);
            }
'''
if s.count(old_build) != 1:
    raise SystemExit("Sunflower footprint pattern-build anchor missing or duplicated")
s = s.replace(old_build, new_build, 1)

old_log = '''            Log.i("RevoGatherAdapter", "configured pattern=" + patternName + " steps=" + steps.size() + " display=" + displayId);
'''
new_log = '''            Log.i("RevoGatherAdapter", "configured pattern=" + patternName
                    + " field=" + field
                    + " requestedLength=" + length
                    + " physicalLength=" + physicalPatternLength
                    + " steps=" + steps.size()
                    + " display=" + displayId);
'''
if s.count(old_log) != 1:
    raise SystemExit("Sunflower footprint configure-log anchor missing or duplicated")
s = s.replace(old_log, new_log, 1)

for needle in (
    marker,
    'physicalPatternLength = Math.min(length, 4.0)',
    'buildRecoveredPattern(patternName, width, physicalPatternLength, steps)',
    'requestedLength=" + length',
    'physicalLength=" + physicalPatternLength',
):
    if needle not in s:
        raise SystemExit("Sunflower footprint marker missing after patch: " + needle)

P.write_text(s, encoding="utf-8")
print("PASS: installed Sunflower-only mobile e_lol long-axis cap")

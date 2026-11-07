#!/usr/bin/env python3
"""Produce an isolated native adapter accepting validated movement-only plans."""
import argparse
import hashlib
from pathlib import Path

ANCHOR = '''            List<MoveStep> steps = new ArrayList<>();
            if ("gather".equalsIgnoreCase(routine)) buildRecoveredPattern(patternName, width, length, steps);
'''
REPLACEMENT = '''            List<MoveStep> steps = new ArrayList<>();
            if ("gather".equalsIgnoreCase(routine)) {
                if (o.has("actionPlan")) {
                    // A compiler report is never an authorization to move a device.
                    if (!o.optBoolean("enablePlannedExecution", false)) {
                        throw new IllegalArgumentException("explicit planned execution authorization required");
                    }
                    for (RevoActionPlan.Step s : RevoActionPlan.load(
                            o.getJSONObject("actionPlan"), patternName, msPerStud)) {
                        steps.add(new MoveStep(Direction.valueOf(s.direction), s.studs));
                    }
                } else {
                    buildRecoveredPattern(patternName, width, length, steps);
                }
            }
'''

def patch(source: str) -> str:
    if source.count(ANCHOR) != 1:
        raise ValueError("native gather anchor missing/duplicated; no changes made")
    if "RevoActionPlan.load(" in source:
        raise ValueError("plan integration already present")
    return source.replace(ANCHOR, REPLACEMENT, 1)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    src = Path(a.source)
    dst = Path(a.output)
    if src.resolve() == dst.resolve():
        raise SystemExit("refusing to overwrite the working original")
    original = src.read_text(encoding="utf-8")
    patched = patch(original)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patched, encoding="utf-8")
    print("ORIGINAL_SHA256", hashlib.sha256(original.encode()).hexdigest())
    print("SANDBOX_SHA256", hashlib.sha256(patched.encode()).hexdigest())
    print("SANDBOX_OUTPUT", dst)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Inventory Revo's exact shipped frontend backend calls without running it."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

def read(p):
    return Path(p).read_text(encoding="utf-8")

def api_calls(js):
    result = defaultdict(set)
    for group, method in re.findall(r"window\.go\.cmd\.(\w+)\.(\w+)\s*\(", js):
        result[group].add(method)
    return {key: sorted(value) for key, value in sorted(result.items())}

def shim_members(src):
    blocks = {}
    for marker, group in (("macro", "Macro"), ("analytics", "AnalyticsHandler"),
                          ("auth", "AuthHandler"), ("fflags", "FFlagsHandler")):
        match = re.search(r"const\s+" + marker + r"\s*=\s*\{(.*?)\n\s*\};", src, re.S)
        if not match:
            blocks[group] = {}
            continue
        body = match.group(1)
        found = {}
        for hit in re.finditer(r"\b([A-Za-z]\w*)\s*:\s*(noop|async\b)", body):
            method, impl = hit.groups()
            found[method] = "stub" if impl == "noop" else "handler"
        blocks[group] = found
    return blocks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frontend", required=True)
    ap.add_argument("--shim", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    calls = api_calls(read(args.frontend))
    handlers = shim_members(read(args.shim))
    groups = {}
    for group, methods in calls.items():
        mapped = handlers.get(group, {})
        groups[group] = {
            "called_methods": methods,
            "missing_in_shim": [m for m in methods if m not in mapped],
            "stub_methods": [m for m in methods if mapped.get(m) == "stub"],
            "handled_methods": [m for m in methods if mapped.get(m) == "handler"],
        }
    report = {
        "source": str(args.frontend),
        "method_count": sum(map(len, calls.values())),
        "groups": groups,
        "limitations": [
            "Static references establish API names only, not runtime behavior.",
            "Shim handler classification does not verify a functioning native backend.",
            "Exact recovered JavaScript is not redistributed by this report.",
        ],
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("METHODS", report["method_count"])
    for name, group in groups.items():
        print(name, "called", len(group["called_methods"]), "shim_missing",
              len(group["missing_in_shim"]), "stubbed", len(group["stub_methods"]),
              "present_handler", len(group["handled_methods"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

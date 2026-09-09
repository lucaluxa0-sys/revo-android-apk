#!/usr/bin/env python3
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "com.revolution.android"
SERVICE_CLASS = "com.revolution.android.RevoAccessibilityService"
ARTIFACT_DIR = Path("emulator-artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def run(*args, check=True, capture=True):
    cmd = [str(a) for a in args]
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def adb(*args, check=True):
    return run("adb", *args, check=check)


def shell(*args, check=True):
    return adb("shell", *args, check=check)


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "stage"


def capture(stage):
    stage = safe_name(stage)
    remote = "/sdcard/revo-a11y.xml"
    xml_path = ARTIFACT_DIR / f"a11y-{stage}.xml"
    png_path = ARTIFACT_DIR / f"a11y-{stage}.png"

    dump = shell("uiautomator", "dump", remote, check=False)
    if dump.stdout:
        print(dump.stdout, flush=True)
    pulled = adb("pull", remote, str(xml_path), check=False)
    if pulled.stdout:
        print(pulled.stdout, flush=True)
    with png_path.open("wb") as fh:
        proc = subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=fh)
        if proc.returncode != 0:
            raise RuntimeError(f"screencap failed at {stage}: {proc.returncode}")

    if not xml_path.exists():
        raise RuntimeError(f"UI hierarchy missing at {stage}")
    return ET.parse(xml_path).getroot()


def parent_map(root):
    return {child: parent for parent in root.iter() for child in parent}


def label(node):
    return " ".join(
        part.strip()
        for part in (
            node.attrib.get("text", ""),
            node.attrib.get("content-desc", ""),
            node.attrib.get("resource-id", ""),
        )
        if part and part.strip()
    )


def center(node):
    bounds = node.attrib.get("bounds", "")
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not match:
        raise RuntimeError(f"Node has unusable bounds: {bounds!r} label={label(node)!r}")
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def clickable_target(node, parents):
    cur = node
    while cur is not None:
        if cur.attrib.get("clickable") == "true" or cur.attrib.get("checkable") == "true":
            return cur
        cur = parents.get(cur)
    return node


def click(node, parents, reason):
    target = clickable_target(node, parents)
    x, y = center(target)
    print(
        f"CLICK {reason}: ({x},{y}) label={label(node)!r} "
        f"target={label(target)!r} class={target.attrib.get('class')} "
        f"checked={target.attrib.get('checked')}",
        flush=True,
    )
    shell("input", "tap", str(x), str(y))
    time.sleep(1.2)


def enabled_state():
    services = shell("settings", "get", "secure", "enabled_accessibility_services", check=False).stdout.strip()
    enabled = shell("settings", "get", "secure", "accessibility_enabled", check=False).stdout.strip()
    print(f"STATE services={services!r} accessibility_enabled={enabled!r}", flush=True)
    return SERVICE_CLASS in services and enabled == "1"


def find_by_text(root, needles, exact=False):
    needles = [n.lower() for n in needles]
    for node in root.iter():
        text = " ".join(
            p for p in (node.attrib.get("text", ""), node.attrib.get("content-desc", "")) if p
        ).strip()
        low = text.lower()
        if not low:
            continue
        if exact:
            if low in needles:
                return node
        elif any(n in low for n in needles):
            return node
    return None


def first_switch(root):
    for node in root.iter():
        cls = node.attrib.get("class", "")
        if ("Switch" in cls or node.attrib.get("checkable") == "true") and node.attrib.get("enabled") != "false":
            if node.attrib.get("checked") != "true":
                return node
    return None


def page_has_revolution(root):
    return find_by_text(root, ["revolution macro", "revolution android", "revolution"]) is not None


def dump_visible_labels(root):
    values = []
    for node in root.iter():
        value = label(node)
        if value and value not in values:
            values.append(value)
    print("VISIBLE UI:", flush=True)
    for value in values[:120]:
        print("  ", value, flush=True)


def main():
    print("Opening Android Accessibility Settings", flush=True)
    shell("am", "start", "-a", "android.settings.ACCESSIBILITY_SETTINGS")
    time.sleep(1.5)

    for attempt in range(16):
        if enabled_state():
            capture(f"enabled-{attempt:02d}")
            print("PASS: Revolution Accessibility is enabled", flush=True)
            return 0

        root = capture(f"step-{attempt:02d}")
        parents = parent_map(root)
        dump_visible_labels(root)

        # Confirmation dialogs take priority once a toggle is pressed.
        node = find_by_text(root, ["allow"], exact=True)
        if node is not None:
            click(node, parents, "confirmation Allow")
            continue
        node = find_by_text(root, ["ok"], exact=True)
        if node is not None:
            click(node, parents, "confirmation OK")
            continue
        node = find_by_text(root, ["continue"], exact=True)
        if node is not None:
            click(node, parents, "confirmation Continue")
            continue

        # On the service detail page, toggle the service before clicking the title again.
        if page_has_revolution(root):
            node = find_by_text(root, ["use revolution macro", "use revolution android", "use service"])
            if node is not None:
                click(node, parents, "service enable row")
                continue
            switch = first_switch(root)
            if switch is not None:
                click(switch, parents, "service switch")
                continue

        # Pixel/Android 15 usually places third-party services under Downloaded apps.
        node = find_by_text(root, ["downloaded apps", "installed apps"], exact=True)
        if node is not None:
            click(node, parents, "third-party accessibility apps")
            continue

        node = find_by_text(root, ["revolution macro", "revolution android", "revolution"])
        if node is not None:
            click(node, parents, "Revolution accessibility service")
            continue

        # Some Settings builds expose a search affordance; fail with evidence rather than
        # blindly tapping coordinates if the expected path is not represented in the tree.
        print(f"No known Accessibility UI target on attempt {attempt}", flush=True)
        time.sleep(0.8)

    root = capture("failed-final")
    dump_visible_labels(root)
    raise SystemExit("Revolution Accessibility could not be enabled through Android Settings UI")


if __name__ == "__main__":
    raise SystemExit(main())

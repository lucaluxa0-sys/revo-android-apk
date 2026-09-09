#!/usr/bin/env python3
import base64
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "com.revolution.android"
SERVICE_CLASS = "com.revolution.android.RevoAccessibilityService"
SERVICE_COMPONENT = f"{PACKAGE}/{SERVICE_CLASS}"
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


def wake_and_unlock():
    for args in (
        ("input", "keyevent", "KEYCODE_WAKEUP"),
        ("wm", "dismiss-keyguard"),
        ("input", "keyevent", "82"),
    ):
        result = shell(*args, check=False)
        if result.stdout:
            print(result.stdout, flush=True)
    time.sleep(0.35)


def take_screenshot(path):
    with path.open("wb") as fh:
        proc = subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=fh)
    if proc.returncode != 0:
        raise RuntimeError(f"screencap failed for {path}: {proc.returncode}")


def print_filtered(title, output, patterns=None, max_lines=160):
    print(f"===== {title} =====", flush=True)
    lines = (output or "").splitlines()
    if patterns:
        regexes = [re.compile(p, re.I) for p in patterns]
        selected = [line for line in lines if any(rx.search(line) for rx in regexes)]
        if selected:
            lines = selected
    for line in lines[:max_lines]:
        print(line, flush=True)
    if len(lines) > max_lines:
        print(f"... ({len(lines) - max_lines} more lines)", flush=True)


def print_failure_diagnostics(stage, png_path):
    print_filtered(
        f"WINDOW FOCUS {stage}",
        shell("dumpsys", "window", check=False).stdout,
        [r"mCurrentFocus", r"mFocusedApp", r"mObscuringWindow", r"mTopFocusedDisplayId"],
    )
    print_filtered(
        f"RESUMED ACTIVITIES {stage}",
        shell("dumpsys", "activity", "activities", check=False).stdout,
        [r"mResumedActivity", r"topResumedActivity", r"ResumedActivity", r"Task\\{"],
        max_lines=120,
    )
    print_filtered(
        f"ACTIVITY TOP {stage}",
        shell("dumpsys", "activity", "top", check=False).stdout,
        [r"ACTIVITY", r"mResumed", r"mStopped", r"mCurrentFocus", r"settings"],
        max_lines=120,
    )
    print_filtered(
        f"CMD ACCESSIBILITY HELP {stage}",
        shell("cmd", "accessibility", "help", check=False).stdout,
        max_lines=160,
    )
    if png_path.exists():
        encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
        print(f"REVO_SCREENSHOT_BASE64_STAGE={stage}", flush=True)
        print(f"REVO_SCREENSHOT_BASE64={encoded}", flush=True)


def capture(stage):
    stage = safe_name(stage)
    remote = "/sdcard/revo-a11y.xml"
    xml_path = ARTIFACT_DIR / f"a11y-{stage}.xml"
    png_path = ARTIFACT_DIR / f"a11y-{stage}.png"
    xml_path.unlink(missing_ok=True)

    last_output = ""
    for retry in range(5):
        wake_and_unlock()
        shell("rm", "-f", remote, check=False)
        for command in (
            ("uiautomator", "dump", "--compressed", remote),
            ("uiautomator", "dump", remote),
        ):
            dump = shell(*command, check=False)
            last_output = dump.stdout or ""
            if last_output:
                print(f"UI DUMP retry={retry} command={' '.join(command)}", flush=True)
                print(last_output, flush=True)
            pulled = adb("pull", remote, str(xml_path), check=False)
            if pulled.stdout:
                print(pulled.stdout, flush=True)
            if xml_path.exists() and xml_path.stat().st_size > 20:
                try:
                    root = ET.parse(xml_path).getroot()
                    take_screenshot(png_path)
                    return root
                except ET.ParseError as exc:
                    print(f"Invalid UI hierarchy retry={retry}: {exc}", flush=True)
                    xml_path.unlink(missing_ok=True)
        time.sleep(0.8 + retry * 0.2)

    take_screenshot(png_path)
    print(f"UI hierarchy still missing after retries at {stage}: {last_output!r}", flush=True)
    print_failure_diagnostics(stage, png_path)
    raise RuntimeError(f"UI hierarchy missing at {stage}")


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


def dump_visible_labels(root):
    values = []
    for node in root.iter():
        value = label(node)
        if value and value not in values:
            values.append(value)
    print("VISIBLE UI:", flush=True)
    for value in values[:120]:
        print("  ", value, flush=True)


def open_service_settings():
    wake_and_unlock()
    print("Opening Revolution Accessibility service detail page", flush=True)
    detail = shell(
        "am",
        "start",
        "-a",
        "android.settings.ACCESSIBILITY_DETAILS_SETTINGS",
        "--es",
        "android.provider.extra.ACCESSIBILITY_SERVICE_COMPONENT_NAME",
        SERVICE_COMPONENT,
        check=False,
    )
    output = detail.stdout or ""
    if output:
        print(output, flush=True)
    if detail.returncode != 0 or "Error:" in output or "unable to resolve" in output.lower():
        print("Accessibility detail deep-link unavailable; falling back to general Accessibility Settings", flush=True)
        fallback = shell("am", "start", "-a", "android.settings.ACCESSIBILITY_SETTINGS", check=False)
        if fallback.stdout:
            print(fallback.stdout, flush=True)
    time.sleep(1.8)


def main():
    print_filtered(
        "CMD ACCESSIBILITY HELP INITIAL",
        shell("cmd", "accessibility", "help", check=False).stdout,
        max_lines=160,
    )
    open_service_settings()

    for attempt in range(16):
        if enabled_state():
            capture(f"enabled-{attempt:02d}")
            print("PASS: Revolution Accessibility is enabled", flush=True)
            return 0

        root = capture(f"step-{attempt:02d}")
        parents = parent_map(root)
        dump_visible_labels(root)

        # Android 15 emulator can surface a Pixel Launcher ANR over Settings.
        # Run-10 evidence showed this exact dialog blocked every retry even though
        # the Revolution accessibility row was already visible underneath it.
        launcher_anr = find_by_text(root, ["pixel launcher isn't responding"], exact=True)
        if launcher_anr is not None:
            close_app = find_by_text(root, ["close app"], exact=True)
            if close_app is None:
                raise RuntimeError("Pixel Launcher ANR is blocking Accessibility Settings without a Close app action")
            click(close_app, parents, "dismiss Pixel Launcher ANR")
            continue

        # Confirmation dialogs after enabling the service.
        for text in ("allow", "ok", "continue"):
            node = find_by_text(root, [text], exact=True)
            if node is not None:
                click(node, parents, f"confirmation {text}")
                break
        else:
            # Service detail page: prefer the explicit 'Use ...' row or switch.
            node = find_by_text(root, ["use revolution macro", "use revolution android", "use service"])
            if node is not None:
                click(node, parents, "service enable row")
                continue

            switch = first_switch(root)
            if switch is not None:
                click(switch, parents, "service switch")
                continue

            # Run-9 evidence showed Revolution Macro is already directly visible under
            # Downloaded apps on the main Accessibility page. Click this row BEFORE the
            # Downloaded apps category heading; the old ordering repeatedly tapped the
            # non-navigating category label and never entered the service detail page.
            node = find_by_text(root, ["revolution macro", "revolution android"], exact=True)
            if node is not None:
                click(node, parents, "Revolution accessibility service row")
                continue

            node = find_by_text(root, ["downloaded apps", "installed apps"], exact=True)
            if node is not None:
                click(node, parents, "third-party accessibility apps")
                continue

            print(f"No known Accessibility UI target on attempt {attempt}", flush=True)
            time.sleep(0.8)
            continue

        continue

    root = capture("failed-final")
    dump_visible_labels(root)
    print_failure_diagnostics("failed-final", ARTIFACT_DIR / "a11y-failed-final.png")
    raise SystemExit("Revolution Accessibility could not be enabled through Android Settings UI")


if __name__ == "__main__":
    raise SystemExit(main())

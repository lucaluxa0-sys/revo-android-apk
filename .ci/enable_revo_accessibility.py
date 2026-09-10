#!/usr/bin/env python3
import re
import subprocess
import time
from pathlib import Path

PACKAGE = "com.revolution.android"
SERVICE_CLASS = "com.revolution.android.RevoAccessibilityService"
SERVICE_COMPONENT = f"{PACKAGE}/{SERVICE_CLASS}"
SHORT_COMPONENT = f"{PACKAGE}/.RevoAccessibilityService"
ARTIFACT_DIR = Path("emulator-artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def run(*args, check=True):
    cmd = [str(a) for a in args]
    print("+", " ".join(cmd), flush=True)
    result = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed rc={result.returncode}: {' '.join(cmd)}\n{result.stdout or ''}"
        )
    return result


def adb(*args, check=True):
    return run("adb", *args, check=check)


def shell(*args, check=True):
    return adb("shell", *args, check=check)


def component_present(text):
    value = text or ""
    return (
        SERVICE_COMPONENT in value
        or SHORT_COMPONENT in value
        or SERVICE_CLASS in value
    )


def read_setting(name):
    result = shell("settings", "get", "secure", name, check=False)
    return (result.stdout or "").strip()


def enabled_services():
    raw = read_setting("enabled_accessibility_services")
    if not raw or raw == "null":
        return []
    return [entry for entry in raw.split(":") if entry]


def verify_service_declared():
    package_dump = shell("dumpsys", "package", PACKAGE, check=False).stdout or ""
    (ARTIFACT_DIR / "a11y-package.txt").write_text(package_dump, encoding="utf-8", errors="replace")
    if not component_present(package_dump):
        raise RuntimeError(
            "installed Revolution package does not declare RevoAccessibilityService; "
            "refusing to fake an enabled state"
        )
    print("PASS prerequisite: installed package declares RevoAccessibilityService", flush=True)


def set_service_enabled():
    current = enabled_services()
    print(f"Existing enabled accessibility services: {current!r}", flush=True)
    if not any(component_present(entry) for entry in current):
        current.append(SERVICE_COMPONENT)
    value = ":".join(current)

    put_services = shell(
        "settings", "put", "secure", "enabled_accessibility_services", value, check=False
    )
    if put_services.returncode != 0:
        raise RuntimeError(
            "failed to write enabled_accessibility_services via emulator shell: "
            + (put_services.stdout or "")
        )

    put_master = shell(
        "settings", "put", "secure", "accessibility_enabled", "1", check=False
    )
    if put_master.returncode != 0:
        raise RuntimeError(
            "failed to set accessibility_enabled=1 via emulator shell: "
            + (put_master.stdout or "")
        )


def bound_section(text):
    # Android 15 dumpsys accessibility prints separate Bound/Enabled/Binding/Crashed
    # service sections. Only Bound services proves that AccessibilityManager actually
    # connected our service; merely appearing in the secure setting is not enough.
    match = re.search(
        r"(?is)Bound services\s*:(.*?)(?="
        r"\n\s*(?:Enabled services|Binding services|Crashed services|Client list|User state)\s*:|\Z)",
        text or "",
    )
    return match.group(1) if match else ""


def binding_verified(accessibility_dump):
    section = bound_section(accessibility_dump)
    if not section:
        return False
    return component_present(section)


def write_state_artifacts(attempt, settings_services, master, accessibility_dump):
    (ARTIFACT_DIR / "a11y-enabled-setting.txt").write_text(
        settings_services + "\n", encoding="utf-8"
    )
    (ARTIFACT_DIR / "a11y-master-setting.txt").write_text(master + "\n", encoding="utf-8")
    (ARTIFACT_DIR / "a11y-dumpsys.txt").write_text(
        accessibility_dump, encoding="utf-8", errors="replace"
    )
    (ARTIFACT_DIR / "a11y-attempt.txt").write_text(str(attempt) + "\n", encoding="utf-8")


def wait_for_bound_service(timeout_s=20.0):
    deadline = time.monotonic() + timeout_s
    attempt = 0
    last = ("", "", "")
    while time.monotonic() < deadline:
        services = read_setting("enabled_accessibility_services")
        master = read_setting("accessibility_enabled")
        dump = shell("dumpsys", "accessibility", check=False).stdout or ""
        last = (services, master, dump)
        write_state_artifacts(attempt, services, master, dump)

        setting_ok = component_present(services) and master == "1"
        bound_ok = binding_verified(dump)
        print(
            f"A11Y probe={attempt} setting_ok={setting_ok} bound_ok={bound_ok} "
            f"services={services!r} master={master!r}",
            flush=True,
        )
        if setting_ok and bound_ok:
            return True
        time.sleep(0.5)
        attempt += 1

    services, master, dump = last
    print("===== FINAL ACCESSIBILITY DUMPSYS =====", flush=True)
    print(dump, flush=True)
    print("===== REVOLUTION ACCESSIBILITY LOGCAT =====", flush=True)
    logcat = adb("logcat", "-d", "-v", "time", check=False).stdout or ""
    for line in logcat.splitlines():
        if re.search(r"RevoAccessibility|AccessibilityManager|com\.revolution\.android", line, re.I):
            print(line, flush=True)
    raise RuntimeError(
        "Revolution Accessibility secure setting was not sufficient to produce a bound service "
        f"within {timeout_s:.0f}s; services={services!r} master={master!r}"
    )


def main():
    # This helper is CI setup, not a macro assertion. The previous Android-Settings
    # UI automation repeatedly remained on the top-level page on API 35 and never
    # reached the service switch. The emulator shell can set the same secure state
    # deterministically, after which we fail closed unless AccessibilityManager binds
    # the *real installed* Revolution service.
    verify_service_declared()
    set_service_enabled()
    wait_for_bound_service()
    print(
        "PASS: Revolution Accessibility is enabled in secure settings and bound by AccessibilityManager",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

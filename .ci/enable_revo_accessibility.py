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


def section(text, heading, next_headings):
    following = "|".join(re.escape(item) for item in next_headings)
    match = re.search(
        rf"(?is){re.escape(heading)}\s*:(.*?)(?=\n\s*(?:{following})\s*:|\Z)",
        text or "",
    )
    return match.group(1) if match else ""


def bound_section(text):
    # Android 15 intentionally renders bound services as Service[label=..., ...]
    # and does NOT include the component class name in that line.
    return section(
        text,
        "Bound services",
        ("Enabled services", "Binding services", "Crashed services", "Client list", "User state"),
    )


def enabled_section(text):
    return section(
        text,
        "Enabled services",
        ("Binding services", "Crashed services", "Client list", "User state"),
    )


def accessibility_manager_reports_bound(accessibility_dump):
    # The previous verifier searched this section for RevoAccessibilityService and
    # false-failed on API 35 because dumpsys prints only the service label here.
    # A populated Service[...] record proves AccessibilityManager has a bound
    # accessibility service. Exact component identity is checked independently below.
    return bool(re.search(r"\bService\s*\[", bound_section(accessibility_dump)))


def accessibility_manager_reports_enabled_component(accessibility_dump):
    return component_present(enabled_section(accessibility_dump))


def activity_service_dump():
    return shell("dumpsys", "activity", "services", PACKAGE, check=False).stdout or ""


def exact_service_active(activity_dump):
    # ActivityManager's service table keeps the concrete component identity, unlike
    # dumpsys accessibility's Bound-services display on API 35. Require an active
    # ServiceRecord for Revolution's exact accessibility component so a similarly
    # labelled third-party accessibility service cannot satisfy this gate.
    value = activity_dump or ""
    return component_present(value) and bool(re.search(r"\bServiceRecord\s*\{", value))


def write_state_artifacts(
    attempt,
    settings_services,
    master,
    accessibility_dump,
    activity_dump,
):
    (ARTIFACT_DIR / "a11y-enabled-setting.txt").write_text(
        settings_services + "\n", encoding="utf-8"
    )
    (ARTIFACT_DIR / "a11y-master-setting.txt").write_text(master + "\n", encoding="utf-8")
    (ARTIFACT_DIR / "a11y-dumpsys.txt").write_text(
        accessibility_dump, encoding="utf-8", errors="replace"
    )
    (ARTIFACT_DIR / "a11y-activity-services.txt").write_text(
        activity_dump, encoding="utf-8", errors="replace"
    )
    (ARTIFACT_DIR / "a11y-attempt.txt").write_text(str(attempt) + "\n", encoding="utf-8")


def wait_for_bound_service(timeout_s=20.0):
    deadline = time.monotonic() + timeout_s
    attempt = 0
    last = ("", "", "", "")
    while time.monotonic() < deadline:
        services = read_setting("enabled_accessibility_services")
        master = read_setting("accessibility_enabled")
        accessibility_dump = shell("dumpsys", "accessibility", check=False).stdout or ""
        activity_dump = activity_service_dump()
        last = (services, master, accessibility_dump, activity_dump)
        write_state_artifacts(
            attempt,
            services,
            master,
            accessibility_dump,
            activity_dump,
        )

        setting_ok = component_present(services) and master == "1"
        enabled_exact = accessibility_manager_reports_enabled_component(accessibility_dump)
        manager_bound = accessibility_manager_reports_bound(accessibility_dump)
        active_exact = exact_service_active(activity_dump)
        print(
            f"A11Y probe={attempt} setting_ok={setting_ok} enabled_exact={enabled_exact} "
            f"manager_bound={manager_bound} active_exact={active_exact} "
            f"services={services!r} master={master!r}",
            flush=True,
        )
        if setting_ok and enabled_exact and manager_bound and active_exact:
            return True
        time.sleep(0.5)
        attempt += 1

    services, master, accessibility_dump, activity_dump = last
    print("===== FINAL ACCESSIBILITY DUMPSYS =====", flush=True)
    print(accessibility_dump, flush=True)
    print("===== FINAL ACTIVITY SERVICE DUMPSYS =====", flush=True)
    print(activity_dump, flush=True)
    print("===== REVOLUTION ACCESSIBILITY LOGCAT =====", flush=True)
    logcat = adb("logcat", "-d", "-v", "time", check=False).stdout or ""
    for line in logcat.splitlines():
        if re.search(r"RevoAccessibility|AccessibilityManager|com\.revolution\.android", line, re.I):
            print(line, flush=True)
    raise RuntimeError(
        "Revolution Accessibility did not produce a verified exact active service binding "
        f"within {timeout_s:.0f}s; services={services!r} master={master!r}"
    )


def main():
    # CI setup only: enable the real installed service deterministically, then fail
    # closed unless both AccessibilityManager and ActivityManager prove the service
    # is enabled/bound and the concrete active component is Revolution's service.
    verify_service_declared()
    set_service_enabled()
    wait_for_bound_service()
    print(
        "PASS: Revolution Accessibility is enabled and its exact service is active/bound",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

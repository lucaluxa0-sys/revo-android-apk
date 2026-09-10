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


def parse_enabled_setting(raw):
    if not raw or raw == "null":
        return []
    return [entry for entry in raw.split(":") if entry]


def enabled_services():
    return parse_enabled_setting(read_setting("enabled_accessibility_services"))


def verify_service_declared():
    package_dump = shell("dumpsys", "package", PACKAGE, check=False).stdout or ""
    (ARTIFACT_DIR / "a11y-package.txt").write_text(
        package_dump, encoding="utf-8", errors="replace"
    )
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
    # Android 15 renders bound accessibility services as Service[label=..., ...]
    # and omits the concrete component class name from this section.
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


def binding_section(text):
    return section(
        text,
        "Binding services",
        ("Crashed services", "Client list", "User state"),
    )


def crashed_section(text):
    return section(text, "Crashed services", ("Client list", "User state"))


def accessibility_manager_reports_exact_clean_binding(accessibility_dump, settings_services):
    # The API-35 Bound-services section is label-only, so correlate it with the
    # exact enabled component instead of asking ActivityManager for a service record.
    # This CI emulator starts clean: requiring exactly one enabled component and
    # exactly one bound Service[...] makes the identity mapping unambiguous.
    entries = parse_enabled_setting(settings_services)
    if len(entries) != 1 or not component_present(entries[0]):
        return False
    if not component_present(enabled_section(accessibility_dump)):
        return False
    if len(re.findall(r"\bService\s*\[", bound_section(accessibility_dump))) != 1:
        return False
    if re.search(r"\bService\s*\[", binding_section(accessibility_dump)):
        return False
    if re.search(r"\bService\s*\[", crashed_section(accessibility_dump)):
        return False
    return True


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
        accessibility_dump = shell("dumpsys", "accessibility", check=False).stdout or ""
        last = (services, master, accessibility_dump)
        write_state_artifacts(attempt, services, master, accessibility_dump)

        entries = parse_enabled_setting(services)
        setting_ok = (
            master == "1"
            and len(entries) == 1
            and component_present(entries[0])
        )
        manager_exact_clean = accessibility_manager_reports_exact_clean_binding(
            accessibility_dump, services
        )
        print(
            f"A11Y probe={attempt} setting_ok={setting_ok} "
            f"manager_exact_clean={manager_exact_clean} "
            f"services={services!r} master={master!r}",
            flush=True,
        )
        if setting_ok and manager_exact_clean:
            return True
        time.sleep(0.5)
        attempt += 1

    services, master, accessibility_dump = last
    print("===== FINAL ACCESSIBILITY DUMPSYS =====", flush=True)
    print(accessibility_dump, flush=True)
    print("===== REVOLUTION ACCESSIBILITY LOGCAT =====", flush=True)
    logcat = adb("logcat", "-d", "-v", "time", check=False).stdout or ""
    for line in logcat.splitlines():
        if re.search(r"RevoAccessibility|AccessibilityManager|com\.revolution\.android", line, re.I):
            print(line, flush=True)
    raise RuntimeError(
        "Revolution Accessibility did not produce one exact enabled component plus "
        f"one clean bound Accessibility service within {timeout_s:.0f}s; "
        f"services={services!r} master={master!r}"
    )


def main():
    # CI setup only. On the clean Android emulator, fail closed unless the installed
    # package declares the exact service, secure settings enable only that component,
    # and AccessibilityManager reports exactly one clean bound service for it.
    verify_service_declared()
    set_service_enabled()
    wait_for_bound_service()
    print(
        "PASS: Revolution Accessibility exact component is enabled and cleanly bound",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

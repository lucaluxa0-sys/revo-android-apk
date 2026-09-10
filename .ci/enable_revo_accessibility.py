#!/usr/bin/env python3
import re
import subprocess
import time
from pathlib import Path

PACKAGE = "com.revolution.android"
SERVICE_CLASS = "com.revolution.android.RevoAccessibilityService"
SERVICE_COMPONENT = f"{PACKAGE}/{SERVICE_CLASS}"
SHORT_COMPONENT = f"{PACKAGE}/.RevoAccessibilityService"
BIND_ACCESSIBILITY_OP = "android:bind_accessibility_service"
SETTINGS_USER = "0"
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
    result = shell(
        "settings", "--user", SETTINGS_USER, "get", "secure", name, check=False
    )
    return (result.stdout or "").strip()


def parse_enabled_setting(raw):
    if not raw or raw == "null":
        return []
    return [entry for entry in raw.split(":") if entry]


def enabled_services():
    return parse_enabled_setting(read_setting("enabled_accessibility_services"))


def secure_setting_is_exact(services, master):
    entries = parse_enabled_setting(services)
    return (
        master == "1"
        and len(entries) == 1
        and component_present(entries[0])
    )


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


def grant_bind_accessibility_appop():
    before = shell(
        "cmd", "appops", "get", PACKAGE, BIND_ACCESSIBILITY_OP, check=False
    )
    before_text = before.stdout or ""
    (ARTIFACT_DIR / "a11y-bind-appop-before.txt").write_text(
        before_text, encoding="utf-8", errors="replace"
    )

    set_result = shell(
        "cmd", "appops", "set", PACKAGE, BIND_ACCESSIBILITY_OP, "allow", check=False
    )
    if set_result.returncode != 0:
        raise RuntimeError(
            "failed to allow android:bind_accessibility_service AppOp: "
            + (set_result.stdout or "")
        )

    after = shell(
        "cmd", "appops", "get", PACKAGE, BIND_ACCESSIBILITY_OP, check=False
    )
    after_text = after.stdout or ""
    (ARTIFACT_DIR / "a11y-bind-appop-after.txt").write_text(
        after_text, encoding="utf-8", errors="replace"
    )
    if after.returncode != 0 or not re.search(r"\ballow(?:ed)?\b", after_text, re.I):
        raise RuntimeError(
            "android:bind_accessibility_service AppOp did not read back as allowed: "
            + after_text
        )
    print("PASS prerequisite: BIND_ACCESSIBILITY_SERVICE AppOp is allowed", flush=True)


def write_secure_accessibility_state(reason):
    current = enabled_services()
    print(
        f"Writing Accessibility secure state reason={reason} existing={current!r}",
        flush=True,
    )
    if not any(component_present(entry) for entry in current):
        current.append(SERVICE_COMPONENT)
    value = ":".join(current)

    put_services = shell(
        "settings",
        "--user",
        SETTINGS_USER,
        "put",
        "secure",
        "enabled_accessibility_services",
        value,
        check=False,
    )
    if put_services.returncode != 0:
        raise RuntimeError(
            "failed to write enabled_accessibility_services via emulator shell: "
            + (put_services.stdout or "")
        )

    put_master = shell(
        "settings",
        "--user",
        SETTINGS_USER,
        "put",
        "secure",
        "accessibility_enabled",
        "1",
        check=False,
    )
    if put_master.returncode != 0:
        raise RuntimeError(
            "failed to set accessibility_enabled=1 via emulator shell: "
            + (put_master.stdout or "")
        )

    services_after = read_setting("enabled_accessibility_services")
    master_after = read_setting("accessibility_enabled")
    print(
        f"Accessibility secure readback reason={reason} "
        f"services={services_after!r} master={master_after!r}",
        flush=True,
    )
    return services_after, master_after


def set_service_enabled():
    grant_bind_accessibility_appop()
    write_secure_accessibility_state("initial")


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


def collection_section_is_empty(value):
    # dumpsys accessibility prints these sets as {} when settled. During the
    # API35 race it printed the component as {{package/class}} while Bound services
    # was already populated, so merely searching for Service[...] was insufficient.
    return re.sub(r"\s+", "", value or "") == "{}"


def accessibility_manager_reports_exact_clean_binding(accessibility_dump, settings_services):
    # The API-35 Bound-services section is label-only, so correlate it with the
    # exact enabled component instead of asking ActivityManager for a service record.
    # This CI emulator starts clean: require one exact enabled component, one bound
    # service, no in-progress/crashed binding, and the gesture input filter that the
    # real macro needs before declaring Accessibility usable.
    entries = parse_enabled_setting(settings_services)
    if len(entries) != 1 or not component_present(entries[0]):
        return False
    if not component_present(enabled_section(accessibility_dump)):
        return False
    if len(re.findall(r"\bService\s*\[", bound_section(accessibility_dump))) != 1:
        return False
    if not collection_section_is_empty(binding_section(accessibility_dump)):
        return False
    if not collection_section_is_empty(crashed_section(accessibility_dump)):
        return False
    if not re.search(
        r"Enabled features of Display\s*\[\s*0\s*\]\s*=\s*\[[^\]]*\bMotionEventInjector\b",
        accessibility_dump,
        re.I,
    ):
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
        setting_ok = secure_setting_is_exact(services, master)

        # Android's AccessibilityManager can sanitize secure settings while the
        # package/service registration is settling after install. The failed API35
        # run demonstrated that a one-shot write can regress to null/0. Repair only
        # observed setting drift; never rewrite while a valid service is binding.
        if not setting_ok:
            print(
                f"A11Y secure-state drift probe={attempt}; re-arming exact component",
                flush=True,
            )
            services, master = write_secure_accessibility_state(
                f"probe-{attempt}-readback-drift"
            )
            setting_ok = secure_setting_is_exact(services, master)

        accessibility_dump = shell("dumpsys", "accessibility", check=False).stdout or ""
        last = (services, master, accessibility_dump)
        write_state_artifacts(attempt, services, master, accessibility_dump)

        manager_exact_clean = accessibility_manager_reports_exact_clean_binding(
            accessibility_dump, services
        )
        binding = re.sub(r"\s+", " ", binding_section(accessibility_dump)).strip()
        crashed = re.sub(r"\s+", " ", crashed_section(accessibility_dump)).strip()
        has_motion_injector = "MotionEventInjector" in accessibility_dump
        print(
            f"A11Y probe={attempt} setting_ok={setting_ok} "
            f"manager_exact_clean={manager_exact_clean} "
            f"binding={binding!r} crashed={crashed!r} "
            f"motionInjector={has_motion_injector} "
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
        "Revolution Accessibility did not produce one exact enabled component, "
        "one settled bound service, and the gesture input filter within "
        f"{timeout_s:.0f}s; services={services!r} master={master!r}"
    )


def main():
    # CI setup only. On the clean Android emulator, fail closed unless the installed
    # package declares the exact service, its bind AppOp is explicitly allowed,
    # secure settings enable only that component, and AccessibilityManager reports
    # a fully settled service with the gesture input path active.
    verify_service_declared()
    set_service_enabled()
    wait_for_bound_service()
    print(
        "PASS: Revolution Accessibility exact component is enabled and fully settled",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

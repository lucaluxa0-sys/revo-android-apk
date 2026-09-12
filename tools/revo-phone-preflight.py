#!/usr/bin/env python3
"""Fail-closed preflight for physical Revo movement-start commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_COMMANDS = {"start", "sunflower-e2e"}


def validate(command: str, state: dict) -> str:
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"unsupported command: {command}")
    if state.get("http_status") != 200:
        raise ValueError("status request was not HTTP 200")
    if state.get("engineKnown") is not True:
        raise ValueError(
            "phone does not expose authoritative engine state; install the current preview and retry status first"
        )
    if not isinstance(state.get("engineRunning"), bool):
        raise ValueError("engineRunning is missing or not boolean")
    if not isinstance(state.get("enginePaused"), bool):
        raise ValueError("enginePaused is missing or not boolean")
    transition = state.get("transition")
    if not isinstance(transition, str):
        raise ValueError("transition is missing or not a string")

    running = state["engineRunning"]
    paused = state["enginePaused"]
    if paused and not running:
        raise ValueError("invalid engine snapshot: paused=true while running=false")
    if transition:
        raise ValueError(f"phone has command transition {transition!r}")
    if command == "sunflower-e2e" and running:
        raise ValueError("refused Sunflower: macro engine is already active")
    if command == "start" and running and not paused:
        raise ValueError("refused Start: macro engine is already running")

    return f"PASS: physical preflight command={command} running={running} paused={paused}"


def run_self_test() -> None:
    base = {
        "http_status": 200,
        "engineKnown": True,
        "engineRunning": False,
        "enginePaused": False,
        "transition": "",
    }
    cases = [
        ("start", base, True),
        ("sunflower-e2e", base, True),
        ("start", {**base, "engineRunning": True}, False),
        ("sunflower-e2e", {**base, "engineRunning": True}, False),
        ("start", {**base, "engineRunning": True, "enginePaused": True}, True),
        ("sunflower-e2e", {**base, "engineRunning": True, "enginePaused": True}, False),
        ("start", {**base, "transition": "starting"}, False),
        ("start", {**base, "engineKnown": False}, False),
        ("start", {**base, "http_status": 503}, False),
        ("start", {**base, "engineRunning": None}, False),
        ("start", {**base, "enginePaused": None}, False),
        ("start", {**base, "transition": None}, False),
        ("start", {**base, "enginePaused": True}, False),
    ]
    for index, (command, state, should_pass) in enumerate(cases, 1):
        passed = True
        try:
            validate(command, state)
        except ValueError:
            passed = False
        if passed != should_pass:
            raise SystemExit(f"self-test case {index} failed: command={command} state={state}")
    print(f"PASS: physical preflight self-test cases={len(cases)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("status_json", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return
    if args.command is None or args.status_json is None:
        parser.error("command and status_json are required unless --self-test is used")

    state = json.loads(args.status_json.read_text(encoding="utf-8"))
    try:
        print(validate(args.command, state))
    except ValueError as exc:
        raise SystemExit(f"Preflight failed closed: {exc}")


if __name__ == "__main__":
    main()

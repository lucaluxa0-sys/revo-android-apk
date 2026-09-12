#!/usr/bin/env python3
"""Verify that a physical Revo control command actually reached the engine state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_COMMANDS = {"start", "stop", "sunflower-e2e"}


def validate(command: str, state: dict) -> str:
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"unsupported command: {command}")
    if state.get("http_status") != 200:
        raise ValueError("status request was not HTTP 200")
    if state.get("engineKnown") is not True:
        raise ValueError("phone does not expose authoritative engine state")
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
        raise ValueError(f"command transition did not settle: {transition!r}")

    if command in {"start", "sunflower-e2e"}:
        if not running:
            raise ValueError(f"{command} was accepted but engine is not running")
        if paused:
            raise ValueError(f"{command} settled into paused state")
    elif command == "stop":
        if running:
            raise ValueError("stop was accepted but engine is still running")
        if paused:
            raise ValueError("stop settled into an invalid paused state")

    return f"PASS: physical postflight command={command} running={running} paused={paused}"


def run_self_test() -> None:
    stopped = {
        "http_status": 200,
        "engineKnown": True,
        "engineRunning": False,
        "enginePaused": False,
        "transition": "",
    }
    running = {**stopped, "engineRunning": True}
    paused = {**running, "enginePaused": True}
    cases = [
        ("start", running, True),
        ("sunflower-e2e", running, True),
        ("stop", stopped, True),
        ("start", stopped, False),
        ("sunflower-e2e", stopped, False),
        ("stop", running, False),
        ("start", paused, False),
        ("sunflower-e2e", paused, False),
        ("stop", paused, False),
        ("start", {**running, "transition": "starting"}, False),
        ("stop", {**stopped, "transition": "stopping"}, False),
        ("start", {**running, "engineKnown": False}, False),
        ("start", {**running, "http_status": 503}, False),
        ("start", {**running, "engineRunning": None}, False),
        ("stop", {**stopped, "enginePaused": None}, False),
        ("start", {**running, "transition": None}, False),
        ("start", {**stopped, "enginePaused": True}, False),
    ]
    for index, (command, state, should_pass) in enumerate(cases, 1):
        passed = True
        try:
            validate(command, state)
        except ValueError:
            passed = False
        if passed != should_pass:
            raise SystemExit(f"self-test case {index} failed: command={command} state={state}")
    print(f"PASS: physical postflight self-test cases={len(cases)}")


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
        raise SystemExit(f"Postflight failed closed: {exc}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Small controller for the authenticated Revo physical-phone test agent.

The bearer token is stored only on the controller machine, never in the repo.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PORT = 38421
TOKEN_FILE = Path(os.environ.get("REVO_PHONE_TOKEN_FILE", Path.home() / ".revo-phone-agent-token"))


def base_url(host: str) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    if ":" in host:
        return "http://" + host.rstrip("/")
    return f"http://{host}:{PORT}"


def request(host: str, method: str, path: str, *, token: str | None = None, pair_code: str | None = None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if pair_code:
        headers["X-Revo-Pair-Code"] = pair_code
    req = Request(base_url(host) + path, data=b"" if method == "POST" else None, headers=headers, method=method)
    try:
        with urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"error": raw or str(exc)}
        return exc.code, body
    except URLError as exc:
        raise SystemExit(f"Cannot reach phone agent at {base_url(host)}: {exc.reason}")


def load_token(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    env = os.environ.get("REVO_PHONE_TOKEN", "").strip()
    if env:
        return env
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise SystemExit("No token found. Run the 'pair' command first or set REVO_PHONE_TOKEN.")


def save_token(token: str):
    TOKEN_FILE.write_text(token + "\n")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Control the Revo Android physical-test agent")
    parser.add_argument("--host", required=True, help="Phone LAN/Tailscale IP or host[:port]")
    parser.add_argument("--token", help="Override stored token (prefer REVO_PHONE_TOKEN for CI)")
    sub = parser.add_subparsers(dest="command", required=True)

    pair = sub.add_parser("pair", help="Pair once using the 6-digit code shown by Revo")
    pair.add_argument("code")
    sub.add_parser("ping")
    sub.add_parser("status")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("sunflower-e2e")

    args = parser.parse_args()
    if args.command == "ping":
        status, body = request(args.host, "GET", "/v1/ping")
    elif args.command == "pair":
        status, body = request(args.host, "POST", "/v1/pair", pair_code=args.code)
        if status == 200 and body.get("token"):
            save_token(body["token"])
            body = {"paired": True, "token_file": str(TOKEN_FILE)}
    else:
        token = load_token(args.token)
        method, path = {
            "status": ("GET", "/v1/status"),
            "start": ("POST", "/v1/start"),
            "stop": ("POST", "/v1/stop"),
            "sunflower-e2e": ("POST", "/v1/sunflower-e2e"),
        }[args.command]
        status, body = request(args.host, method, path, token=token)

    print(json.dumps({"http_status": status, **body}, indent=2, sort_keys=True))
    if status >= 400:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

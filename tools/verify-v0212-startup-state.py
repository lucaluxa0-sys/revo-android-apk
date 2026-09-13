#!/usr/bin/env python3
import pathlib
import re
import sys

EXPECTED_ROOTS = ['settings', 'planters', 'accounts']
EXPECTED_BASE_OPS = [
    ('state.ready', 'true'),
    ('state.activeAccount', "'Default'"),
    ('state.defaultPreset', "'Default'"),
    ('auth.sessionId', "''"),
    ('auth.hwid', "'android'"),
]


def verify_source(source: str) -> None:
    roots_match = re.search(r"const\s+PERSIST_ROOTS\s*=\s*\[([^\]]*)\]\s*;", source, re.S)
    if not roots_match:
        raise AssertionError('PERSIST_ROOTS declaration missing')
    roots = re.findall(r"['\"]([^'\"]+)['\"]", roots_match.group(1))
    if roots != EXPECTED_ROOTS:
        raise AssertionError(f'PERSIST_ROOTS changed: {roots!r}')

    base_match = re.search(r"const\s+baseOps\s*=\s*\[(.*?)\]\s*;", source, re.S)
    if not base_match:
        raise AssertionError('baseOps preload block missing')
    base_body = base_match.group(1)
    entries = re.findall(
        r"\{\s*op\s*:\s*['\"]set['\"]\s*,\s*path\s*:\s*['\"]([^'\"]+)['\"]\s*,\s*value\s*:\s*(true|false|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")\s*\}",
        base_body,
        re.S,
    )
    if entries != EXPECTED_BASE_OPS:
        raise AssertionError(f'Android bootstrap operations changed: {entries!r}')

    for path, value in entries:
        root = path.split('.', 1)[0]
        if root in EXPECTED_ROOTS:
            raise AssertionError(f'bootstrap must not inject persisted user configuration: {path}')
        if value == 'true' and path != 'state.ready':
            raise AssertionError(f'bootstrap must not silently enable a user-facing option: {path}')

    merge_pattern = r"const\s+ops\s*=\s*\[\s*\.\.\.loadPersistedOps\(\)\s*,\s*\.\.\.baseOps\s*\]\s*;"
    if not re.search(merge_pattern, source):
        raise AssertionError('persisted user state must stay explicitly separate from bootstrap defaults')


def self_test(source: str) -> None:
    verify_source(source)

    bad_setting = source.replace(
        "{op:'set', path:'state.ready', value:true},",
        "{op:'set', path:'settings.syntheticFollow', value:true},",
        1,
    )
    try:
        verify_source(bad_setting)
    except AssertionError:
        pass
    else:
        raise AssertionError('self-test failed: synthetic enabled setting was accepted')

    bad_extra = source.replace(
        "{op:'set', path:'auth.hwid', value:'android'}",
        "{op:'set', path:'auth.hwid', value:'android'},\n      {op:'set', path:'state.syntheticToggle', value:true}",
        1,
    )
    try:
        verify_source(bad_extra)
    except AssertionError:
        pass
    else:
        raise AssertionError('self-test failed: extra bootstrap toggle was accepted')


if len(sys.argv) not in (2, 3):
    raise SystemExit('usage: verify-v0212-startup-state.py <android-wails-shim-v0.2.4.js> [--self-test]')

path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding='utf-8')
try:
    if len(sys.argv) == 3:
        if sys.argv[2] != '--self-test':
            raise SystemExit(f'unknown option: {sys.argv[2]}')
        self_test(source)
    else:
        verify_source(source)
except AssertionError as exc:
    raise SystemExit(f'FAIL: {exc}')

print('PASS: Android bootstrap injects only internal startup state; persisted user configuration is replayed separately')

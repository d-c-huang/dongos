#!/usr/bin/env python3
"""Explain Dong compiler diagnostic codes.

    python tools/dong_explain.py E0301          explain one code
    python tools/dong_explain.py --list         list all codes
    python -m lang.dongc --check a.dg 2>&1 | python tools/dong_explain.py -
                                                echo diagnostics, then explain
                                                every code they mention

The text comes from lang/docs/diagnostics.md (one `## E####` section per
code), whose examples are compiled by tools/dong_doctest.py, so this tool and
the documentation cannot drift apart.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

CATALOG = Path(__file__).resolve().parents[1] / 'lang' / 'docs' / 'diagnostics.md'
HEADING = re.compile(r'^## (E\d{4})(?:[:：\s]\s*(.*))?$')
# Seed CLI `error[E0301]` and native CLI `E0301:` diagnostics.
MENTION = re.compile(r'\berror\[(E\d{4})\]|:\s(E\d{4}):')


def load(path: Path = CATALOG) -> dict[str, tuple[str, str]]:
    """Map code -> (title, body) parsed from the catalog's `## E####` sections."""
    entries, code, title, body = {}, None, '', []
    fence = False
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fence = not fence
            # Replace doctest attributes with a readable marker for the terminal.
            failing = re.search(r'\berror=(E\d{4})', line)
            if fence and re.match(r'^\s*(?:```|~~~)\s*dong\b', line):
                line = '```dong  ' + (f'✗ 触发 {failing.group(1)}' if failing else '✓ 正确写法')
        match = None if fence else HEADING.match(line)
        if match or (not fence and line.startswith('## ')):
            if code:
                entries[code] = (title, '\n'.join(body).strip())
            code, title, body = (match.group(1), (match.group(2) or '').strip(), []) if match else (None, '', [])
            continue
        if code:
            body.append(line)
    if code:
        entries[code] = (title, '\n'.join(body).strip())
    return entries


def explain(code: str, entries) -> str:
    title, body = entries[code]
    return f'{code}: {title}\n\n{body}\n'


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description='explain Dong diagnostic codes')
    parser.add_argument('codes', nargs='*', help="codes such as E0301, or '-' to read diagnostics from stdin")
    parser.add_argument('--list', action='store_true', help='list every documented code')
    options = parser.parse_args(argv)
    try:
        entries = load()
    except OSError as error:
        print(f'dong_explain: cannot read {CATALOG}: {error}', file=sys.stderr)
        return 2
    if options.list:
        for code, (title, _) in sorted(entries.items()):
            print(f'{code}  {title}')
        return 0
    if not options.codes:
        parser.error('provide a code, - or --list')
    codes = []
    for argument in options.codes:
        if argument == '-':
            text = sys.stdin.read()
            sys.stdout.write(text if text.endswith('\n') or not text else text + '\n')
            codes.extend(code for match in MENTION.finditer(text) for code in match.groups() if code)
        else:
            codes.append(argument.upper())
    status, shown = 0, set()
    for code in codes:
        if code in shown:
            continue
        shown.add(code)
        if code not in entries:
            print(f'dong_explain: unknown code {code}; use --list', file=sys.stderr)
            status = 1
            continue
        print('\n' + '=' * 72)
        print(explain(code, entries), end='')
    return status


if __name__ == '__main__':
    raise SystemExit(main())

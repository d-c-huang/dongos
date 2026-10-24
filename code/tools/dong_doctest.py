#!/usr/bin/env python3
"""Compile the Dong examples embedded in Markdown documents.

Every fenced block whose info string starts with `dong` is a complete module
and is checked with the repository compiler, unless marked otherwise:

    ```dong                    must compile
    ```dong error=E0301        must fail with this diagnostic code
    ```dong error=E0301 line=4 ... and on this source line of the block
    ```dong release            compile in release mode instead of debug
    ```dong ignore             shown with highlighting, never compiled

Successful blocks of one document share a temporary source root, so a later
block may import a module defined by an earlier one; `lang/std` is always
available as a second root. Nothing is written into the repository.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
import tempfile


def compiler_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'lang/dongc/frontend.py').is_file():
            return parent
    raise RuntimeError('cannot find the Dong compiler beside dong_doctest')


ROOT = compiler_root()
sys.path.insert(0, str(ROOT))
from lang.dongc import compile_file
from lang.dongc.model import CompileError

STD = ROOT / 'lang' / 'std'
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})\s*(.*)$')
MODULE = re.compile(r'^\s*module\s+([^\s;]+)\s*;', re.MULTILINE)


class UsageError(ValueError):
    pass


@dataclass
class Example:
    path: Path
    line: int  # 1-based line of the first source line inside the fence
    source: str
    ignore: bool = False
    release: bool = False
    error: str | None = None
    error_line: int | None = None


@dataclass
class Outcome:
    example: Example
    passed: bool
    detail: str = ''
    skipped: bool = False


def parse_info(info: str, where: str) -> dict[str, str] | None:
    words = info.split()
    if not words or words[0] != 'dong':
        return None
    options = {}
    for word in words[1:]:
        key, sep, value = word.partition('=')
        if key not in {'ignore', 'release', 'error', 'line'} or bool(sep) != (key in {'error', 'line'}):
            raise UsageError(f'{where}: unknown example attribute {word!r}')
        options[key] = value
    if 'line' in options and 'error' not in options:
        raise UsageError(f'{where}: line= requires error=')
    if 'error' in options and not re.fullmatch(r'E\d{4}', options['error']):
        raise UsageError(f'{where}: error= expects a code such as E0301')
    if 'line' in options and not options['line'].isdigit():
        raise UsageError(f'{where}: line= expects a positive integer')
    return options


def extract(path: Path, text: str) -> list[Example]:
    examples, lines, index = [], text.splitlines(), 0
    while index < len(lines):
        match = FENCE.match(lines[index])
        if not match:
            index += 1
            continue
        fence, info, start = match.group(1), match.group(2), index + 1
        end = start
        while end < len(lines) and not re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*$', lines[end]):
            end += 1
        if end == len(lines):
            raise UsageError(f'{path.as_posix()}:{index + 1}: unterminated code fence')
        options = parse_info(info, f'{path.as_posix()}:{index + 1}')
        if options is not None:
            examples.append(Example(path, start + 1, '\n'.join(lines[start:end]) + '\n', 'ignore' in options,
                                    'release' in options, options.get('error'),
                                    int(options['line']) if 'line' in options else None))
        index = end + 1
    return examples


def run_document(path: Path, examples: list[Example]) -> list[Outcome]:
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='dong-doctest-') as temporary:
        root = Path(temporary)
        for example in examples:
            if example.ignore:
                outcomes.append(Outcome(example, True, 'ignored', skipped=True))
                continue
            match = MODULE.search(example.source)
            if not match:
                outcomes.append(Outcome(example, False, 'example has no `module name;` declaration'))
                continue
            target = root.joinpath(*match.group(1).split('.')).with_suffix('.dg')
            previous = target.read_bytes() if target.is_file() else None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(example.source, encoding='utf-8', newline='\n')
            outcome = check(example, target, root)
            outcomes.append(outcome)
            # Only examples that compile stay visible to later imports.
            if example.error is not None or not outcome.passed:
                if previous is None:
                    target.unlink()
                else:
                    target.write_bytes(previous)
    return outcomes


def check(example: Example, target: Path, root: Path) -> Outcome:
    try:
        compile_file(target, roots=[root, STD], mode='release' if example.release else 'debug')
    except CompileError as error:
        found = f'{error.code} at line {error.token.line}: {error.message}'
        if example.error is None:
            return Outcome(example, False, f'expected success, got {found}')
        if error.code != example.error:
            return Outcome(example, False, f'expected {example.error}, got {found}')
        if example.error_line is not None and error.token.line != example.error_line:
            return Outcome(example, False, f'expected {example.error} at line {example.error_line}, got {found}')
        return Outcome(example, True, found)
    except Exception as error:  # compiler bugs are reported, not hidden
        return Outcome(example, False, f'internal compiler error: {type(error).__name__}: {error}')
    if example.error is not None:
        return Outcome(example, False, f'expected {example.error}, but the example compiled')
    return Outcome(example, True)


def collect(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob('*.md')))
        elif path.is_file():
            files.append(path)
        else:
            raise UsageError(f'no such file or directory: {path}')
    return list(dict.fromkeys(files))


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description='check Dong examples in Markdown documents')
    parser.add_argument('paths', type=Path, nargs='+', help='Markdown files or directories (searched for *.md)')
    parser.add_argument('-v', '--verbose', action='store_true', help='also list passing examples')
    options = parser.parse_args(argv)
    try:
        documents = [(path, extract(path, path.read_text(encoding='utf-8-sig'))) for path in collect(options.paths)]
    except (UsageError, OSError, UnicodeDecodeError) as error:
        print(f'dong_doctest: {error}', file=sys.stderr)
        return 2
    passed = failed = skipped = 0
    for path, examples in documents:
        for outcome in run_document(path, examples):
            where = f'{path.as_posix()}:{outcome.example.line}'
            if outcome.skipped:
                skipped += 1
            elif outcome.passed:
                passed += 1
                if options.verbose:
                    print(f'ok    {where}' + (f'  ({outcome.detail})' if outcome.detail else ''))
            else:
                failed += 1
                print(f'FAIL  {where}: {outcome.detail}')
    print(f'{passed} passed, {failed} failed, {skipped} ignored in {len(documents)} document(s)')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

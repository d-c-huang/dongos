#!/usr/bin/env python3
"""Generate Markdown API reference pages from Dong module sources.

Public declarations come from the repository parser; the `//` comment block
directly above each declaration (no blank line in between) becomes its text.
Modules are found under explicit source roots and rendered deterministically,
so `--check` can verify that committed reference pages are current.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import sys


def compiler_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'lang/dongc/frontend.py').is_file():
            return parent
    raise RuntimeError('cannot find the Dong compiler beside dongdoc')


ROOT = compiler_root()
sys.path.insert(0, str(ROOT))
from lang.dongc.frontend import Parser, lex
from lang.dongc.model import CompileError

VERSION = '0.1.0'

# Section order and Chinese headings of a module page.
SECTIONS = (('error', '错误码'), ('const', '常量'), ('var', '全局变量'), ('type', '类型别名'),
            ('struct', '结构体'), ('enum', '枚举'), ('fn', '函数'), ('method', '方法'))


class DocError(ValueError):
    pass


@dataclass
class Item:
    kind: str
    name: str
    line: int
    signature: str
    doc: str
    unsafe: bool = False


@dataclass
class ModuleDoc:
    name: str
    path: Path
    doc: str
    imports: list[str]
    items: list[Item] = field(default_factory=list)


def line_starts(source: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(source):
        if char == '\n':
            starts.append(index + 1)
    return starts


def comment_block(lines: list[str], first: int) -> str:
    """Collect the contiguous `//` lines ending just above 0-based line `first`."""
    collected = []
    index = first - 1
    while index >= 0:
        text = lines[index].strip()
        if not text.startswith('//'):
            break
        collected.append(text[2:].lstrip('/'))
        index -= 1
    collected.reverse()
    paragraphs, current = [], ''
    for text in collected:
        text = text.strip()
        if not text:
            if current:
                paragraphs.append(current)
            current = ''
        elif current.endswith('-') and text[0].isalpha():
            current += text  # rejoin a word hyphenated across comment lines
        else:
            current = f'{current} {text}' if current else text
    if current:
        paragraphs.append(current)
    return '\n\n'.join(paragraphs)


def top_level_spans(tokens) -> list[tuple[int, int]]:
    """Token index ranges of top-level items; the module header is item 0.

    An item ends at a depth-0 `;`, or at a `}` returning to depth 0 that is not
    followed by `;` (that `}` closes a constant's literal, not the item).
    """
    spans, start, depth = [], 0, 0
    for index, token in enumerate(tokens):
        if token.kind == 'eof':
            break
        if token.kind in {'{', '(', '['}:
            depth += 1
        elif token.kind in {'}', ')', ']'}:
            depth -= 1
        if depth:
            continue
        if token.kind == ';' or (token.kind == '}' and tokens[index + 1].kind != ';'):
            spans.append((start, index))
            start = index + 1
    return spans


def render_module(path: Path, display: str) -> ModuleDoc:
    raw = path.read_bytes()
    try:
        source = raw.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise DocError(f'{display}: source is not valid UTF-8') from error
    try:
        tokens = lex(source, path=display)
        module = Parser(list(tokens)).parse()
    except CompileError as error:
        raise DocError(error.format(display, source)) from error
    starts, lines = line_starts(source), source.splitlines()

    def offset(token):
        return starts[token.line - 1] + token.column - 1

    spans = top_level_spans(tokens)
    if not spans:
        raise DocError(f'{display}: missing module declaration')
    # The module text is the file's leading comment block, which is usually
    # separated from the `module` line by a blank line.
    header = next((index for index, text in enumerate(lines) if not text.strip().startswith('//')), len(lines))
    result = ModuleDoc(module.name, path, comment_block(lines, header), [item.path for item in module.imports])
    by_position = {}
    for function in module.functions:
        by_position[(function.token.line, function.token.column)] = (
            'method' if function.receiver else 'fn', function.public, function.unsafe, function)
    for kind, values in (('struct', module.structs), ('enum', module.enums), ('error', module.errors),
                         ('type', module.aliases), ('const', module.constants), ('var', module.globals)):
        for value in values:
            by_position[(value.token.line, value.token.column)] = (kind, value.public, False, value)
    for first, last in spans[1:]:
        names = [(token.line, token.column) for token in tokens[first:last + 1]
                 if (token.line, token.column) in by_position]
        if not names:
            continue  # imports
        kind, public, unsafe, declaration = by_position[names[0]]
        if not public:
            continue
        text_start, text_end = offset(tokens[first]), offset(tokens[last]) + len(tokens[last].value)
        if kind in {'fn', 'method'} and tokens[last].kind == '}':
            body = next(index for index in range(first, last + 1) if tokens[index].kind == '{')
            text_end = offset(tokens[body])
        signature = dedent(source[text_start:text_end].rstrip())
        name = declaration.local_name or declaration.token.value
        if kind == 'method':
            receiver = declaration.receiver[1].removeprefix('*').removeprefix('const ')
            name = f'{receiver}.{name}'
        result.items.append(Item(kind, name, tokens[first].line, signature,
                                 comment_block(lines, tokens[first].line - 1), unsafe))
    return result


def dedent(text: str) -> str:
    rows = text.replace('\r\n', '\n').split('\n')
    indents = [len(row) - len(row.lstrip()) for row in rows[1:] if row.strip()]
    trim = min(indents, default=0)
    return '\n'.join([rows[0]] + [row[trim:] for row in rows[1:]])


def discover(roots: list[Path]) -> list[tuple[Path, str]]:
    found, seen = [], {}
    for root in roots:
        if not root.is_dir():
            raise DocError(f'source root is not a directory: {root}')
        for path in sorted(root.rglob('*.dg')):
            relative = path.relative_to(root).with_suffix('')
            name = '.'.join(relative.parts)
            if name in seen:
                raise DocError(f'module {name!r} is present in multiple source roots')
            seen[name] = path
            found.append((path, name))
    return sorted(found, key=lambda pair: pair[1])


def first_sentence(text: str) -> str:
    paragraph = text.split('\n\n', 1)[0]
    head, sep, rest = paragraph.partition(' — ')
    summary = rest if sep and '.' in head else paragraph
    end = summary.find('. ')
    return (summary[:end + 1] if end >= 0 else summary).strip()


def table_cell(text: str) -> str:
    return text.replace('|', r'\|')


def anchor(kind: str, name: str) -> str:
    return f'{kind}-{name}'.lower().replace('.', '-')


def module_page(doc: ModuleDoc, source_link: str) -> str:
    out = [f'# `{doc.name}`', '', '<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->', '']
    if doc.doc:
        out += [doc.doc, '']
    out += [f'- 源码：[{doc.path.name}]({source_link})', f'- 导入：`import {doc.name};`（编译时提供包含该模块的 `--root`）']
    if doc.imports:
        out.append('- 依赖：' + '、'.join(f'`{name}`' for name in doc.imports))
    out.append('')
    if not doc.items:
        out += ['该模块没有公开声明。', '']
        return '\n'.join(out)
    out += ['## 目录', '', '| 名称 | 类别 | 摘要 |', '| --- | --- | --- |']
    labels = dict(SECTIONS)
    for kind, _ in SECTIONS:
        for item in (item for item in doc.items if item.kind == kind):
            flag = ' ⚠unsafe' if item.unsafe else ''
            out.append(f'| [`{item.name}`](#{anchor(kind, item.name)}) | {labels[kind]}{flag} | '
                       f'{table_cell(first_sentence(item.doc))} |')
    out.append('')
    for kind, heading in SECTIONS:
        items = [item for item in doc.items if item.kind == kind]
        if not items:
            continue
        out += [f'## {heading}', '']
        for item in items:
            out += [f'<a id="{anchor(kind, item.name)}"></a>', f'### `{item.name}`', '',
                    # Signatures are not whole modules; dong_doctest skips them.
                    '```dong ignore', item.signature, '```', '']
            if item.unsafe:
                out += ['> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。', '']
            out += [item.doc or '*（源码中没有文档注释。）*', '',
                    f'<sub>[源码第 {item.line} 行]({source_link}#L{item.line})</sub>', '']
    return '\n'.join(out).rstrip('\n') + '\n'


def index_page(docs: list[ModuleDoc], title: str) -> str:
    out = [f'# {title}', '', '<!-- 由 tools/dongdoc.py 生成，请勿手工编辑。 -->', '',
           '标准库没有自动导入，也没有默认堆；使用前显式 `import` 并给编译器加 `--root lang/std`。', '',
           '| 模块 | 公开声明 | 说明 |', '| --- | ---: | --- |']
    for doc in docs:
        out.append(f'| [`{doc.name}`]({doc.name}.md) | {len(doc.items)} | {table_cell(first_sentence(doc.doc))} |')
    return '\n'.join(out) + '\n'


def build(roots: list[Path], output: Path, title: str) -> dict[Path, str]:
    docs = [render_module(path, f'{name.replace(".", "/")}.dg') for path, name in discover(roots)]
    pages = {}
    for doc in docs:
        try:
            link = Path(os.path.relpath(doc.path.resolve(), output.resolve())).as_posix()
        except ValueError:  # different Windows drives have no relative path
            link = doc.path.resolve().as_uri()
        pages[output / f'{doc.name}.md'] = module_page(doc, link)
    pages[output / 'index.md'] = index_page(docs, title)
    return pages


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description='Dong API reference generator')
    parser.add_argument('--root', type=Path, action='append', required=True, help='module source root (repeatable)')
    parser.add_argument('--output', type=Path, required=True, help='directory for index.md and <module>.md pages')
    parser.add_argument('--title', default='Dong 标准库参考')
    parser.add_argument('--check', action='store_true', help='report stale or missing pages; write nothing')
    parser.add_argument('--version', action='version', version=f'dongdoc {VERSION}')
    options = parser.parse_args(argv)
    try:
        pages = build(options.root, options.output, options.title)
        stale = [path for path, text in pages.items()
                 if not path.is_file() or path.read_text(encoding='utf-8') != text]
        if options.check:
            for path in stale:
                print(f'stale: {path.as_posix()}')
            return 1 if stale else 0
        options.output.mkdir(parents=True, exist_ok=True)
        for path in stale:
            with open(path, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(pages[path])
            print(f'wrote: {path.as_posix()}')
        return 0
    except DocError as error:
        print(f'dongdoc: {error}', file=sys.stderr)
        return 1
    except OSError as error:
        print(f'dongdoc: IO error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

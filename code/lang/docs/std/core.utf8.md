# `core.utf8`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.utf8 — strict UTF-8 scalar decode/encode and whole-slice validation. Only shortest-form encodings of U+0000..U+10FFFF are accepted; surrogates, overlong forms, C0/C1, F5..FF, bad continuations and truncation are rejected. No replacement-character tolerance, no BOM skipping, no state.

- 源码：[utf8.dg](../../std/core/utf8.dg)
- 导入：`import core.utf8;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`Decode`](#struct-decode) | 结构体 |  |
| [`decode`](#fn-decode) | 函数 ⚠unsafe | Decode exactly one scalar at start. |
| [`encode`](#fn-encode) | 函数 ⚠unsafe | Write the unique shortest encoding of scalar. |
| [`validate`](#fn-validate) | 函数 | True only when the whole slice is complete strict UTF-8. |

## 结构体

<a id="struct-decode"></a>
### `Decode`

```dong ignore
pub struct Decode {
    pub scalar: u32,
    pub width: usize,
}
```

*（源码中没有文档注释。）*

<sub>[源码第 8 行](../../std/core/utf8.dg#L8)</sub>

## 函数

<a id="fn-decode"></a>
### `decode`

```dong ignore
pub unsafe fn decode(bytes: []const u8, start: usize, out: *Decode) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Decode exactly one scalar at start. On failure Decode is untouched. The suffix is not inspected, so a valid leader with a broken tail still decodes.

<sub>[源码第 63 行](../../std/core/utf8.dg#L63)</sub>

<a id="fn-encode"></a>
### `encode`

```dong ignore
pub unsafe fn encode(scalar: u32, output: []u8, written: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Write the unique shortest encoding of scalar. Invalid scalars and short output are rejected before any byte or count is published.

<sub>[源码第 75 行](../../std/core/utf8.dg#L75)</sub>

<a id="fn-validate"></a>
### `validate`

```dong ignore
pub fn validate(bytes: []const u8) bool
```

True only when the whole slice is complete strict UTF-8. Read-only.

<sub>[源码第 106 行](../../std/core/utf8.dg#L106)</sub>

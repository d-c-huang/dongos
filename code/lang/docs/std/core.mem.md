# `core.mem`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.mem — raw byte-memory primitives with explicit pointer and length. All functions treat memory as untyped bytes; callers guarantee that every non-zero-length range is valid, mapped and large enough for the count.

- 源码：[mem.dg](../../std/core/mem.dg)
- 导入：`import core.mem;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`copy`](#fn-copy) | 函数 ⚠unsafe | Copy count bytes from src to dst. |
| [`move`](#fn-move) | 函数 ⚠unsafe | Copy count bytes, accepting overlapping ranges and identical addresses. |
| [`zero`](#fn-zero) | 函数 ⚠unsafe | Set count bytes at dst to zero. |
| [`compare`](#fn-compare) | 函数 ⚠unsafe | Lexicographic comparison of count unsigned bytes, returning -1, 0 or 1. |

## 函数

<a id="fn-copy"></a>
### `copy`

```dong ignore
pub unsafe fn copy(dst: *u8, src: *const u8, count: usize) void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Copy count bytes from src to dst. The source and destination ranges must not overlap; use move for ranges that may overlap. A zero count never touches memory and permits null pointers on either side.

<sub>[源码第 10 行](../../std/core/mem.dg#L10)</sub>

<a id="fn-move"></a>
### `move`

```dong ignore
pub unsafe fn move(dst: *u8, src: *const u8, count: usize) void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Copy count bytes, accepting overlapping ranges and identical addresses. A zero count performs no memory access.

<sub>[源码第 20 行](../../std/core/mem.dg#L20)</sub>

<a id="fn-zero"></a>
### `zero`

```dong ignore
pub unsafe fn zero(dst: *u8, count: usize) void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Set count bytes at dst to zero.

<sub>[源码第 43 行](../../std/core/mem.dg#L43)</sub>

<a id="fn-compare"></a>
### `compare`

```dong ignore
pub unsafe fn compare(a: *const u8, b: *const u8, count: usize) i32
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Lexicographic comparison of count unsigned bytes, returning -1, 0 or 1.

<sub>[源码第 52 行](../../std/core/mem.dg#L52)</sub>

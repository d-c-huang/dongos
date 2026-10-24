# `core.arena`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.arena — caller-supplied linear arena. The caller owns the storage; the arena only tracks base/capacity/used and hands out aligned byte offsets. No allocation, growth, zeroing, locks, global state or OS calls.

- 源码：[arena.dg](../../std/core/arena.dg)
- 导入：`import core.arena;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`Arena`](#struct-arena) | 结构体 |  |
| [`init`](#fn-init) | 函数 ⚠unsafe | Adopt caller storage. |
| [`allocate`](#fn-allocate) | 函数 ⚠unsafe | Reserve size bytes at the first alignment-aligned address at or after base+used. |
| [`rewind`](#fn-rewind) | 函数 ⚠unsafe | Roll used back to the byte mark. |

## 结构体

<a id="struct-arena"></a>
### `Arena`

```dong ignore
pub struct Arena {
    pub base: *u8,
    pub capacity: usize,
    pub used: usize,
}
```

*（源码中没有文档注释。）*

<sub>[源码第 9 行](../../std/core/arena.dg#L9)</sub>

## 函数

<a id="fn-init"></a>
### `init`

```dong ignore
pub unsafe fn init(arena: *Arena, storage: []u8) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Adopt caller storage. Rejects a null pointer with non-empty storage and any base+capacity overflow. On success sets base/capacity and used=0 without touching a single storage byte. On failure the Arena bytes stay unchanged.

<sub>[源码第 18 行](../../std/core/arena.dg#L18)</sub>

<a id="fn-allocate"></a>
### `allocate`

```dong ignore
pub unsafe fn allocate(arena: *Arena, size: usize, alignment: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Reserve size bytes at the first alignment-aligned address at or after base+used. alignment must be a non-zero power of two. All rounding, padding and range checks run before any write, so debug/release never overflow or panic. Success writes only *out = p and used = (p - base) + size and keeps base/capacity; failure keeps the entire Arena, out and storage unchanged.

<sub>[源码第 37 行](../../std/core/arena.dg#L37)</sub>

<a id="fn-rewind"></a>
### `rewind`

```dong ignore
pub unsafe fn rewind(arena: *Arena, mark: usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Roll used back to the byte mark. Requires mark <= used <= capacity and a valid arena interval; success changes only used. A mark is a byte offset, not a generation-checked handle: the caller owns post-rewind lifetimes.

<sub>[源码第 65 行](../../std/core/arena.dg#L65)</sub>

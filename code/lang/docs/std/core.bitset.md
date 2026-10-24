# `core.bitset`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.bitset — allocation-free bitset with LSB-first bit order. bit i lives in byte i/8 at bit i%8; 0 means free, 1 means occupied. Only bits in [0, bit_count) are valid logical bits; the high tail bits of the last byte and any bytes past storage_bytes(bit_count) are never read or written.

- 源码：[bitset.dg](../../std/core/bitset.dg)
- 导入：`import core.bitset;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`storage_bytes`](#fn-storage_bytes) | 函数 | Ceiling of bit_count / 8. |
| [`test`](#fn-test) | 函数 ⚠unsafe | Write the value of logical bit index into *out. |
| [`set_range`](#fn-set_range) | 函数 ⚠unsafe | Set or clear bits [start, start+count). |
| [`find_clear_run`](#fn-find_clear_run) | 函数 ⚠unsafe | Find the lowest start s >= start such that bits [s, s+count) are all clear (0). |

## 函数

<a id="fn-storage_bytes"></a>
### `storage_bytes`

```dong ignore
pub fn storage_bytes(bit_count: usize) usize
```

Ceiling of bit_count / 8. Computed without bit_count + 7, so it cannot overflow even for USIZE_MAX.

<sub>[源码第 12 行](../../std/core/bitset.dg#L12)</sub>

<a id="fn-test"></a>
### `test`

```dong ignore
pub unsafe fn test(bytes: []const u8, bit_count: usize, index: usize, out: *bool) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Write the value of logical bit index into *out. Returns false and leaves *out unchanged when index is not in [0, bit_count). Never touches storage.

<sub>[源码第 20 行](../../std/core/bitset.dg#L20)</sub>

<a id="fn-set_range"></a>
### `set_range`

```dong ignore
pub unsafe fn set_range(bytes: []u8, bit_count: usize, start: usize, count: usize, value: bool) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Set or clear bits [start, start+count). Returns false and leaves every byte unchanged on an invalid range. count == 0 succeeds without touching memory. Only the selected bits change; every other bit in the storage is preserved.

<sub>[源码第 36 行](../../std/core/bitset.dg#L36)</sub>

<a id="fn-find_clear_run"></a>
### `find_clear_run`

```dong ignore
pub unsafe fn find_clear_run(bytes: []const u8, bit_count: usize, start: usize, count: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Find the lowest start s >= start such that bits [s, s+count) are all clear (0). Read-only; never occupies a bit. Returns false and leaves *out unchanged when storage is short, start is out of range, the run cannot fit, or no such run exists.

<sub>[源码第 63 行](../../std/core/bitset.dg#L63)</sub>

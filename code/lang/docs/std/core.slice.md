# `core.slice`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.slice — byte-slice helpers. All comparisons and searches operate on raw bytes; NUL bytes and UTF-8 content carry no special meaning.

- 源码：[slice.dg](../../std/core/slice.dg)
- 导入：`import core.slice;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`equal`](#fn-equal) | 函数 |  |
| [`compare`](#fn-compare) | 函数 | Unsigned lexicographic comparison; the shorter slice compares smaller when one is a prefix of the other. |
| [`find_byte`](#fn-find_byte) | 函数 | Index of the first byte equal to value at or after start, or bytes.len when absent or when start is not less than the length. |
| [`range_valid`](#fn-range_valid) | 函数 | True when lower <= upper <= length. |

## 函数

<a id="fn-equal"></a>
### `equal`

```dong ignore
pub fn equal(a: []const u8, b: []const u8) bool
```

*（源码中没有文档注释。）*

<sub>[源码第 6 行](../../std/core/slice.dg#L6)</sub>

<a id="fn-compare"></a>
### `compare`

```dong ignore
pub fn compare(a: []const u8, b: []const u8) i32
```

Unsigned lexicographic comparison; the shorter slice compares smaller when one is a prefix of the other. Returns -1, 0 or 1.

<sub>[源码第 18 行](../../std/core/slice.dg#L18)</sub>

<a id="fn-find_byte"></a>
### `find_byte`

```dong ignore
pub fn find_byte(bytes: []const u8, value: u8, start: usize) usize
```

Index of the first byte equal to value at or after start, or bytes.len when absent or when start is not less than the length.

<sub>[源码第 32 行](../../std/core/slice.dg#L32)</sub>

<a id="fn-range_valid"></a>
### `range_valid`

```dong ignore
pub fn range_valid(length: usize, lower: usize, upper: usize) bool
```

True when lower <= upper <= length. Computed without addition, so it cannot overflow.

<sub>[源码第 44 行](../../std/core/slice.dg#L44)</sub>

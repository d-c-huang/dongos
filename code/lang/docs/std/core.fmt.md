# `core.fmt`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.fmt — buffer/callback formatting without allocation or a global output. Every formatter returns the number of bytes written (never NUL-terminated) as !usize, or error.errors.BufferTooSmall when the output buffer is too small. Capacity is checked before any byte is written, so a failure leaves the output buffer unchanged.

- 源码：[fmt.dg](../../std/core/fmt.dg)
- 导入：`import core.fmt;`（编译时提供包含该模块的 `--root`）
- 依赖：`core.errors`、`core.mem`

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`decimal`](#fn-decimal) | 函数 | Unsigned decimal, no padding or sign. |
| [`signed_decimal`](#fn-signed_decimal) | 函数 | Signed decimal with a leading '-' for negatives. |
| [`hexadecimal`](#fn-hexadecimal) | 函数 | Lowercase hexadecimal, no "0x" prefix and no padding. |
| [`write`](#fn-write) | 函数 | Copies bytes into output, preserving UTF-8 and embedded NUL bytes. |
| [`emit`](#fn-emit) | 函数 ⚠unsafe | Calls the provided SysV callback with bytes and forwards its error result. |

## 函数

<a id="fn-decimal"></a>
### `decimal`

```dong ignore
pub fn decimal(value: u64, output: []u8) !usize
```

Unsigned decimal, no padding or sign. Zero renders as "0".

<sub>[源码第 38 行](../../std/core/fmt.dg#L38)</sub>

<a id="fn-signed_decimal"></a>
### `signed_decimal`

```dong ignore
pub fn signed_decimal(value: i64, output: []u8) !usize
```

Signed decimal with a leading '-' for negatives. Handles i64::MIN without overflow by negating through unsigned wrapping arithmetic.

<sub>[源码第 46 行](../../std/core/fmt.dg#L46)</sub>

<a id="fn-hexadecimal"></a>
### `hexadecimal`

```dong ignore
pub fn hexadecimal(value: u64, output: []u8) !usize
```

Lowercase hexadecimal, no "0x" prefix and no padding. Zero renders as "0".

<sub>[源码第 67 行](../../std/core/fmt.dg#L67)</sub>

<a id="fn-write"></a>
### `write`

```dong ignore
pub fn write(bytes: []const u8, output: []u8) !usize
```

Copies bytes into output, preserving UTF-8 and embedded NUL bytes. The source and destination may overlap; the copy uses move semantics.

<sub>[源码第 92 行](../../std/core/fmt.dg#L92)</sub>

<a id="fn-emit"></a>
### `emit`

```dong ignore
pub unsafe fn emit(bytes: []const u8, sink: fn([]const u8)!void) !void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Calls the provided SysV callback with bytes and forwards its error result. There is no global output device, allocation or variadic formatting.

<sub>[源码第 100 行](../../std/core/fmt.dg#L100)</sub>

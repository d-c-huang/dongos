# `core.int`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

core.int — usize checked arithmetic and power-of-two alignment helpers. Checked helpers never trigger a debug overflow or divide-by-zero panic: the range test runs before the arithmetic that could overflow.

- 源码：[int.dg](../../std/core/int.dg)
- 导入：`import core.int;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`is_power_of_two`](#fn-is_power_of_two) | 函数 |  |
| [`add_checked`](#fn-add_checked) | 函数 ⚠unsafe | Write a + b to *out on success. |
| [`sub_checked`](#fn-sub_checked) | 函数 ⚠unsafe | Write a - b to *out on success. |
| [`mul_checked`](#fn-mul_checked) | 函数 ⚠unsafe | Write a * b to *out on success. |
| [`align_up`](#fn-align_up) | 函数 ⚠unsafe | Round value up to the next multiple of alignment (a non-zero power of two). |
| [`align_down`](#fn-align_down) | 函数 ⚠unsafe | Round value down to the previous multiple of alignment (a non-zero power of two). |

## 函数

<a id="fn-is_power_of_two"></a>
### `is_power_of_two`

```dong ignore
pub fn is_power_of_two(value: usize) bool
```

*（源码中没有文档注释。）*

<sub>[源码第 9 行](../../std/core/int.dg#L9)</sub>

<a id="fn-add_checked"></a>
### `add_checked`

```dong ignore
pub unsafe fn add_checked(a: usize, b: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Write a + b to *out on success. Returns false and leaves *out unchanged when the addition overflows usize.

<sub>[源码第 16 行](../../std/core/int.dg#L16)</sub>

<a id="fn-sub_checked"></a>
### `sub_checked`

```dong ignore
pub unsafe fn sub_checked(a: usize, b: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Write a - b to *out on success. Returns false and leaves *out unchanged when b is greater than a.

<sub>[源码第 24 行](../../std/core/int.dg#L24)</sub>

<a id="fn-mul_checked"></a>
### `mul_checked`

```dong ignore
pub unsafe fn mul_checked(a: usize, b: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Write a * b to *out on success. Returns false and leaves *out unchanged when the multiplication overflows usize.

<sub>[源码第 32 行](../../std/core/int.dg#L32)</sub>

<a id="fn-align_up"></a>
### `align_up`

```dong ignore
pub unsafe fn align_up(value: usize, alignment: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Round value up to the next multiple of alignment (a non-zero power of two). Returns false and leaves *out unchanged on an invalid alignment or overflow.

<sub>[源码第 40 行](../../std/core/int.dg#L40)</sub>

<a id="fn-align_down"></a>
### `align_down`

```dong ignore
pub unsafe fn align_down(value: usize, alignment: usize, out: *usize) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Round value down to the previous multiple of alignment (a non-zero power of two). Returns false and leaves *out unchanged on an invalid alignment.

<sub>[源码第 50 行](../../std/core/int.dg#L50)</sub>

# `arch.x86_64`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

arch.x86_64 — reviewed external-assembly wrappers for x86-64 hardware. Every declaration below is unsafe: the callee may require privilege, or its effect depends on CPU/page-table state the caller owns. The NASM bodies are in lang/std/arch/x86_64.asm; link names use the dg_arch_ prefix.

- 源码：[x86_64.dg](../../std/arch/x86_64.dg)
- 导入：`import arch.x86_64;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`CpuId`](#struct-cpuid) | 结构体 |  |
| [`in8`](#fn-in8) | 函数 ⚠unsafe | Port I/O. |
| [`out8`](#fn-out8) | 函数 ⚠unsafe | out8 writes one byte (value) to port. |
| [`read_cr3`](#fn-read_cr3) | 函数 ⚠unsafe | Page-table root. |
| [`write_cr3`](#fn-write_cr3) | 函数 ⚠unsafe |  |
| [`read_msr`](#fn-read_msr) | 函数 ⚠unsafe | Model-specific registers. |
| [`write_msr`](#fn-write_msr) | 函数 ⚠unsafe |  |
| [`read_tsc`](#fn-read_tsc) | 函数 ⚠unsafe | Time-stamp counter. |
| [`cpuid`](#fn-cpuid) | 函数 ⚠unsafe | CPUID. |
| [`lfence`](#fn-lfence) | 函数 ⚠unsafe | Ordering fences as thin wrappers. |
| [`sfence`](#fn-sfence) | 函数 ⚠unsafe |  |
| [`mfence`](#fn-mfence) | 函数 ⚠unsafe |  |

## 结构体

<a id="struct-cpuid"></a>
### `CpuId`

```dong ignore
pub struct CpuId { pub eax: u32, pub ebx: u32, pub ecx: u32, pub edx: u32 }
```

*（源码中没有文档注释。）*

<sub>[源码第 8 行](../../std/arch/x86_64.dg#L8)</sub>

## 函数

<a id="fn-in8"></a>
### `in8`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_in8") fn in8(port: u16) u8;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Port I/O. Privileged: needs CPL 0 or an IOPL that permits the port. in8 reads one byte from port into the low byte of the u8 result.

<sub>[源码第 12 行](../../std/arch/x86_64.dg#L12)</sub>

<a id="fn-out8"></a>
### `out8`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_out8") fn out8(port: u16, value: u8) void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

out8 writes one byte (value) to port.

<sub>[源码第 14 行](../../std/arch/x86_64.dg#L14)</sub>

<a id="fn-read_cr3"></a>
### `read_cr3`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_read_cr3") fn read_cr3() u64;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Page-table root. Privileged. write_cr3 changes the address space: the caller owns the page tables, the CR3 reserved bits and TLB/PGE semantics.

<sub>[源码第 18 行](../../std/arch/x86_64.dg#L18)</sub>

<a id="fn-write_cr3"></a>
### `write_cr3`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_write_cr3") fn write_cr3(value: u64) void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

*（源码中没有文档注释。）*

<sub>[源码第 19 行](../../std/arch/x86_64.dg#L19)</sub>

<a id="fn-read_msr"></a>
### `read_msr`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_read_msr") fn read_msr(msr: u32) u64;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Model-specific registers. Privileged. read_msr returns the 64-bit value; write_msr splits value into EDX:EAX. The caller owns MSR selection and reserved/undefined bits.

<sub>[源码第 24 行](../../std/arch/x86_64.dg#L24)</sub>

<a id="fn-write_msr"></a>
### `write_msr`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_write_msr") fn write_msr(msr: u32, value: u64) void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

*（源码中没有文档注释。）*

<sub>[源码第 25 行](../../std/arch/x86_64.dg#L25)</sub>

<a id="fn-read_tsc"></a>
### `read_tsc`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_read_tsc") fn read_tsc() u64;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Time-stamp counter. Available in user mode on most CPUs; the read itself is not a serializing barrier, so pair it with a fence for ordering.

<sub>[源码第 29 行](../../std/arch/x86_64.dg#L29)</sub>

<a id="fn-cpuid"></a>
### `cpuid`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_cpuid") fn cpuid(leaf: u32, subleaf: u32, out: *CpuId) void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

CPUID. Writes the four result registers into *out (eax/ebx/ecx/edx order). Preserves the SysV non-volatile registers, especially RBX which CPUID clobbers. CpuId is passed by pointer, never by value.

<sub>[源码第 34 行](../../std/arch/x86_64.dg#L34)</sub>

<a id="fn-lfence"></a>
### `lfence`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_lfence") fn lfence() void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Ordering fences as thin wrappers.

<sub>[源码第 37 行](../../std/arch/x86_64.dg#L37)</sub>

<a id="fn-sfence"></a>
### `sfence`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_sfence") fn sfence() void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

*（源码中没有文档注释。）*

<sub>[源码第 38 行](../../std/arch/x86_64.dg#L38)</sub>

<a id="fn-mfence"></a>
### `mfence`

```dong ignore
pub unsafe extern "sysv64" ("dg_arch_mfence") fn mfence() void;
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

*（源码中没有文档注释。）*

<sub>[源码第 39 行](../../std/arch/x86_64.dg#L39)</sub>

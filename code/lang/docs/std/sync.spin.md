# `sync.spin`

<!-- 由 tools/dongdoc.py 生成，请勿手工编辑；修改源码注释后重新生成。 -->

sync.spin — a spin lock over a single u32 cell, built on sequential-consistency atomics and the pause hint. It has no interrupt, preemption or scheduler integration; callers must enforce the locking discipline.

- 源码：[spin.dg](../../std/sync/spin.dg)
- 导入：`import sync.spin;`（编译时提供包含该模块的 `--root`）

## 目录

| 名称 | 类别 | 摘要 |
| --- | --- | --- |
| [`Lock`](#struct-lock) | 结构体 |  |
| [`try_lock`](#fn-try_lock) | 函数 ⚠unsafe | Try to acquire without waiting. |
| [`lock`](#fn-lock) | 函数 ⚠unsafe | Acquire the lock, spinning until it becomes free. |
| [`unlock`](#fn-unlock) | 函数 ⚠unsafe | Release the lock. |

## 结构体

<a id="struct-lock"></a>
### `Lock`

```dong ignore
pub struct Lock { pub state: u32 }
```

*（源码中没有文档注释。）*

<sub>[源码第 7 行](../../std/sync/spin.dg#L7)</sub>

## 函数

<a id="fn-try_lock"></a>
### `try_lock`

```dong ignore
pub unsafe fn try_lock(lock: *Lock) bool
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Try to acquire without waiting. Returns true on success.

<sub>[源码第 10 行](../../std/sync/spin.dg#L10)</sub>

<a id="fn-lock"></a>
### `lock`

```dong ignore
pub unsafe fn lock(lock: *Lock) void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Acquire the lock, spinning until it becomes free.

<sub>[源码第 15 行](../../std/sync/spin.dg#L15)</sub>

<a id="fn-unlock"></a>
### `unlock`

```dong ignore
pub unsafe fn unlock(lock: *Lock) void
```

> 调用方须位于 `unsafe { ... }` 块中，并自行保证文档列出的前提条件。

Release the lock. Only the holder may call this.

<sub>[源码第 26 行](../../std/sync/spin.dg#L26)</sub>

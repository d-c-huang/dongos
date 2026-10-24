# Dong 速查表

一页纸汇总 Dong v0.1 的语法。详细说明见[语言指南](guide.md)。

## 模块与声明

```dong
module app.demo;                          // 文件 <root>/app/demo.dg

import core.fmt;                          // 绑定 fmt
import core.errors as errors;             // 绑定 errors

pub const LIMIT: usize = 64;              // 常量：必须写类型
var counter: u64 = 0;                     // 全局：必须有初始值
type Index = usize;                       // 透明别名
pub error Overflow = 0x4000_0001;         // 错误码：程序内唯一

pub struct Pair { pub a: u32, b: u32 }    // 字段默认私有
packed struct Wire { tag: u8, len: u32 }  // 无填充
align(64) struct Line { v: u64 }          // 提高对齐
pub enum State { Off, On(u8) }            // 每个变体最多一个载荷

pub fn add(a: u64, b: u64) u64 { return a + b; }
unsafe fn raw(p: *u8) void {}             // 调用者要 unsafe 块
export("c_name") fn exported() void {}    // 固定链接名
fn (self: *Pair) sum() u32 {              // 方法：接收者 *T / *const T
    unsafe { return (*self).a + (*self).b; }
}
extern "sysv64" fn c_func(x: u64) u64;    // 外部函数（调用需 unsafe）
extern "sysv64" ("strlen") fn len(s: *const u8) usize;
```

## 类型

| 写法 | 含义 |
| --- | --- |
| `u8 … u64` `i8 … i64` `usize` `isize` `bool` | 标量（`usize`≡`u64`） |
| `*T` `*const T` | 裸指针 |
| `[N]T` | 数组 |
| `[]T` `[]const T` | 切片（ptr + len） |
| `?T` | 可选值 |
| `!T` `!void` | 错误结果 |
| `fn(A) R` `unsafe fn(A) R` `unsafe extern "win64" fn(A) R` | 函数指针 |
| `void` `noreturn` | 仅返回类型 |

## 语句与表达式

```dong
module app.statements;

error Bad = 0x4000_0002;

fn get(ok: bool) !u64 {
    if !ok { return error.Bad; }
    return 1;
}

fn demo(items: []const u64, maybe: ?u64) !u64 {
    let fixed = 1;                         // 不可变（推导为 i64）
    var total: u64 = 0;                    // 可变
    var later: u64;                        // 使用前必须整体赋值
    later = 5;
    var arr: [4]u8 = [0; 4];               // 重复初始化
    let part = arr[1..3];                  // 切片视图
    total += (fixed as u64) + later + part.len;
    if total > 10 { total = 10; } else if total == 0 { total = 1; } else {}
    while total < 20 { total += 1; }
    for i in 0..items.len { total += items[i]; }
    for v in items { total += v; }
    loop { break; }
    let v = maybe orelse 0;                // 解包可选值
    let w = try get(true);                 // 传播错误
    defer { arr[0] = 0; }                  // 离开块时执行：单条调用或 { 块 }
    match maybe {
        some(x) => { total += x; },
        null => {},
    }
    match get(false) {
        ok(x) => { total += x; },
        err(code) => { total += code & 0; },
    }
    return total + v + w;
}
```

## 运算符优先级（高 → 低）

`f() .x [i] [a..b]` → 前缀 `! ~ - & * try` → `as` → `* / %` → `+ -` → `<< >>` → `&` → `^` → `|` → `== != < <= > >=` → `&&` → `||` → `orelse`

求值顺序总是从左到右，每个子表达式只求值一次。

## 编译期内建

`sizeof(T)` · `alignof(T)` · `offsetof(T, field)` · `wrapping_add/sub/mul(a, b)`

## unsafe 内建（都必须在 `unsafe { }` 块中）

| 内建 | 说明 |
| --- | --- |
| `*p`、`p + n`、`p as usize`、`n as *T` | 裸指针操作 |
| `slice_from_raw_parts(p, n)` | 由指针构造切片 |
| `volatile_load(p)` `volatile_store(p, v)` | MMIO，恰好一次访问 |
| `read_unaligned(p)` `write_unaligned(p, v)` | 非对齐访问 |
| `atomic_load` `atomic_store` `atomic_compare_exchange` `atomic_fetch_add` | `u32`/`u64` 顺序一致原子 |
| `compiler_fence()` | 编译器屏障 |
| `asm { cli \| sti \| hlt \| pause \| int3 \| lfence \| sfence \| mfence }` | 单条无操作数指令 |

## 运行时检查（panic kind）

1 越界 · 2 溢出（仅 debug）· 3 除零 · 4 移位量 · 5 有符号除法溢出

## 常用命令

```powershell
python -m lang.dongc --check --root src --root lang/std src/app/main.dg
python -m lang.dongc --root src --emit-asm build/main.asm src/app/main.dg
python tools/dongfmt.py --write src/app/main.dg
python tools/dong_explain.py E0301
python tools/dongdoc.py --root lang/std --output lang/docs/std
python tools/dong_doctest.py lang/docs
```

## 诊断代码

| 代码 | 含义 |
| --- | --- |
| E0001 | 词法 |
| E0101 | 语法 |
| E0201 | 名称未定义/重复/不可见 |
| E0202 | 模块缺失/冲突/循环 |
| E0301 | 类型不匹配 |
| E0302 | 布局/常量 |
| E0401 | 可能未初始化 |
| E0402 | 不可变赋值/缺少 return |
| E0403 | match 不穷尽/重复 |
| E0501 | 需要 unsafe / defer、try 上下文 |
| E0601 | 不支持的特性/超出限制 |
| E0602 | 错误码/链接名冲突 |

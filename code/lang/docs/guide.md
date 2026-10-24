# Dong 语言指南

本指南按主题完整介绍 Dong v0.1 当前实现的语言。它面向写代码的人：每节给出可编译的例子和容易踩的坑。逐条的规范性要求（ABI 寄存器分配、表示细节、验收条件）以[语言规格](../spec.md)为准；实现进度与实测证据见[语言线 README](../README.md)。

> 本页所有 `dong` 代码块都由 `tools/dong_doctest.py` 实际编译。

**目录**

1. [源文件与词法](#1-源文件与词法)
2. [类型一览](#2-类型一览)
3. [整数语义与检查](#3-整数语义与检查)
4. [绑定、常量与全局变量](#4-绑定常量与全局变量)
5. [表达式与运算符](#5-表达式与运算符)
6. [控制流](#6-控制流)
7. [数组与切片](#7-数组与切片)
8. [结构体与内存布局](#8-结构体与内存布局)
9. [指针与 unsafe](#9-指针与-unsafe)
10. [函数、方法与函数指针](#10-函数方法与函数指针)
11. [枚举、可选值与 match](#11-枚举可选值与-match)
12. [错误结果、try 与 defer](#12-错误结果try-与-defer)
13. [模块与可见性](#13-模块与可见性)
14. [外部函数与调用约定](#14-外部函数与调用约定)
15. [硬件内建与内联汇编](#15-硬件内建与内联汇编)
16. [运行时接口与限制](#16-运行时接口与限制)
17. [尚不支持的特性](#17-尚不支持的特性)

## 1. 源文件与词法

- 源文件是 UTF-8（可带 BOM），扩展名 `.dg`，换行可为 LF 或 CRLF。
- 标识符区分大小写，可以是 Unicode（包括中文），不做规范化。关键字固定为英文。
- 注释：`// 行注释` 和 `/* 块注释 */`，块注释**不嵌套**。
- 整数字面量：十进制 `1_000`、十六进制 `0xff`、二进制 `0b1010`，`_` 只能在数字之间。没有浮点和字符字面量。
- 字符串 `"..."` 的类型是 `[]const u8`（UTF-8 字节，不含结尾 NUL），转义有 `\n \r \t \0 \\ \" \xNN`，不能含未转义换行。
- 简单语句和顶层的 `const`/`var`/`type`/`error`/`import` 以 `;` 结尾；块、函数和类型声明不加分号。

```dong
module guide.lexical;

const 问候: []const u8 = "你好, Dong\n";
const MASK: u32 = 0xffff_0000;
const FLAGS: u8 = 0b0000_0101;

/* 块注释不能嵌套 */
fn 长度() usize {
    return 问候.len;      // 按 UTF-8 字节计数：13
}
```

保留关键字：`module import as pub const let var type struct enum fn extern unsafe packed align export if else while loop for in match break continue return defer try error orelse true false null void noreturn asm`。

## 2. 类型一览

| 类型 | 大小/对齐 | 说明 |
| --- | --- | --- |
| `u8 u16 u32 u64` / `i8 i16 i32 i64` | 1/2/4/8 | 无符号 / 补码整数 |
| `usize` / `isize` | 8 | 与 `u64` / `i64` **是同一类型** |
| `bool` | 1 | `true`/`false`，存储为 1/0 |
| `*T` / `*const T` | 8 | 可写 / 只读裸指针，可为 `null` |
| `[N]T` | `N*sizeof(T)` | 定长数组，`N` 为正的编译期整数 |
| `[]T` / `[]const T` | 16 | 切片：数据指针 + `usize` 长度 |
| `fn(A, B) R` | 8 | 函数指针，非空 |
| `?T` | 16 | 可选值 `{tag, value}` |
| `!T` | 16 | 错误结果 `{code, value}` |
| 无载荷 `enum` | 8 | `u64` 标签 |
| 带载荷 `enum` | 16 | `{tag, value}` |
| `void` / `noreturn` | — | 只能作返回类型 |

`type Name = T;` 声明**透明**别名：它与 `T` 完全是同一类型，只是换个名字。

```dong
module guide.aliases;

type PhysAddr = u64;
type Handler = fn(u64) u64;

fn page_of(addr: PhysAddr) PhysAddr {
    let mask: u64 = 4095;
    return addr & ~mask;
}
```

无类型内存用 `*u8` / `[]u8` 表示；不存在 `*void`、零长数组和空结构体。

## 3. 整数语义与检查

**没有隐式转换。** 不同宽度或符号的整数不能混合运算或比较，必须 `as`：

```dong
module guide.integers;

fn mix(a: u8, b: i32, c: u64) u64 {
    let widened = a as u64;            // 零扩展
    let signed = b as i64;             // 符号扩展
    let truncated = c as u16;          // 截取低 16 位
    let flag = (a != 0) as u64;        // bool -> 整数只能显式
    return widened + (signed as u64) + (truncated as u64) + flag;
}
```

未定类型的整数字面量按上下文确定类型，无上下文时为 `i64`；字面量超出目标类型范围是编译错误。

运行时检查：

| 情况 | debug | release |
| --- | --- | --- |
| `+ - *` 与一元 `-` 溢出 | panic（kind 2） | 按位宽取模 |
| 数组/切片越界、非法区间 | panic（kind 1） | panic |
| 除数为 0 | panic（kind 3） | panic |
| 移位量 ≥ 位宽 | panic（kind 4） | panic |
| 有符号 `MIN / -1`、`MIN % -1` | panic（kind 5） | panic |

需要明确的取模算术时，用 `wrapping_add/sub/mul`，它们在两种模式下都按位宽取模，也能用于常量：

```dong
module guide.wrapping;

const SEED: u32 = wrapping_mul(0x9e37_79b9 as u32, 3);

fn hash_step(h: u32, byte: u8) u32 {
    return wrapping_add(wrapping_mul(h, 31), byte as u32);
}
```

整数除法向零截断，余数与被除数同号。有符号右移是算术移位。移位右侧必须是 `usize`。

## 4. 绑定、常量与全局变量

| 写法 | 位置 | 含义 |
| --- | --- | --- |
| `let x = e;` / `let x: T = e;` | 局部 | 不可重新赋值；聚合字段也不可写 |
| `var x = e;` / `var x: T;` | 局部 | 可赋值；未初始化的必须在每条使用路径前整体赋值 |
| `const X: T = e;` | 顶层或局部 | 编译期常量，有只读静态存储，可取地址 |
| `var X: T = e;` | 顶层 | 可写全局，初始化器必须是编译期值 |

```dong
module guide.bindings;

const PAGE_SIZE: usize = 4096;
const PAGES: usize = 4;
const BANNER: []const u8 = "DongOS";
var buffer: [PAGES * 16]u8 = [0; PAGES * 16];
var cursor: *u8 = &buffer[0];               // 全局地址常量通过重定位生成

fn fill() usize {
    const STEP: usize = 2;                  // 局部 const 可用于数组长度
    var marks: [STEP]u64 = [1, 2];
    var written: usize;
    written = 0;                            // 首次使用前整体赋值
    for i in 0..buffer.len {
        if i % STEP == 0 {
            buffer[i] = BANNER[i % BANNER.len];
            written += 1;
        }
    }
    marks[0] = written as u64;
    return written + PAGE_SIZE;
}
```

要点：

- 局部变量只在 `let`/`var`/字面量上推导类型；顶层 `const`/`var` 必须写类型。
- `let x = null;` 和空数组字面量无法推导，需要写类型。
- 同一块内不能重复声明；内层块可以遮蔽外层名称。
- 全零的全局变量进入 BSS，其余进入 data，常量进入 rodata。
- 确定初始化按控制流求交集：仅在 `if` 一个分支或循环体里赋值，不足以证明已初始化（E0401）。

## 5. 表达式与运算符

优先级从高到低（同级左结合，前缀与 `orelse` 右结合）：

| 级别 | 运算符 |
| --- | --- |
| 后缀 | `f(x)`、`.field`、`[i]`、`[lo..hi]` |
| 前缀 | `!` `~` `-` `&` `*` `try` |
| 转换 | `e as T` |
| 乘法 | `* / %` |
| 加法 | `+ -` |
| 移位 | `<< >>` |
| 按位 | `&`，然后 `^`，然后 `|`（各自一级） |
| 比较 | `== != < <= > >=`（禁止链式） |
| 逻辑 | `&&`，然后 `||`（短路） |
| 可选回退 | `orelse`（短路） |

- **求值顺序固定为从左到右**，每个子表达式恰好求值一次，包括调用参数和字面量元素。
- 赋值 `= += -= *= /= %= &= |= ^= <<= >>=` 是语句，不产生值；复合赋值的左侧地址只求值一次。
- 单独的表达式语句只能是函数调用（或 `try` 调用）。
- 条件里出现结构体字面量时要加括号：`if (p == Point { x: 0, y: 0 })` 之类的写法会与块混淆。
- 聚合值（结构体、数组）不能用 `==` 比较。

## 6. 控制流

```dong
module guide.control;

fn classify(values: []const i64) u64 {
    var score: u64 = 0;
    for v in values {                  // 按值遍历，循环变量不可变
        if v < 0 {
            continue;
        } else if v == 0 {
            break;
        } else {
            score += v as u64;
        }
    }
    var i: usize = 0;
    while i < 3 {
        i += 1;
    }
    for k in 2..5 {                    // usize 区间，边界只求值一次
        score += k;
    }
    loop {
        score += 1;
        if score > 100 { break; }
    }
    return score;
}
```

- 没有循环标签，`break`/`continue` 作用于最近的循环；没有 `break 值`。
- `if`/`match` 是语句；没有三元运算符和尾表达式返回。
- `noreturn` 返回类型表示函数不会正常返回：函数体内不能有 `return`，每条路径必须死循环或调用另一个 `noreturn` 函数。

```dong
module guide.halt;

fn halt_forever() noreturn {
    loop {
        unsafe { asm { hlt } }
    }
}
```

## 7. 数组与切片

```dong
module guide.arrays;

fn checksum(bytes: []const u8) u32 {
    var sum: u32 = 0;
    for b in bytes {
        sum = wrapping_add(sum, b as u32);
    }
    return sum;
}

fn demo() u32 {
    var data: [8]u8 = [1, 2, 3, 4, 5, 6, 7, 8];
    let head = data[..4];               // []u8，可写，因为 data 是 var
    head[0] = 100;                      // let 只禁止重新绑定描述符，元素仍可写
    let frozen = [9, 9];
    let view = frozen[..];              // []const i64，因为 frozen 是 let
    let tail: []const u8 = data[4..];   // []u8 可隐式转成 []const u8
    return checksum(head) + checksum(tail) + (view.len as u32);
}
```

规则：

- 索引类型是 `usize`，总是检查 `i < len`；`a[lo..hi]` 检查 `lo <= hi <= len`。
- 从数组创建切片时，可写性继承源位置：`var` 数组得到 `[]T`，`let` 数组或只读字段得到 `[]const T`。
- 切片的 `let` 绑定不会让元素变成只读——这与 `let p: *T` 一致。
- 编译器拒绝从可能未对齐的 `packed` 数组字段直接取切片；先复制到普通数组，或确认对齐后用 `slice_from_raw_parts`。
- 切片不拥有存储，没有生命周期分析；存储失效后切片也随之失效。
- `slice_from_raw_parts(ptr, len)` 从裸指针构造切片，需要 `unsafe`。

## 8. 结构体与内存布局

```dong
module guide.layout;

struct Header {
    magic: u32,          // 偏移 0
    flags: u8,           // 偏移 4
    size: u64,           // 偏移 8（对齐到 8）
}                        // 大小 16，对齐 8

packed struct Wire {
    kind: u8,            // 偏移 0
    length: u32,         // 偏移 1，无填充
}                        // 大小 5，对齐 1

align(64) struct CacheLine {
    counter: u64,
}                        // 大小 64，对齐 64

const HEADER_SIZE: usize = sizeof(Header);
const SIZE_OFFSET: usize = offsetof(Header, size);
const WIRE_SIZE: usize = sizeof(Wire);
const LINE_ALIGN: usize = alignof(CacheLine);

fn copy_header(src: *const Header, dst: *Header) void {
    unsafe {
        *dst = *src;                     // 整体复制
        (*dst).flags = 1;
    }
}
```

- 普通结构体按声明顺序布局，字段偏移按字段对齐取整，整体大小补齐到整体对齐；字段**永不重排**。
- `packed` 取消所有填充、整体对齐为 1；直接读写字段时编译器生成允许非对齐的访问。
- `align(N)` 提高整体对齐（`N` 为 1–4096 的 2 的幂，不能低于自然对齐），不能与 `packed` 同用。
- 结构体字面量必须给出每个字段且仅一次，没有默认值。未初始化的结构体变量不能逐字段填充。
- 复制包含填充字节，填充值未规定；跨磁盘/网络/IPC 的数据要逐字段编码。
- `--emit-layout` 导出每个类型的大小、对齐和字段偏移 JSON，`tools/gen_offsets.py` 再生成 NASM `struc`，汇编不再手写偏移表。

## 9. 指针与 unsafe

```dong
module guide.pointers;

fn sum_raw(p: *const u32, count: usize) u64 {
    var total: u64 = 0;
    unsafe {
        for i in 0..count {
            total += *(p + i) as u64;     // 指针加减按元素大小缩放
        }
    }
    return total;
}

fn demo() u64 {
    var values: [4]u32 = [1, 2, 3, 4];
    let p: *u32 = &values[0];
    let readonly: *const u32 = p;           // *T 可以隐式转成 *const T
    var address: usize = 0;
    unsafe {
        address = p as usize;               // 指针与 usize 互转需要 unsafe
        let again = address as *u32;
        *again = 10;
        let s = slice_from_raw_parts(p, values.len);
        s[1] = 20;
    }
    return sum_raw(readonly, values.len) + (address & 0);
}
```

只有下列操作需要 `unsafe { ... }` 块：

- 裸指针的解引用、索引、加减，整数与指针互转，去掉 `const`。
- `slice_from_raw_parts`。
- 调用 `unsafe fn`、`extern` 函数或**任意**函数指针。
- `asm` 块、volatile/原子/非对齐内建。

`unsafe fn` 只是声明“调用者必须满足契约”：调用点要进入 `unsafe` 块，而函数体里的不安全操作仍要自己写 `unsafe` 块。`unsafe` 不会关闭边界、溢出等普通检查。

调用者负责：地址有效且已映射、对齐、初始化、类型表示正确、生命周期、别名与并发同步。编译器不做空指针或悬垂指针检查。

## 10. 函数、方法与函数指针

```dong
module guide.functions;

fn double(x: u64) u64 { return x * 2; }
fn square(x: u64) u64 { return x * x; }

const TABLE: [2]fn(u64) u64 = [double, square];
var current: fn(u64) u64 = double;

fn apply(f: fn(u64) u64, x: u64) u64 {
    unsafe {
        return f(x);                       // 调用函数指针总是需要 unsafe
    }
}

fn pick(fast: bool) fn(u64) u64 {
    if fast { return double; }
    return square;
}

fn demo() u64 {
    current = pick(false);
    var total: u64 = apply(current, 3);
    for f in TABLE {
        total += apply(f, 4);
    }
    if current == square { total += 1; }    // 同类型函数指针可比较相等
    return total;
}
```

- 函数写作 `fn name(params) R { ... }`；没有重载、默认参数、可变参数和嵌套函数。模块内声明先收集再检查，可以前向调用和互相递归。
- 函数名直接产生代码指针；`&function_name` 被拒绝。函数指针非空，不接受 `null` 或整数转换。
- 函数指针类型包含 ABI 和 `unsafe` 属性，必须精确匹配：`unsafe fn(u64) u64`、`unsafe extern "win64" fn(handle: *u8) u64`。参数名不参与类型身份。
- 方法 `fn (self: *T) name(...) R` 是普通函数的语法糖，只能定义在 `T` 的声明模块；`p.name(x)` 等价于 `name(p, x)`，接收者类型必须精确匹配（不自动取地址、解引用或加 `const`）。

## 11. 枚举、可选值与 match

```dong
module guide.matching;

enum Shape { Dot, Circle(u64), Square(u64) }
enum Mode { Read, Write }

fn area(s: Shape) u64 {
    match s {
        Shape.Dot => { return 0; },
        Shape.Circle(r) => { return 3 * r * r; },
        _ => { return 1; },             // 兜底只能在最后
    }
    return 0;
}

fn first_even(values: []const u64) ?u64 {
    for v in values {
        if v % 2 == 0 { return v; }
    }
    return null;
}

fn demo(mode: Mode) u64 {
    let numbers: [3]u64 = [3, 5, 6];
    var total: u64 = area(Shape.Square(4));
    match first_even(numbers[..]) {
        some(v) => { total += v; },
        null => {},
    }
    match total > 10 {
        true => { total += 1; },
        false => {},
    }
    if mode == Mode.Write {              // 无载荷枚举可比较相等
        total += 100;
    }
    let fallback = first_even(numbers[..1]) orelse 7;
    return total + fallback;
}
```

- 变体按声明顺序从 0 编号，不支持自定标签值；每个变体最多一个载荷，载荷限整数、`bool`、裸指针或函数指针。
- `match` 支持枚举、`bool`、`?T`（模式 `null` / `some(x)`）和 `!T`（模式 `ok(x)` / `err(code)`）。必须穷尽，不能重复，`_` 必须最后。
- 被匹配的值只求值一次；分支绑定不可变，仅在分支内可见。没有守卫和范围模式。
- `?T` 的载荷限制同上，不能嵌套 `??T`。有上下文时 `T` 自动提升为 `?T`。
- `a orelse b` 仅在 `a` 为空时求值 `b`；`b` 也可以是 `return e`、`break`、`continue`。

## 12. 错误结果、try 与 defer

```dong
module guide.results;

import core.errors as errors;

error NotFound = 0x3000_0001;

fn lookup(key: u64) !u64 {
    if key == 0 { return error.NotFound; }
    return key * 10;
}

fn copy_into(out: []u8, value: u8) !void {
    if out.len == 0 { return error.errors.BufferTooSmall; }   // 引用导入模块的错误
    out[0] = value;
    return;
}

fn total(keys: []const u64) !u64 {
    var sum: u64 = 0;
    for k in keys {
        sum += try lookup(k);              // 失败时运行清理并原样传播
    }
    return sum;
}

fn demo() u64 {
    let keys: [2]u64 = [1, 2];
    var buffer: [1]u8 = [0];
    match copy_into(buffer[..], 7) {
        ok => {},
        err(code) => { return code; },
    }
    match total(keys[..]) {
        ok(v) => { return v; },
        err(code) => {
            if code == 0x3000_0001 { return 0; }
            return 1;
        },
    }
    return 2;
}
```

- `error Name = 编号;` 在模块顶层声明，编号在 `1..=0xffff_ffff`，**在最终程序中唯一**（否则 E0602）。0 表示成功。
- 导入模块别名为 `errors` 时，用 `error.errors.Name` 引用它的公开错误。
- `return value;` 成功，`return error.Name;` 失败；`!void` 用 `return;` 成功；同类型结果可直接 `return other();` 转发。
- `try` 只能用在返回错误类型的函数中；直接丢弃 `!T` 调用结果是错误（E0301）。
- 没有错误字符串注册表；需要文字说明时自行维护映射。

### defer

```dong
module guide.cleanup;

var log: u64 = 0;

fn note(n: u64) void { log = log * 10 + n; }

fn nested() u64 {
    log = 0;
    defer note(1);
    {
        defer note(2);
        note(3);
    }                                   // 先打印 3，离开内层块时执行 2
    for i in 0..2 {
        defer note(4);                  // 每次迭代独立注册和执行
        if i == 1 { continue; }
    }
    return log;                         // 返回值先保存（3244），然后执行 note(1)
}
```

- `defer` 后接单条调用或 `{ ... }` 块，执行到该语句时注册，离开所在**词法块**时按逆序执行，包括正常结束、`return`、`try` 传播、`break`、`continue`。
- 返回表达式先求值保存，再执行清理，清理不能改变已保存的返回值。
- `defer` 体内禁止 `return`、`try`、`break`、`continue` 和嵌套 `defer`（E0501）。
- panic、CPU 异常不会运行 `defer`。

## 13. 模块与可见性

- 每个文件一个 `module a.b;`，从 `--root` 指定的源码根下的 `a/b.dg` 加载；不搜索当前目录或网络。缺失、多处重复、循环导入均报 E0202。
- `import a.b;` 绑定 `b`，`import a.b as c;` 绑定 `c`，通过 `c.name` 访问。没有通配导入、再导出和预导入。
- 顶层声明默认私有，`pub` 公开函数、类型、错误、常量和全局变量。结构体字段默认私有，需要 `pub field: T`；枚举变体随枚举可见。
- 公开签名不能暴露私有类型。私有方法不能跨模块调用。
- 链接符号按模块与名称编码：`__dg_m<模块名十六进制>_f<名称十六进制>`，方法为 `..._t<类型>_f<方法>`。需要固定外部名时用 `export("name")`。

```dong
module guide.visibility;

pub struct Account {
    pub id: u64,
    balance: u64,              // 私有：只有本模块能读写
}

pub fn (self: *Account) deposit(amount: u64) void {
    unsafe { (*self).balance += amount; }
}

pub fn (self: *const Account) balance_of() u64 {
    unsafe { return (*self).balance; }
}

export("account_open") fn open(out: *Account, id: u64) void {
    unsafe { *out = Account { id: id, balance: 0 }; }
}
```

## 14. 外部函数与调用约定

普通 Dong 函数使用 SysV AMD64 的整数子集：参数依次放在 `rdi rsi rdx rcx r8 r9`，其余入栈；切片、`?T`、`!T` 和带载荷枚举是 16 字节“双字值”，占两个连续寄存器（不够时整体入栈），返回时用 `rax:rdx`。没有 red zone，每个函数建立 `rbp` 帧，不生成任何 SIMD/浮点指令。

```dong
module guide.ffi;

extern "sysv64" fn host_write(fd: u32, data: *const u8, length: usize) i64;
extern "sysv64" ("memcmp") fn c_memcmp(a: *const u8, b: *const u8, n: usize) i32;
extern "win64" fn firmware_call(handle: *u8, message: *const u16) u64;

export("efi_callback") extern "win64" fn callback(handle: *u8) u64 {
    return 0;                          // Win64 入口桥接到 SysV 函数体
}

type OutputString = unsafe extern "win64" fn(self: *u8, text: *const u16) u64;

fn say(text: []const u8) i64 {
    unsafe {
        return host_write(1, text.ptr, text.len);
    }
}
```

- `extern "sysv64"` / `extern "win64"` 无函数体时声明外部符号，默认按 `unsafe` 处理；`("name")` 指定实际链接名。
- 外部函数只接受标量（整数、`bool`、指针、函数指针、无载荷枚举）参数和返回值；切片和结果类型要拆成指针/长度/状态参数。
- **结构体和数组任何时候都不能按值跨函数**，用指针传递（E0601）。
- 带函数体的 `extern "win64" fn` 由编译器生成桥接：保存 Win64 非易失寄存器（含 XMM6–XMM15），重排参数后调用 SysV 函数体。目标必须已启用 SSE2；不生成 SEH 展开信息。
- 系统调用入口、中断入口、上下文切换等需要特殊寄存器约定的代码用手写汇编实现，不要用 `extern` 函数冒充。

## 15. 硬件内建与内联汇编

所有内建都要求显式 `unsafe` 块（即便在 `unsafe fn` 里）。

| 内建 | 用途 |
| --- | --- |
| `volatile_load(p)` / `volatile_store(p, v)` | 恰好一次指定宽度访问（MMIO），要求自然对齐；不是线程同步 |
| `read_unaligned(p)` / `write_unaligned(p, v)` | 非对齐整数读写，可能拆分，不能用于 MMIO 或原子 |
| `atomic_load(p)` / `atomic_store(p, v)` | `u32`/`u64`，自然对齐，普通可缓存内存，顺序一致性 |
| `atomic_compare_exchange(p, expected, desired)` | 强 CAS，返回旧值；旧值等于 `expected` 即成功 |
| `atomic_fetch_add(p, delta)` | 模加法，返回旧值 |
| `compiler_fence()` | 编译器内存屏障，不生成 CPU 指令 |

volatile 与非对齐内建支持全部八种整数类型；写入值类型必须与指针目标精确一致。

```dong
module guide.hardware;

struct Mmio { status: u32, data: u32 }
packed struct Frame { tag: u8, value: u32 }

var refcount: u64 = 0;

fn poll(regs: *Mmio) u32 {
    unsafe {
        while volatile_load(&(*regs).status) & 1 == 0 {
            asm { pause }
        }
        volatile_store(&(*regs).data, 0);
        return volatile_load(&(*regs).data);
    }
}

fn retain() u64 {
    unsafe {
        return atomic_fetch_add(&refcount, 1) + 1;
    }
}

fn try_claim(flag: *u32) bool {
    unsafe {
        return atomic_compare_exchange(flag, 0, 1) == 0;
    }
}

fn frame_value(f: *const Frame) u32 {
    unsafe {
        return read_unaligned(&(*f).value);
    }
}
```

内联汇编只有一种形式：`unsafe { asm { 指令 } }`，每块恰好一条**无操作数**指令，白名单为 `cli sti hlt pause int3 lfence sfence mfence`。每个 `asm` 块都是不可删除的副作用和完整的编译器内存屏障。端口 I/O、CR/MSR、CPUID 等使用标准库 `arch.x86_64` 中的外部汇编包装器。

## 16. 运行时接口与限制

检查失败时调用目标提供的唯一运行时符号：

```dong ignore
extern "sysv64" fn __dong_panic(kind: u32, line: u32, file: *const u8, file_len: usize) noreturn;
```

`kind`：1 越界、2 溢出、3 除零、4 移位量、5 有符号除法溢出。`file` 是不含 NUL 的 UTF-8 路径（源码根相对）。实现不得返回、分配内存或抛异常；panic 不运行 `defer`。不需要检查的程序不会依赖该符号，产物清单（`--emit-manifest`）的 `runtime_symbols` 列出实际依赖。

实现限制：

- 函数最坏栈帧（局部变量、临时值、保存寄存器、对齐填充、出参区/shadow space）不得超过 **4096 字节**，超限报 E0601。大对象放进全局 `var` 或调用方提供的内存。
- 静态初始化数据总量上限 16 MiB。
- 编译期不执行用户函数；编译期地址不能转整数、比较或参与运算。
- 没有栈探测、red zone、隐式 `memcpy`/`memset` 依赖。

## 17. 尚不支持的特性

以下写法会被诊断，而不是按近似语义编译：浮点与向量类型、泛型、接口/动态分发、闭包、递归数据枚举、借用检查、异常、async、宏、运算符重载、可变参数、任意内联汇编、完整 C 聚合 ABI、TLS 语法、包管理、格式化插值、顶层 `let`、`extern`/`export` 全局对象、局部类型声明、枚举显式标签值。

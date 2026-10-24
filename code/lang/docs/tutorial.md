# Dong 入门教程

本教程用一个小时带你写出第一批 Dong 模块，并在宿主机上从 C 调用它们。读完后再看[语言指南](guide.md)和[速查表](cheatsheet.md)。规范性的定义以[语言规格](../spec.md)为准。

Dong 是 DongOS 的系统编程语言：静态类型、无 GC、无隐式分配、无异常，编译成可读的 NASM x86-64 汇编。它的设计取向是“看得见的代价”——整数不会隐式转换，裸指针操作必须写在 `unsafe` 块里，结构体按声明顺序布局，所有检查失败都走一个显式的 panic 接口。

> 本页所有 `dong` 代码块都会被 `tools/dong_doctest.py` 实际编译，可以放心复制。

## 1. 准备

所有命令都在仓库的 `code/` 目录下执行。编译器 `dongc` 是纯 Python 实现（3.10+），只用标准库：

```powershell
python -m lang.dongc --help
```

如果还要把产物链接成可执行文件，需要 NASM 和一个 C 编译器（Linux 上的 GCC/Clang，Windows 上的 MinGW GCC）。仓库在 `.tools/nasm/` 下可能已有 NASM。

编辑器方面，`editors/vscode-dong/` 提供 VS Code 语法高亮，见[工具链手册](toolchain.md#vs-code-高亮)。

## 2. 第一个模块

新建目录 `hello/src/hello/`，写入 `math.dg`：

```dong
module hello.math;

// 求 1..=n 的和。
export("dong_sum_to") fn sum_to(n: u64) u64 {
    var total: u64 = 0;
    for i in 1..n + 1 {
        total += i;
    }
    return total;
}
```

几点说明：

- 每个文件以 `module 名称;` 开头。模块 `hello.math` 必须位于某个源码根下的 `hello/math.dg`。
- 函数写作 `fn 名称(参数: 类型, ...) 返回类型 { ... }`，返回类型不能省略；没有返回值写 `void`。
- `var` 声明可变变量，`let` 声明不可变绑定。
- `for i in a..b` 遍历左闭右开区间，`i` 的类型是 `usize`（与 `u64` 是同一类型）。
- `export("dong_sum_to")` 给函数一个固定的外部链接名，方便 C 调用。不写时，编译器按模块名生成唯一符号。

先只做检查，不写任何文件：

```powershell
python -m lang.dongc --check --root hello/src hello/src/hello/math.dg
```

没有输出、退出码为 0 就表示通过。然后生成汇编：

```powershell
python -m lang.dongc --root hello/src --emit-asm build/hello/math.asm hello/src/hello/math.dg
```

打开 `math.asm` 看看：它是带 `; line N` 注释的普通 NASM 源码，文件头记录了构建模式和它依赖的运行时符号 `__dong_panic`。

## 3. 从 C 调用 Dong

Dong 没有自己的运行时，检查失败（越界、溢出、除零等）时会调用目标提供的 `__dong_panic`。在宿主机上我们用 C 提供它：

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#if defined(_WIN32)
#define DONG_ABI __attribute__((sysv_abi))  /* Dong 函数固定使用 SysV 约定 */
#else
#define DONG_ABI
#endif

DONG_ABI uint64_t dong_sum_to(uint64_t n);

/* 检查失败时由 Dong 代码调用；不得返回。 */
DONG_ABI _Noreturn void __dong_panic(uint32_t kind, uint32_t line,
                                     const char *file, size_t file_len) {
    fprintf(stderr, "dong panic: kind=%u at %.*s:%u\n", kind, (int)file_len, file, line);
    exit(101);
}

int main(int argc, char **argv) {
    uint64_t n = argc > 1 ? strtoull(argv[1], NULL, 0) : 100;
    printf("sum_to(%llu) = %llu\n", (unsigned long long)n, (unsigned long long)dong_sum_to(n));
    return 0;
}
```

Linux：

```sh
nasm -f elf64 build/hello/math.asm -o build/hello/math.o
gcc hello/main.c build/hello/math.o -o build/hello/hello
./build/hello/hello
```

Windows（MinGW GCC；同一份汇编组装成 COFF）：

```powershell
.tools/nasm/nasm-3.02/nasm.exe -f win64 build/hello/math.asm -o build/hello/math.obj
gcc hello/main.c build/hello/math.obj -o build/hello/hello.exe
build/hello/hello.exe
```

输出 `sum_to(100) = 5050`。再试试 `hello 0xffffffffffffffff`：`n + 1` 在 debug 模式下溢出，程序打印 `dong panic: kind=2 at hello/math.dg:6` 并以 101 退出。kind 的取值：1 越界、2 溢出、3 除零、4 移位量非法、5 有符号除法溢出。

用 `--mode release` 编译时，`+ - *` 的溢出按位宽取模而不再 panic；越界、除零、移位量检查在两种模式下都保留。

## 4. 变量与类型

```dong
module tour.values;

const LIMIT: u32 = 1_000;          // 顶层常量必须写类型
var calls: u64 = 0;                // 顶层可变全局，必须有初始值

fn demo(x: u8) u64 {
    let wide: u64 = x as u64;      // 不同整数类型之间必须显式 as
    let mask = 0xff;               // 未定类型整数：无上下文时为 i64
    var flags: u32 = 0b1010;
    flags |= 1 << 4;               // 复合赋值
    let ok: bool = flags != 0 && LIMIT > 10;
    calls += 1;
    if ok {
        return wide + (mask as u64);
    }
    return 0;
}
```

- 整数类型：`u8 u16 u32 u64 i8 i16 i32 i64`，`usize`/`isize` 分别等于 `u64`/`i64`。
- **没有隐式整数转换**：`u32 + u64` 是编译错误（E0301）。`as` 转换截取低位或按源类型符号/零扩展。
- 条件必须是 `bool`；整数转布尔写 `x != 0`。
- 移位右侧必须是 `usize`；未定类型的字面量会自动适配。

## 5. 控制流

```dong
module tour.flow;

fn collatz_steps(start: u64) u64 {
    var n: u64 = start;
    var steps: u64 = 0;
    while n > 1 {
        if n % 2 == 0 {
            n = n / 2;
        } else {
            n = 3 * n + 1;
        }
        steps += 1;
    }
    return steps;
}

fn first_multiple(limit: u64, k: u64) u64 {
    var found: u64 = 0;
    for i in 1..limit {
        if i % k != 0 {
            continue;
        }
        found = i;
        break;
    }
    loop {
        // 无条件循环，必须用 break 退出
        break;
    }
    return found;
}
```

`if`、`while`、`for` 的条件不加括号，花括号不可省略。`if`/`match` 是语句而不是表达式，也没有“最后一个表达式即返回值”的写法——非 `void` 函数必须显式 `return`。

## 6. 数组与切片

```dong
module tour.slices;

fn sum(values: []const u64) u64 {
    var total: u64 = 0;
    for v in values {
        total += v;
    }
    return total;
}

fn demo() u64 {
    var numbers: [5]u64 = [1, 2, 3, 4, 5];
    numbers[0] = 10;                    // 索引总会检查边界
    let zeros: [4]u8 = [0; 4];          // 重复初始化 [值; 个数]
    let middle = numbers[1..4];         // 切片视图：元素 2,3,4
    let text: []const u8 = "你好";      // 字符串是 UTF-8 字节切片
    return sum(numbers[..]) + sum(middle) + text.len + zeros.len;
}
```

- `[N]T` 是定长数组，`[]T` / `[]const T` 是由指针和长度组成的切片。
- `a[lo..hi]` 创建视图，不复制数据；省略边界分别取 0 和长度。
- `.len` 取长度，`.ptr` 取数据指针。
- 切片不拥有存储，也没有生命周期检查：不要返回指向局部数组的切片。

## 7. 结构体、指针与 unsafe

```dong
module tour.shapes;

struct Rect {
    width: u64,
    height: u64,
}

fn area(r: *const Rect) u64 {
    unsafe {
        return (*r).width * (*r).height;
    }
}

fn grow(r: *Rect, by: u64) void {
    unsafe {
        (*r).width += by;
        (*r).height += by;
    }
}

fn demo() u64 {
    var box = Rect { width: 3, height: 4 };
    grow(&box, 1);
    return area(&box) + sizeof(Rect) + offsetof(Rect, height);
}
```

- 结构体字面量必须给出全部字段；字段按声明顺序布局，`sizeof`/`alignof`/`offsetof` 在编译期求值。
- 结构体和数组**不能按值**作为参数或返回值，用 `*const T` 传入、`*T` 传出（否则 E0601）。局部复制不受影响。
- `&x` 取地址；`*p` 解引用必须写在 `unsafe { }` 中。`unsafe` 是代码审查边界：编译器不检查空指针、悬垂指针和数据竞争。

### 方法

方法是普通函数的语法糖，接收者必须是 `*T` 或 `*const T`，且只能定义在 `T` 的声明模块里：

```dong
module tour.counter;

struct Counter { value: u64 }

fn (self: *Counter) add(amount: u64) void {
    unsafe {
        (*self).value += amount;
    }
}

fn (self: *const Counter) get() u64 {
    unsafe {
        return (*self).value;
    }
}

fn demo() u64 {
    var c = Counter { value: 0 };
    let p = &c;
    p.add(5);
    add(p, 2);           // 与 p.add(2) 等价
    let view: *const Counter = p;
    return view.get();
}
```

调用时不会自动取地址、解引用或改变只读性：先得到指针 `p = &c` 再调用 `p.add(...)`；接收者为 `*const Counter` 的方法要用 `*const Counter` 类型的值调用（`*T` 可以隐式转成 `*const T` 绑定）。

## 8. 枚举、match 与可选值

```dong
module tour.events;

enum Event { Idle, Key(u8), Tick(u64) }

fn describe(e: Event) u64 {
    match e {
        Event.Idle => { return 0; },
        Event.Key(code) => { return code as u64; },
        Event.Tick(ms) => { return ms; },
    }
    return 0;
}

fn find(values: []const u64, wanted: u64) ?usize {
    for i in 0..values.len {
        if values[i] == wanted {
            return i;          // 自动提升为 ?usize
        }
    }
    return null;
}

fn demo() u64 {
    let numbers: [3]u64 = [7, 8, 9];
    let index = find(numbers[..], 8) orelse 99;
    var bonus: u64 = 0;
    match find(numbers[..], 1) {
        null => { bonus = 1; },
        some(i) => { bonus = i; },
    }
    return describe(Event.Key(65)) + index + bonus;
}
```

- 枚举变体最多带一个载荷（整数、`bool`、裸指针或函数指针）。
- `match` 必须穷尽（否则 E0403），`_` 兜底只能放在最后。
- `?T` 是可选值；`x orelse 默认值` 解包，右侧也可以是 `return ...`、`break` 或 `continue`。

## 9. 错误处理与 defer

Dong 没有异常。可能失败的函数返回 `!T`，错误是模块里显式编号的 `error` 声明：

```dong
module tour.errors;

error Empty = 0x2000_0001;
error TooLarge = 0x2000_0002;

var depth: u64 = 0;

fn enter() void { depth += 1; }
fn leave() void { depth -= 1; }

fn parse_digit(c: u8) !u64 {
    if c < 48 || c > 57 {
        return error.TooLarge;
    }
    return (c - 48) as u64;
}

fn parse(text: []const u8) !u64 {
    enter();
    defer leave();               // 离开本块时执行，包括 try 提前返回
    if text.len == 0 {
        return error.Empty;
    }
    var value: u64 = 0;
    for c in text {
        value = value * 10 + try parse_digit(c);
    }
    return value;
}

fn demo() u64 {
    match parse("42") {
        ok(v) => { return v; },
        err(code) => { return code; },
    }
    return 0;
}
```

- `return error.Name;` 返回失败，`return value;` 返回成功。
- `try expr` 在失败时运行清理并把错误原样向上传播；只能用在返回 `!T` 的函数中。
- 不允许静默丢弃 `!T` 结果：要么 `try`，要么 `match`，要么赋值后处理。
- `defer` 在离开所在**词法块**时按注册的逆序执行；返回值先求出再执行清理。panic 不运行 `defer`。

## 10. 多模块与标准库

模块之间用 `import` 引用，默认一切私有，`pub` 公开。先写一个库模块 `geo/vec.dg`：

```dong
module geo.vec;

pub struct Vec2 { pub x: i64, pub y: i64 }

pub fn dot(a: *const Vec2, b: *const Vec2) i64 {
    unsafe {
        return (*a).x * (*b).x + (*a).y * (*b).y;
    }
}
```

再写使用它的模块，同时使用标准库 `core.fmt`：

```dong
module geo.app;

import geo.vec;
import core.fmt as fmt;

fn render(out: []u8) !usize {
    let a = vec.Vec2 { x: 3, y: 4 };
    let b = vec.Vec2 { x: 2, y: -1 };
    let d = vec.dot(&a, &b);
    return fmt.signed_decimal(d, out);
}
```

编译时，每个源码根都要用 `--root` 显式给出，标准库也不例外：

```powershell
python -m lang.dongc --check --root src --root lang/std src/geo/app.dg
```

- `import geo.vec;` 绑定名称 `vec`，`import core.fmt as fmt;` 绑定 `fmt`。
- 结构体字段要跨模块访问，必须写 `pub x: i64`。
- 标准库没有自动导入，也没有默认堆；全部 API 见[标准库参考](std/index.md)。

## 11. 下一步

- [语言指南](guide.md)：按主题讲解完整语法与语义（ABI、内建函数、unsafe 契约等）。
- [工具链手册](toolchain.md)：`dongc` 全部选项、优化与调试信息、格式化器、文档工具。
- [诊断参考](diagnostics.md)：每个错误码的原因与修正方法。
- [速查表](cheatsheet.md)：一页纸的语法汇总。

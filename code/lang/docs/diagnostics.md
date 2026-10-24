# Dong 诊断参考

`dongc` 的每条错误都带稳定代码，格式为：

```text
path:line:column: error[E0301]: message
    出错的源码行
    ^
```

行、列从 1 开始，列按 Unicode 码点计数（中文标识符算一列）。消息正文是英文，可能随版本细化；**代码是稳定的**，脚本和文档应只依赖代码。原生自举编译器使用单行形式 `path:line:column: E0301: ...`，代码含义相同。

退出码：`0` 成功，`1` 源码错误（下列任一代码），`2` I/O 或编译器内部错误。编译器只报告遇到的第一个错误。

在终端里查看某个代码的解释：

```powershell
python tools/dong_explain.py E0301
python -m lang.dongc --check app.dg 2>&1 | python tools/dong_explain.py -
```

本页每个示例都由 `tools/dong_doctest.py` 实际编译：错误示例必须产生标注的代码，修正示例必须通过检查。

## E0001：词法错误

源码无法切分成合法的 token：非法 UTF-8、未知字符、非法整数字面量、未终止的字符串或块注释、无效转义。

常见消息：`invalid character`、`invalid integer literal`、`newline in string literal`、`unterminated block comment`、`invalid string escape`、`source is not valid UTF-8`。

```dong error=E0001 line=4
module demo.lex;

fn bad() u64 {
    return 0x1G;
}
```

十六进制数字只能是 `0-9a-fA-F`；数字分隔符 `_` 只能出现在两个数字之间。Dong 没有浮点和字符字面量，ASCII 字符直接写整数（`'A'` 写作 `65` 或 `0x41`）。

```dong
module demo.lex;

fn good() u64 {
    return 0x1F + 0b1010_0101 + 1_000;
}
```

## E0101：语法错误

token 序列不符合语法。消息通常写明期望的 token：`expected ';', found '}'`。

常见原因：

- 漏写分号。Dong 的简单语句和顶层 `const`/`var`/`type`/`error`/`import` 都必须以 `;` 结尾。
- 链式比较 `a < b < c`。
- 把 `break`/`continue` 写在循环之外。
- 独立表达式语句不是调用（如单独一行 `x + 1;`）。
- 修饰符重复或用错位置：`packed`/`align` 只能修饰结构体，`export`/`extern`/`unsafe` 只能修饰函数。
- `let`/`const` 缺少初始化器。

```dong error=E0101 line=5
module demo.syntax;

fn bad() u64 {
    let x: u64 = 1
    return x;
}
```

```dong
module demo.syntax;

fn good() u64 {
    let x: u64 = 1;
    return x;
}
```

## E0201：名称错误

名称未定义、重复定义或不可见。

常见消息：`undefined name`、`undefined function`、`duplicate declaration`、`duplicate binding`、`type T has no field`、`field T.x is private to module m`、`public signature exposes private type`、`method is private to its declaring module`。

```dong error=E0201 line=4
module demo.names;

fn bad() u64 {
    return count;
}
```

跨模块访问要注意：结构体字段默认私有，需要写 `pub field: T`；公开函数的签名中不能出现私有类型。

```dong
module demo.names;

pub struct Point { pub x: i64, pub y: i64 }

pub fn manhattan(p: *const Point) i64 {
    unsafe {
        return (*p).x + (*p).y;
    }
}
```

## E0202：模块错误

模块找不到、在多个源码根中重复、路径与 `module` 声明不一致或存在循环导入。

常见消息：`module 'a.b' not found in the specified source roots`、`module imports require an explicit --root`、`entry module name does not match its source-root-relative path`、`cyclic module import: a -> b -> a`。

模块 `a.b` 只会从 `--root` 指定目录下的 `a/b.dg` 加载；编译器不搜索当前目录。

```dong error=E0202 line=3
module demo.modules;

import demo.missing;

fn f() u64 { return 0; }
```

修正方法：确认文件位于 `<root>/demo/missing.dg`，且该文件第一行是 `module demo.missing;`，再用 `--root <root>` 编译。使用标准库时加 `--root lang/std`：

```dong
module demo.modules;

import core.slice as slice;

fn same(a: []const u8, b: []const u8) bool {
    return slice.equal(a, b);
}
```

## E0301：类型错误

类型不匹配或无法推导。这是最常见的错误。

常见原因：

- 不同宽度或符号的整数混用。Dong **没有隐式整数转换**，`u32 + u64` 必须先 `as u64`（`usize` 与 `u64` 是同一类型）。
- 条件不是 `bool`：`if count { ... }` 应写 `if count != 0 { ... }`。
- `let x = null;` 或空数组无法推导类型。
- 顶层 `const`/`var` 没写类型。
- 丢弃了 `!T` 调用结果（必须 `try`、`match` 或赋值给绑定）。
- 移位右侧不是 `usize`。

```dong error=E0301 line=5
module demo.types;

fn widen(small: u32) u64 {
    let big: u64 = 10;
    return big + small;
}
```

```dong
module demo.types;

fn widen(small: u32) u64 {
    let big: u64 = 10;
    return big + (small as u64);
}
```

## E0302：布局与常量错误

非法的类型布局、常量求值溢出或循环依赖。

常见消息：`array length must be positive`、`empty structures are not allowed`、`alignment must be a power of two between 1 and 4096`、`packed and align cannot be combined`、`constant operation overflows u8`、`division by zero in constant operand`、`cyclic constant, alias or layout dependency`、`void/noreturn cannot be used as a pointer, array or slice element type`。

```dong error=E0302 line=3
module demo.layout;

const SMALL: u8 = 200 + 100;
```

常量在所有构建模式下都会检查溢出；需要按位宽取模时使用 `wrapping_add`：

```dong
module demo.layout;

const SMALL: u8 = wrapping_add(200 as u8, 100);
```

## E0401：可能未初始化

读取了某条路径上尚未赋值的变量。确定初始化按所有控制流路径求交集，循环可能执行零次，所以不能仅靠循环体中的赋值证明初始化。

```dong error=E0401 line=8
module demo.init;

fn pick(flag: bool) u64 {
    var value: u64;
    if flag {
        value = 1;
    }
    return value;
}
```

在每条路径上赋值，或直接给初值：

```dong
module demo.init;

fn pick(flag: bool) u64 {
    var value: u64 = 0;
    if flag {
        value = 1;
    }
    return value;
}
```

## E0402：赋值或返回路径错误

给不可变位置赋值，或非 `void` 函数存在没有 `return` 的路径；`noreturn` 函数中出现 `return`。

常见消息：`cannot assign an immutable place`、`cannot assign a compile-time constant`、`non-void function has a path without an explicit return`、`noreturn functions cannot contain return`。

```dong error=E0402 line=5
module demo.assign;

fn bump() u64 {
    let total: u64 = 1;
    total += 1;
    return total;
}
```

`let` 绑定不可重新赋值，其聚合字段也不可写；需要修改时用 `var`。Dong 没有隐式尾表达式返回，所有能正常结束的非 `void` 函数都要显式 `return`：

```dong
module demo.assign;

fn sign(x: i64) i64 {
    if x < 0 {
        return -1;
    } else if x > 0 {
        return 1;
    }
    return 0;
}
```

## E0403：match 错误

`match` 不穷尽、有重复分支，或分支在 `_` 之后不可达。

```dong error=E0403 line=6
module demo.matching;

enum Light { Red, Yellow, Green }

fn wait(light: Light) u64 {
    match light {
        Light.Red => { return 30; },
        Light.Green => { return 0; },
    }
    return 0;
}
```

列出全部变体，或在最后加 `_` 兜底：

```dong
module demo.matching;

enum Light { Red, Yellow, Green }

fn wait(light: Light) u64 {
    match light {
        Light.Red => { return 30; },
        Light.Yellow => { return 5; },
        Light.Green => { return 0; },
    }
    return 0;
}
```

## E0501：unsafe 与 defer/try 上下文

需要 `unsafe` 块的操作写在了块外，或 `defer`/`try` 用在不允许的位置。

需要显式 `unsafe { ... }` 的操作：解引用/索引/算术裸指针、整数与指针互转、去掉 `const`、`slice_from_raw_parts`、调用 `unsafe fn`、`extern` 函数或任意函数指针、`asm`、volatile/原子/非对齐内建。即使位于 `unsafe fn` 内也一样要写块。

其他常见消息：`try requires an error-returning function`、`try is not allowed in defer`、`control transfer is not allowed in defer`、`nested defer is not allowed`。

```dong error=E0501 line=4
module demo.unsafety;

fn read(p: *const u64) u64 {
    return *p;
}
```

```dong
module demo.unsafety;

fn read(p: *const u64) u64 {
    unsafe {
        return *p;
    }
}
```

## E0601：不支持的特性或超出限制

源码合法，但使用了当前编译器不支持的类型、ABI 或特性，或函数最坏栈帧超过 4096 字节，或静态初始化数据超过 16 MiB。

常见原因：

- 结构体或数组**按值**作为函数参数/返回值。改用 `*const T` 输入、`*T` 输出。
- `extern` 函数使用切片、可选值、错误结果等双字值。
- 局部大数组（如 `[8192]u8`）导致栈帧超过 4096 字节。改用全局 `var` 或调用方提供的存储。
- 顶层 `let`、枚举显式标签值、带多个载荷的变体、非白名单 `asm` 指令。

```dong error=E0601 line=5
module demo.limits;

struct Pair { a: u64, b: u64 }

fn make() Pair {
    return Pair { a: 1, b: 2 };
}
```

```dong
module demo.limits;

struct Pair { a: u64, b: u64 }

fn make(out: *Pair) void {
    unsafe {
        *out = Pair { a: 1, b: 2 };
    }
}
```
## E0602：错误码或链接名冲突

两个 `error` 声明在最终模块图中使用了相同编号，或 `export`/`extern` 链接名重复、不是 ASCII 标识符、与编译器保留符号冲突。

```dong error=E0602 line=4
module demo.links;

error Busy = 1;
error Timeout = 1;
```

错误编号在整个程序中必须唯一。标准库的编号集中在 `core.errors`，自己的模块应选择不重叠的范围：

```dong
module demo.links;

error Busy = 0x1000_0001;
error Timeout = 0x1000_0002;
```

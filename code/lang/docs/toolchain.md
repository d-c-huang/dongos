# Dong 工具链手册

本页汇总 Dong 的全部命令行工具。除特别说明外，命令都在仓库 `code/` 目录下执行，只需要 Python 3.10+。

| 工具 | 用途 |
| --- | --- |
| `python -m lang.dongc` | 编译器：检查、生成 NASM 汇编、布局/产物清单、SSA 优化、DWARF 调试信息 |
| `tools/dongfmt.py` | 保留 token 与注释的格式化器 |
| `tools/gen_offsets.py` | 从布局清单生成 NASM `struc` |
| `tools/dongdoc.py` | 从源码注释生成 API 参考（Markdown） |
| `tools/dong_explain.py` | 解释诊断代码 |
| `tools/dong_doctest.py` | 编译 Markdown 文档中的 Dong 示例 |
| `tools/bench_dong.py` | 与手写 NASM 对照的性能基准 |
| `editors/vscode-dong/` | VS Code 语法高亮与离线 VSIX 打包 |
| `tools/build_native_frontend.py` | 构建 Dong 自举的原生编译器（POSIX 宿主） |

## dongc 编译器

```text
python -m lang.dongc [选项] SOURCE.dg
```

必须选择 `--check`，或至少一个产物选项（`--emit-asm`/`--emit-layout`/`--emit-ir`）。

| 选项 | 说明 |
| --- | --- |
| `--check` | 词法、语法、名称、类型、确定初始化、返回路径、ABI 和帧大小检查；不写任何文件。不能与产物选项同用 |
| `--root DIR` | 源码根，可重复。模块 `a.b` 只从各根下的 `a/b.dg` 加载。有 `import` 时必须提供；标准库用 `--root lang/std` |
| `--emit-asm FILE` | 输出 NASM（Intel 语法、`default rel`、ELF64 节）源码 |
| `--emit-manifest FILE` | 输出 JSON 产物清单：目标、模式、模块、导出符号、运行时依赖 |
| `--emit-layout FILE` | 输出 JSON 布局清单：每个结构体/枚举的大小、对齐与字段偏移 |
| `--emit-ir FILE` | 输出 SSA 优化前后 IR、寄存器分配和每函数回退原因；需要 `-O 1` |
| `--mode debug\|release` | 默认 `debug`：整数 `+ - *` 溢出 panic；`release` 按位宽取模。边界/除零/移位检查两种模式都有 |
| `-O 0\|1` | 默认 `0`。`-O 1` 对标量函数启用 SSA 后端（常量折叠、死代码删除、内联、寄存器分配等），不支持的函数自动走原后端 |
| `-g`, `--debug-info` | 生成 DWARF4 行表、类型、变量和栈展开信息 |
| `--function-sections` | 每个函数单独成节，便于链接器回收；不能与 `-g` 同用 |
| `--target` | 目前只有 `x86_64-dongos-elf` |

退出码：`0` 成功；`1` 源码错误；`2` I/O 或内部错误。所有产物先写临时文件，全部成功后才逐个原子替换；中途失败会回滚，不会留下貌似成功的半成品。输出路径必须互不相同，且不能覆盖任何已加载的源码。

常用组合：

```powershell
# 只检查（含标准库）
python -m lang.dongc --check --root src --root lang/std src/app/main.dg

# 生成汇编 + 产物清单 + 布局
python -m lang.dongc --root src --emit-asm build/main.asm --emit-manifest build/main.json --emit-layout build/layout.json src/app/main.dg

# release + 优化，并查看优化记录
python -m lang.dongc --mode release -O 1 --root src --emit-asm build/main.asm --emit-ir build/main.ir.json src/app/main.dg

# 源码级调试信息
python -m lang.dongc -g --root src --emit-asm build/main-debug.asm src/app/main.dg
```

Python API：

```python
from lang.dongc import compile_file, compile_source, CompileError

result = compile_file("src/app/main.dg", roots=["src", "lang/std"], mode="debug")
print(result.assembly)              # NASM 文本
print(result.manifest())            # 产物清单 dict
print(result.layout_manifest)       # 布局清单 dict

try:
    compile_source("module m;\nfn f() u64 { return x; }\n", "m.dg")
except CompileError as error:
    print(error.code, error.format("m.dg", ""))
```

### 汇编与链接

`dongc` 只生成汇编，汇编和链接由构建系统调用：

```sh
nasm -f elf64 build/main.asm -o build/main.o          # DongOS / Linux
nasm -f win64 build/main.asm -o build/main.obj        # Windows 宿主测试（COFF）
```

生成的代码依赖目标提供 `__dong_panic`（见[语言指南第 16 节](guide.md#16-运行时接口与限制)）；产物清单的 `runtime_symbols` 字段会列出它。在 Windows 上从 C 调用 Dong 函数时，C 侧原型要加 `__attribute__((sysv_abi))`。完整示例见[入门教程第 3 节](tutorial.md#3-从-c-调用-dong)。

### 调试

`-g` 生成的 DWARF 使用最终后端的真实栈位置；`-g` 与 `-O 1` 同用时会保留可调试的直接后端。汇编时**不要**再给 NASM 加 `-g`，否则会混入汇编源码级调试信息。

- 使用 `--root` 时模块路径是源码根相对路径，在 GDB 中用 `directory <源码根>` 定位源文件。
- GDB 以 C 兼容表达式查看 Dong 值（没有专门的 Dong 语言插件）。
- Windows COFF 不支持所需的 SECREL 重定位，链接前用 `lang.dongc.debug_info.adapt_coff_debug` 修正调试节；它不改变 `.text`。

## 布局清单与 gen_offsets

Dong 的类型声明是结构体布局的唯一来源。汇编代码需要偏移时，从布局清单生成 NASM 定义，而不是手写偏移表：

```powershell
python -m lang.dongc --root lang/examples --emit-layout build/dong_layout.json lang/examples/boot_probe.dg
python tools/gen_offsets.py build/dong_layout.json build/bootinfo_layout.inc --type boot.abi.BootInfo
```

`--type` 接受短名或完整名（`模块.类型`），`--name` 可覆盖生成的 NASM 结构名。名称必须是 ASCII 标识符。

## dongfmt 格式化器

```powershell
python tools/dongfmt.py path/to/file.dg                 # 结果写到 stdout
python tools/dongfmt.py --check a.dg b.dg               # 只检查；0 已格式化，1 需要格式化，2 错误
python tools/dongfmt.py --write a.dg b.dg               # 原地写入
```

格式器只改动 token 之间的空白：四空格缩进、注释独占一行、生成的空白用 LF。token 拼写、字符串原始字节、注释内容和位置都保持不变，每次都会核对 AST 未变。它只做语法验证，不检查类型或导入。详见[格式器文档](../../docs/dongfmt.md)。

## dongdoc API 文档生成

`tools/dongdoc.py` 读取源码根下的所有模块，为每个模块生成一页 Markdown 参考，再生成索引页：

```powershell
python tools/dongdoc.py --root lang/std --output lang/docs/std            # 生成/更新
python tools/dongdoc.py --root lang/std --output lang/docs/std --check    # 只检查是否过期；过期退出 1
```

写文档注释的约定：

- 文件开头连续的 `//` 注释是**模块说明**；第一句（若写成 `core.fmt — 说明。` 的形式，取破折号后的部分）进入索引表。
- 紧贴在 `pub` 声明上方、中间没有空行的 `//` 注释是该声明的说明；第一句进入目录表的摘要列。
- 只收录 `pub` 声明：错误码、常量、全局变量、类型别名、结构体、枚举、函数和方法。函数只显示签名，结构体/枚举显示完整定义。
- `unsafe` 函数（含所有 `extern` 声明）会被标记，提醒调用者阅读前提条件。
- 生成结果是确定的（固定顺序、LF 换行），可以提交到仓库并用 `--check` 在 CI 中防止过期。

```dong ignore
// geo.vec — 二维整数向量。
// 所有运算都不分配内存。

module geo.vec;

pub struct Vec2 { pub x: i64, pub y: i64 }

// 点积。debug 模式下乘法溢出会 panic。
pub fn dot(a: *const Vec2, b: *const Vec2) i64 { ... }
```

## dong_explain 诊断解释

```powershell
python tools/dong_explain.py E0301          # 解释一个代码
python tools/dong_explain.py --list         # 列出所有代码
python -m lang.dongc --check app.dg 2>&1 | python tools/dong_explain.py -
```

最后一种用法先原样输出编译器诊断，再附上其中每个代码的解释（同时识别 `dongc` 的 `error[E0301]` 和原生编译器的 `E0301:` 格式）。解释文本来自[诊断参考](diagnostics.md)，两者不会不同步。

## dong_doctest 文档示例检查

`tools/dong_doctest.py` 把 Markdown 中的 `dong` 代码块当作完整模块编译，保证文档示例始终可用：

```powershell
python tools/dong_doctest.py lang/docs                 # 递归检查目录下所有 .md
python tools/dong_doctest.py -v lang/docs/guide.md     # 同时列出通过的示例
```

代码块信息串的写法：

| 信息串 | 含义 |
| --- | --- |
| `dong` | 必须编译通过 |
| `dong error=E0301` | 必须以该代码失败 |
| `dong error=E0301 line=4` | 且错误位于块内第 4 行 |
| `dong release` | 以 release 模式编译 |
| `dong ignore` | 只高亮，不编译（片段、伪代码） |

同一文档中编译成功的块共享一个临时源码根，所以后面的块可以 `import` 前面块定义的模块；`lang/std` 始终可用。工具不会写入仓库。退出码：0 全部通过，1 有失败，2 用法或读取错误。

## 性能基准

```powershell
python tools/bench_dong.py --measurement-context diagnostic --check
```

固定的五个内核与手写 NASM 对照，需要 NASM 与 C 编译器。详见[基准说明](../benchmarks/README.md)。

## VS Code 高亮

`editors/vscode-dong/` 提供 `.dg` 文件关联、TextMate 语法高亮、注释切换和括号配对（没有语言服务器）。离线打包 VSIX：

```powershell
python editors/vscode-dong/package.py --output build/editor/dong-language-0.1.0.vsix
```

然后在 VS Code 中“从 VSIX 安装”。Markdown 中的 ` ```dong ` 代码块在安装扩展后也会高亮。

## 原生（自举）编译器

Dong 编写的编译器位于 `lang/bootstrap/`，由 `tools/build_native_frontend.py` 用现有编译器构建为 POSIX x86-64 可执行文件：

```sh
python3 tools/build_native_frontend.py --mode debug --output build/native/dong-native
build/native/dong-native --check --root lang lang/bootstrap/artifact_compare.dg
build/native/dong-native --emit-asm build/artifact.asm --mode debug --root lang lang/bootstrap/artifact_compare.dg
```

它的诊断为单行 `path:line:column: E0301: ...`，退出码约定与 `dongc` 相同。源码目录、内存预算等限制见[原生驱动说明](../host/README.md)。

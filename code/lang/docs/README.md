# Dong 语言文档

Dong 是 DongOS 的系统编程语言：静态类型、无 GC、无隐式分配、无异常，编译为可读的 NASM x86-64 汇编。

| 文档 | 适合 |
| --- | --- |
| [入门教程](tutorial.md) | 第一次接触 Dong：写模块、编译、从 C 调用、错误处理、多模块 |
| [语言指南](guide.md) | 按主题系统学习：类型、布局、指针与 unsafe、ABI、硬件内建、限制 |
| [速查表](cheatsheet.md) | 一页纸语法、内建、命令和诊断代码 |
| [工具链手册](toolchain.md) | `dongc` 全部选项、调试、格式化、文档与诊断工具、VS Code、原生编译器 |
| [诊断参考](diagnostics.md) | 每个错误码的原因、错误示例和修正方法 |
| [标准库参考](std/index.md) | `core.*`、`sync.spin`、`arch.x86_64` 的公开 API（由源码注释生成） |

规范性定义见[语言规格](../spec.md)；实现范围与实测证据见[语言线 README](../README.md)。

## 文档维护

本目录的示例和参考页都由工具校验，修改后请运行：

```powershell
python tools/dong_doctest.py lang/docs                                  # 编译文档中的全部 dong 示例
python tools/dongdoc.py --root lang/std --output lang/docs/std --check  # 标准库参考是否与源码注释一致
python -m unittest lang.tests.test_doc_tools -v                         # 工具自身的测试（也会执行上面两项）
```

- 写示例：` ```dong ` 代码块必须是带 `module` 声明的完整模块；演示错误用 ` ```dong error=E0301 `；片段用 ` ```dong ignore `。
- 改了标准库的 `pub` 声明或注释后，运行 `python tools/dongdoc.py --root lang/std --output lang/docs/std` 重新生成 `std/`，不要手工编辑生成页。
- 新增诊断代码时，在 [diagnostics.md](diagnostics.md) 中加一个 `## E####：标题` 小节并附错误/修正示例，`tools/dong_explain.py` 会自动收录。

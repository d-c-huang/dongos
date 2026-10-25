# L3ELFMATRIX1 — 纯 ELF 完整语言矩阵

状态：实现已完成，提交独立完整复验；尚未验收。

复用 `test_g5_full_native` 的完整 51 项、27 组要求及原有独立 C 行为断言。目标由实际 Dong frontend/lower/backend 产生汇编，再由同一源码构建对象中的生产 native_assembler 产生 ELF，生产内核 ELF 校验器检查产物。编译器种子与 Python seed 对照仍使用 NASM；被验目标无 NASM 回退。

Windows 观察适配器将 ELF 装载到声明的固定地址，原有 C 观察器通过仅含绝对符号的 COFF 表调用目标函数/访问目标全局。外部 C 运行时通过明确追加的 r11 尾调用桥接入，只修补桥的独立数据槽；原 Dong 汇编正文不改写，原 ELF 目标代码及数据按程序头复制，代码 RX、数据 RW。此适配器是宿主测试桥，不代表新增 OS 动态链接能力。

预检日志：`code/build/l3-elf-matrix-preflight.log`。实际完整结果、失败及独立正式复验待填；不提前关闭 L3。

## 预检过程（保留）

- R1 `run-01ad0523a487`：运行时桥追加在 GNU-stack 元数据后，生产 assembler 正确以 syntax/detail58 拒绝；停止该预检，未将诊断成功计为矩阵成功。
- 单独适配器探针暴露本机旧 ld 不支持 `--disable-dynamicbase` 及初始线程栈占用固定地址。宿主 PE 显式核对 ImageBase 并清除动态基址位；沿用已有 mapper 的工作线程等待初始线程退出方式，不修改 ELF 绝对指针。
- 原始 G5 audit 真正 frontend 产物经 native_assembler、绝对符号桥及原 C 观察器实际执行通过，输出 audit=true / abi_words=20。
- 严格 GCC 警告发现装载器 C 语句缩进问题，修正为显式块；R2构建中停止，未计通过。
- R3 `run-44e7ae0502a8` 正在执行。生产源码没有修改。
- 原 opcode 用例仅把观察文件 `.obj` 改为 `.native.elf`，独立 AST 对照其余代码/断言完全相同。其它50项沿用原测试方法，原27组要求不变。

## 提交独立复验

R3 共运行49项，48项通过；旧错误全局地址负控使用 `[rel symbol+8]`，在执行前被内建汇编器拒绝。failfast 保留该失败及尚未运行的末两项，不计完整通过。

最终版本只在私有错误编译器源码中把该负控写法替换为 `lea rax,[rel symbol]` 后接 `lea rax,[rax+8]`，保持相同错误地址及标志位。原生产编译器不改；不修改被验汇编来绕过检查。已核对源码替换唯一性；诊断探针 `run-2e726a606319` 以等价指令生成真实ELF执行，原C观察器准确返回2 / wrong-global-address。最终全矩阵须由协调器新冻结副本从源码构建、全部实际执行通过后方可验收。

正式复验命令：`python -B -X utf8 -m unittest lang.tests.test_l3_elf_full_matrix -v`。独立审查需核对51项/27组、零skip、source_stable、纯ELF产物和执行回执、原六类错误源码及seed回退负控。正式作业和最新状态以协调器为准。

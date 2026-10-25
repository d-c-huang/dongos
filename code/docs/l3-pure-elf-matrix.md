# L3 纯 ELF 完整语言矩阵完成回执

2026-10-24 L3完成：L3ELFMATRIX1 已独立验收并集成本地主线 main 工作树（integrated rev6）。正式作业 ed37c79515f94c87a488e538ea6ba20d：51项/27组全部通过、零skip，963.657秒，source_stable及进程停止/退出均确认。148份目标ELF、166次实际观察运行和六类错误源码通过独立产物审计；157主目录源码与复验一致，G6的456源仍逐字绑定已验收的2,062,984字节编译器。因此L3/L3A剩余纯ELF矩阵门关闭，整体状态更新为complete。

## 实现与验证

- `lang/tests/test_l3_elf_full_matrix.py` 复用完整 G5 的51项、27组要求及两种检查模式。原行为断言不变；指令字节检查改读实际 ELF，已作 AST 等价核对。
- `lang/tests/l3_elf_observer.py` 将实际 Dong frontend/lower/backend 的输出交给生产 `native_assembler`，由生产内核 ELF 校验器检查，再按声明地址装载。C 观察器通过只含绝对符号的 COFF 表访问原函数和全局量，目标指令没有交给 NASM。
- 库式夹具添加测试入口及显式外部运行时槽桥；原汇编正文保持，代码 RX、数据 RW。Windows 初始线程退出后再占用 ELF 固定地址，宿主 PE 基址另行核验。客体入口、自编译和持久化由已有同源 G6 回执证明。
- 独立冻结复验51/51通过，零跳过；覆盖整数/聚合/静态指针、模块、标签与错误处理、方法、循环/match/defer、SysV/Win64、对齐、内存/四线程原子竞争、诊断、panic和真实负控。
- 独立 stdlib 审计核对259份输入、148份ELF、166次观察执行（89种不同ELF哈希）、ELF段权限、嵌入字节、绝对符号地址、NASM目标排除、进程与执行绑定。bad-address、bad-kind、bad-static-address、bad-store、bad-tag、bad-xmm均有真实执行证据，seed回退伪成功被拒绝。

## 审查、集成与当前状态

协调器按 submitted rev4 → accepted rev5 → integrated rev6 登记。两份测试代码、交付及提交快照的5份SHA256全部匹配独立fingerprint，文件真实位于 `main` 主目录。157份测试/生产依赖与冻结副本一致；当前主目录及正式副本的456份G6输入与G6ENC1回执一致。本轮没有修改生产编译器，因此沿用同源当前G4/G6，不把不同版本的历史成功混用。

L3与L3A现为 **complete**：G1–G5的既有语言/语义门、当前纯ELF完整矩阵及同源G4/G6闭环均具备。编译器产物2,062,984字节，源码494,247字节，原2MiB ELF / 512KiB源码 / 56MiB arena / 64KiB栈预算保持。其它系统阶段和真机门不在本次完成范围内。

## 失败历史与证据

R1桥位于元数据尾部后而被正确拒绝；R2在修正宿主适配问题时停止。R3运行49项、48项通过，原错误全局地址负控的 `[rel symbol+8]` 被汇编器拒绝，未冒充执行负控通过。最终仅在私有错误编译器源码中改为两个等价LEA，保留相同错误地址和标志位，原C观察器实际捕获错误；正式全矩阵随后通过。原记录和档案保持。

- [永久完成证据（含完整矩阵回执、独立审计及审计程序）](../../coordination/dongos_works/reviews/2026-10-24-l3-closure.json)
- [提交阶段记录（历史快照）](../../coordination/dongos_works/codex-works/reviews/2026-10-24-L3-ELF-matrix.md)
- [同源当前G6回执](../../coordination/dongos_works/codex-works/reviews/2026-10-24-G6-encoding.md)

复验入口：`python -B -X utf8 -m unittest lang.tests.test_l3_elf_full_matrix -v`（Windows、NASM、GCC必需；缺失即失败，不skip）。本次集成指本地主线工作树，未提交或推送。

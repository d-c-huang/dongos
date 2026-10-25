# L3ELFMATRIX1 — L3完整语言矩阵纯ELF实际执行与独立验收

负责人：codex。状态：待领取。

复用G5 51项27组完整语言/ABI/诊断/负控矩阵，原生Dong前端后端生成目标汇编交给生产native_assembler生成ELF，宿主观察器只负责装载/外部运行时适配，不能用NASM生成目标指令或静默回退。保留两模式、真实负控、来源哈希、零skip与完整覆盖判定；独立冻结复验后验收集成。只改测试和证据，若发现生产缺陷另立修复卡；不上传、不关机。

## 可修改文件

- `lang/tests/test_l3_elf_full_matrix.py`
- `lang/tests/l3_elf_observer.py`
- `codex-works/deliveries/L3ELFMATRIX1.md`
- `codex-works/reviews/2026-10-24-L3-ELF-matrix.md`
- `codex-works/reviews/2026-10-24-L3-ELF-matrix.json`

## 定向验收

- `module:lang.tests.test_l3_elf_full_matrix`

交付：`codex-works/deliveries/L3ELFMATRIX1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

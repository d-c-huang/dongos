# P8SYMBOL1 — 启动观察器兼容合法NASM宏私有局部符号

负责人：codex。状态：待领取。

P8STAGE1完整成品的真实ELF含跨对象同名..@34.recorded等NASM宏私有STB_LOCAL/STT_NOTYPE标签，ELF合法但tests/run_cpu_qemu.read_elf_symbols把所有重复名字当歧义而拒绝，当前normal VM在读取符号时退出，未能验收。只在CPU观察器忽略NASM ..@ 前缀且binding=STB_LOCAL的私有实现标签；同名global/weak和普通有意义local歧义仍拒绝，不放宽required CPU symbols/结构边界/defined/UTF8等检查，不改构建已哈希tools/elf_symbols.py或生产程序。用真实NASM两目标链接ELF及精确host负例覆盖private重复可用、global重复/普通local重复/缺required/截断仍拒绝，零skip/源稳定。补充适配独立验收后P8STAGE1再进行实际完整VM及最终验收。

## 可修改文件

- `tests/run_cpu_qemu.py`
- `tests/test_cpu_elf_symbols.py`
- `codex-works/deliveries/P8SYMBOL1.md`

## 定向验收

- `module:tests.test_cpu_elf_symbols`

交付：`codex-works/deliveries/P8SYMBOL1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

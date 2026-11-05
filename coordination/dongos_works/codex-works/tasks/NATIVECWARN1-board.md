# NATIVECWARN1 — 修复帧缓冲C独立oracle的误导缩进编译错误

负责人：codex。状态：待领取。

P5主线集成回归暴露既有framebuffer_ledger_probe.c:40单行if-return后CK触发本机GCC -Werror=misleading-indentation。仅拆行/显式花括号，不改变独立walker/断言/场景，不禁用警告。不修改DMA实现。非作者审查差异、完整帧缓冲native两模式与坏体复验稳定零skip后验收。原失败run-448b1b198215/link.json保留。无OS/VM/Git。

## 可修改文件

- `tests/framebuffer_ledger_probe.c`
- `codex-works/deliveries/NATIVECWARN1.md`

## 定向验收

- `module:tests.test_framebuffer_ledger`

交付：`codex-works/deliveries/NATIVECWARN1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

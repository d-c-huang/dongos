# G6ENC1 — 扩展纯ELF编码后的当前编译器固定点及G6复验

负责人：codex。状态：待领取。

L3ENC1源码扩展后，在独立冻结副本fresh运行compiler_job_preparation，核对512KiB源码/2MiB ELF/56MiB arena/64KiB栈预算，实际同盘两启并独立raw/FAT/retirement审计。保留所有失败，不把旧G6用于当前源码。结果留档，正式零skip测试后才验收集成；不上传关机。

## 可修改文件

- `codex-works/reviews/2026-10-24-G6-encoding.md`
- `codex-works/reviews/2026-10-24-G6-encoding.json`
- `codex-works/deliveries/G6ENC1.md`

## 定向验收

- `module:tests.test_compiler_guest_runner`

交付：`codex-works/deliveries/G6ENC1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

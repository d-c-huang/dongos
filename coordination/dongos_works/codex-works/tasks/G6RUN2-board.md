# G6RUN2 — [L3] 当前主线扩大编译器的全新G6构建及同盘双启独立验收

负责人：codex。状态：待领取。

用户改优先先完成L3。G6DOC1已证明旧PREP1归档有效但当前12内核/构建输入变化，不沿用旧镜像。先通过协调器冻结当前源码，在隔离workspace实际运行既有test_compiler_job_preparation获得fresh release完整固定点及production runtime5/compiler_job镜像，逐项load_inputs/verify_frozen、ELF/源/预算与FAT核对。随后root协调者按用户授权执行既有run_compiler_job_qemu原流程，真实单BSP客体编译、FLUSH、同盘双启、物理隔离/guard/无能力以及128页退休闭合，原始归档和独立raw审查齐全才可验收。编译器56MiB/64KiB/2MiB预算、原guest期限不放宽，失败保留；不声称更广纯ELF已完成。实现者仅记录证据/文档，不擅改生产源；若定位源缺陷另行明确返修范围。独立检查通过并实际文件集成后登记；不提交/推送/关机。

## 可修改文件

- `codex-works/reviews/2026-10-23-G6-current-run.md`
- `codex-works/reviews/2026-10-23-G6-current-run.json`
- `codex-works/deliveries/G6RUN2.md`

## 定向验收

- `module:tests.test_compiler_guest_runner`

交付：`codex-works/deliveries/G6RUN2.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

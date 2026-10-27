# P8RUNTIME1 — 恢复真机连续桌面启动并捕获实际运行失败

负责人：codex。状态：待领取。

用户要求继续完成真实桌面启动，避免多次无谓逐阶段停机。最新真机FIRST USER检查通过，F4发生于首个系统调用之前。审计并实际验证F4后EOI、锁、连续用户返回、首系统调用与服务启动；基于证据修复具体缺陷，不用虚构故障。允许限定文件中的必要运行修复和无条件成功停车移除/失败时可见可信状态。正常成功路径必须持续到桌面，不人为等待照片停住；保持正常CPU拓扑、存储权限、原时限和normal17服务。新工具必须严格绑定原normalbuild/source/actualcommands且声明诊断差异，不能冒充normal验证。测试实际实现+有效错误体、0skip/stable及独立复验，root负责真实8CPU单USB端到端VM/代码帧与存储无改验证。若需额外文件先扩任务范围。完成实审和验收后准备原SanDiskH备份/写入/flush/readback/FAT rb，设备插入需重新确认或实证。独立复验+真实文件集成后更新进度。不得仅靠新增逐阶段stop任务充当启动修复。

## 可修改文件

- `kernel/sched/user_bridge.dg`
- `kernel/sched/user_entry.asm`
- `kernel/sched/user_boot.asm`
- `kernel/sched/user_boot.dg`
- `kernel/entry.asm`
- `kernel/boot/user_runtime_status.dg`
- `tools/build_user_runtime.py`
- `tests/test_user_runtime.py`
- `tests/user_runtime_probe.c`
- `docs/hardware-user-runtime.md`
- `codex-works/deliveries/P8RUNTIME1.md`

## 定向验收

- `module:tests.test_user_runtime`

交付：`codex-works/deliveries/P8RUNTIME1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8STAGE1 — 真机ACPI画面后停滞的有界屏幕启动阶段诊断

负责人：codex。状态：待领取。

用户确认R4已越过GOP且60秒停P3 ACPI READY，原runtime3物理THREADS PASS，当前正常USB-only runtime7没有后续屏幕检查点，不能据此判定ACPI/USB故障。补runtime7专属BSP同步阶段及失败原始64位码显示：IRQ准备/线程完成、可选AVX、SMP/AP/large/TLB/parallel边界、service ELF准备及首次CPL3前；只在既有Framebuffer Gate与原geometry验证内绘制，保持两个外层writer，使用已arm的RuntimeView，未arm/closed gate不访问MMIO；禁固件/驱动探测/guest写入注入，不改变runtime0/3/4/5/6预处理行为、算法校验、超时和USB-only权限。所有hook保留输入/返回寄存器和flags、SysV对齐，不在已arm计时器到sched_start或发布SMP deadline的临界区插入渲染，不在首次CPL3后写framebuffer。native执行实际helper/renderer验证阶段、失败码、guard/canary、Gate拒绝和真实坏体；原Gate与runtime观察器回归及独立0skip/source稳定；root完整重建runtime7 USB-only并实际VM验证主桌面/HID/FS原强契约，必要实际失败体证明阶段定位且不假PASS。原SanDisk已插回H，更新前核身份与R4成品SHA，备份flush/fsync/readback；不格式化/分区/内盘/Git。真机结果待用户复测，只交诊断不猜根因。

## 可修改文件

- `kernel/entry.asm`
- `kernel/boot_progress.asm`
- `include/boot_progress.inc`
- `kernel/runtime.asm`
- `kernel/smp_runtime.asm`
- `kernel/services_run.asm`
- `tests/test_boot_progress.py`
- `tests/boot_progress_probe.c`
- `docs/hardware-boot-progress.md`
- `codex-works/deliveries/P8STAGE1.md`

## 定向验收

- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8STAGE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

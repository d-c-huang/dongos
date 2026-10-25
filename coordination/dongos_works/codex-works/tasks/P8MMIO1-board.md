# P8MMIO1 — 真机S01 RamConflict的设备页与原始描述符诊断

负责人：codex。状态：待领取。

用户真机S01 IRQ PREPARE/CPU_COUNT8/FIRST_ERROR0x03030002，已精确对应device_policy.add映射前拒绝非MMIO11或RUNTIME描述符；未知设备与原始type，不能把错误名当普通RAM事实，也不能直接放开Reserved。保持所有原规划/输出原子性/UC ownership/检查/预算/USB-only策略，仅追加版本化88B只写诊断上下文：version,valid,error,slot,address,page,descriptor_index,type,descriptor_base,pages,attributes（11qword）。原plan与device_prepare两参数接口语义不变，新增nullable诊断接口经device_memory/runtime_probe导出，runtime7 ASM传独立kernel BSS上下文，不改Plan184/Views88。只有真实RamConflict分支在已验证rawmap后发布context.valid1，其他失败/success/无上下文不能显示旧内容；新out必须不别名输入/Plan，错误不发生设备映射/invalidate/MMIO读写。屏幕仅S01/failed/error匹配/versionvalid时在原两个Gate writer内以640x480亦安全布局显示stage/CPU/error/slot/DEV_ADDR/UEFI_TYPE/DESC_BASE/PAGES/ATTR，完整64位，不新增writer、不重开Gate/首次CPL3后不画，原无context屏幕保持。native debug/release实际planner+原强fixture/截断发布坏体、actual device_memory.prepare副作用stub证明RamConflict零query/map/invalidate、actual renderer独立像素oracle及坏体；独立0skip源稳定。root正常USB-only runtime7完整build/原桌面HIDFS两boot强gate和私有冲突屏VM，截图/raw记录匹配，失败历史保留。原SanDisk已插H，身份和旧成品SHA核验/备份/flushfsync全读回/只读卷审计，不格式化/分区/内盘/Git；只交下一轮准确定位，不猜根因或宣告物理桌面通过。

## 可修改文件

- `kernel/boot/device_policy.dg`
- `kernel/boot/device_memory.dg`
- `kernel/runtime_probe.dg`
- `kernel/runtime.asm`
- `kernel/entry.asm`
- `include/boot_progress.inc`
- `tests/device_policy_probe.dg`
- `tests/device_policy_probe.c`
- `tests/test_device_policy.py`
- `tests/test_device_memory_diag.py`
- `tests/device_memory_diag_probe.c`
- `tests/boot_progress_probe.c`
- `tests/test_boot_progress.py`
- `docs/hardware-mmio-conflict.md`
- `codex-works/deliveries/P8MMIO1.md`

## 定向验收

- `module:tests.test_device_policy`
- `module:tests.test_device_memory_diag`
- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8MMIO1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

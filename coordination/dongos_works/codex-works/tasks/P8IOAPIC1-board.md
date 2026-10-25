# P8IOAPIC1 — 真机MADT IOAPIC Runtime-MMIO定向兼容及USB发布

负责人：codex。状态：待领取。

用户照片S01 IRQ PREPARE CPU8 error03030002，slot1/address/baseFEC00000/type11/pages1/attrs8000000000000001。LAPIC planner已越过，但实际IRQ尚未初始化；当前Runtime&&slot!=0直接拒绝首IOAPIC。用户从暂不更改改为若时间不长修复并写原SanDisk H，且要求全部代码提交GitHub。扩展既有定向Runtime-MMIO兼容至可信MADT IOAPIC槽1..8，仅实际发现设备；保留LAPIC slot0，HPET/PM其他Runtime仍拒，所有非11/retained/duplicates/geometry/atomicity不放宽，rawmap只读、supervisor WRITE|UC/NX、无HHDM/WB别名、EFI runtime服务与allocator不变、不改deadline。native debug/release真实planner+prepare覆盖RuntimeLAPIC+首尾IOAPIC与其它Runtime拒绝、旧只LAPIC/误放全部Runtime/非11坏体应正常oracle拒绝。独立0skip/source稳定。root正常runtime7 USB-only完整两boot原HID/FS/CPU强gate，8CPU私有EFI同时Runtime LAPIC+IOAPIC真实IRQ/线程回归、原rawdesc/PTE/无alias/129ticks等契约；私有guard取证不发布不冒充正常8CPU桌面。原SanDisk确认已回H，核身份/旧SHA/备份/flushfsync全读回/native只读FAT，不format/partition/internaldisk。验收集成后正常产物写盘，源码任务记录去claim_token公开副本提交推送GitHub，不改本机权威元数据；不抢占其它任务。

## 可修改文件

- `kernel/boot/device_policy.dg`
- `tests/device_policy_probe.c`
- `tests/test_device_policy.py`
- `tests/device_memory_diag_probe.c`
- `tests/test_device_memory_diag.py`
- `docs/hardware-runtime-ioapic.md`
- `codex-works/deliveries/P8IOAPIC1.md`

## 定向验收

- `module:tests.test_device_policy`
- `module:tests.test_device_memory_diag`
- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8IOAPIC1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

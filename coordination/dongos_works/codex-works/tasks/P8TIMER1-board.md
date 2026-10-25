# P8TIMER1 — 统一ACPI平台Runtime MMIO并修复真机HPET拒绝

负责人：codex。状态：待领取。

新真机照片S01/error03030002 CPU8，slot9 HPET FED00000/type11/pages1/attrs8000000000000001。此前逐设备Runtime放行边界过窄；按真实UEFI类型与所有权统一可信ACPI平台寄存器：本私有planner只接收MADT LAPIC/IOAPIC、校验HPET和SystemMemory PM timer(0..10槽)，type11含Runtime允许；全部非11 inclReserved/runtimecode/data/RAM仍拒。Runtime位仅SetVA映射元数据，当前EBS后无EFI RuntimeServices/SetVA，无宽WB/HHDM映射，allocator只type7非Runtime；原rawmap attrs不改，资源/重复/几何/诊断/失败原子性/WRITE|UC supervisorNX/PCI-DMA独立Runtime拒绝不变，不改deadline。native两模式实际planner/prepare覆盖11槽12mask、所有同时Runtime、HPET+PM retained冲突/重复、全部非11两属性态拒绝及0sideeffect，真实旧slot>8/slot>9/slot!=0/全Runtime拒绝及误放RAM/Reserved坏体oracle正常拒绝。独立五模块7项0skip/source稳定。root正常runtime7 USB-only完整两boot原HID/FS/CPU强gate；8CPU私有EFI实际LAPIC+IOAPIC+HPET type11 Runtime原map完整字节快照和最终对照、IRQ线程129ticks65switches/真实PTE UCsuperNX/三HHDM无alias/完整磁盘SHA，私有cmp1→2 S03取证不发布不冒称8CPU全SMP桌面。用户已确认原SanDisk H插回，核身份旧SHA备份flushfsync全readback/readonlyFAT后正常成品写盘，不format/partition/internaldisk。沿用用户代码推送授权，完成后代码与去claim_token公开任务记录推GitHub。

## 可修改文件

- `kernel/boot/device_policy.dg`
- `tests/device_policy_probe.c`
- `tests/test_device_policy.py`
- `tests/device_memory_diag_probe.c`
- `tests/test_device_memory_diag.py`
- `docs/hardware-runtime-platform-mmio.md`
- `codex-works/deliveries/P8TIMER1.md`

## 定向验收

- `module:tests.test_device_policy`
- `module:tests.test_device_memory_diag`
- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8TIMER1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8LAPIC1 — 真机LAPIC Runtime-MMIO的定向UC映射兼容

负责人：codex。状态：待领取。

用户新图精确证据：S01/error03030002/CPU8，DEVICE_SLOT0，MADT LAPIC address/page/base FEE00000，descriptor pages1/typeB=11，attributes最高RUNTIME位设置。当前policy把runtime type11也当RamConflict，而该bit是UEFI虚拟运行时映射要求并非RAM类型；内核EBS后无EFI runtime调用/SetVirtualAddressMap，旧root/宽HHDM已退休，新root显式白名单，allocator仅非runtime type7，device映射为supervisor WRITE|UC/NX且platform读前核MSR地址。最小修复仅允许slot0可信MADT LAPIC的type11带RUNTIME，其他slot runtime type11继续拒绝，所有非11(含Reserved/runtimecode/data/RAM)、retained/duplicate/几何/原子性/UC flags保持，rawmap attrs不改、不硬编码FEE或整串attr、不改user.devices或allocator/EFI服务/预算。原生debug/release/O0O2实际planner+prepare新增runtimeLAPIC成功/ctx全零/PTE权限与query→map顺序，其他runtime设备仍fail且0sideeffects；真实旧拒绝/误放所有runtime/误放RAM坏体应正常oracle拒绝。独立0skip/source稳定。root正常USB-only runtime7两boot原GUI/HID/FS/CPU强gate，以及8CPU私有EFI type11+runtime LAPIC descriptor结合真实IRQ线程完成的regression VM，核原描述符不变/UC supervisor NX PTE与无WB/HHDM别名、129ticks等原IRQ契约；必要私有guard1→2停在S03取证不能冒充正常成品。原SanDisk已插H，验证后核身份/旧SHA、备份flushfsync全readback及readonlyFAT审计，不format/partition/internal/Git。物理是否继续到desktop待用户复测。

## 可修改文件

- `kernel/boot/device_policy.dg`
- `tests/device_policy_probe.c`
- `tests/test_device_policy.py`
- `tests/device_memory_diag_probe.c`
- `tests/test_device_memory_diag.py`
- `docs/hardware-runtime-lapic.md`
- `codex-works/deliveries/P8LAPIC1.md`

## 定向验收

- `module:tests.test_device_policy`
- `module:tests.test_device_memory_diag`
- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8LAPIC1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

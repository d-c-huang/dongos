# ACPI 平台寄存器的 Runtime MMIO 兼容

真机依次在 LAPIC 槽0、IOAPIC 槽1和 HPET 槽9被同一策略拒绝。最新照片为 S01 IRQ PREPARE、CPU COUNT=8、error=0x03030002、slot9、address/base=0xFED00000、type11、pages1、attributes=0x8000000000000001。此次仍停在规划阶段，不能据此断言实际中断、8核启动或桌面完成。

上两次修复按槽位逐项允许 Runtime，范围过窄。EFI_MEMORY_RUNTIME 是 SetVirtualAddressMap 的映射要求，不能代替内存类型或资源所有权判断；低位1为 UC 能力，属性能力不一定等同当前设置。[UEFI 定义](https://github.com/UEFI/UEFI-Specification-Release/blob/main/source/07_Services_Boot_Services.rst)

## 统一规则及边界

私有 `boot.device_policy.add` 仅由 `plan_core` 调用，接收已经由 ACPI 发现、校验的 LAPIC、最多8个 IOAPIC、HPET 和 SystemMemory PM timer，共11槽。对这些寄存器，已描述的页必须为 type11 MMIO；Runtime 属性不再按槽位另外拒绝。未发现的设备不产生规划项，SystemIO PM timer 不创建 MMIO 映射。地址和属性整串均不硬编码。

所有非11类型，包括 Reserved、EFI Runtime Code/Data、Conventional RAM，仍拒绝。原始地图及 attributes 不改写；重复页、retained 资源冲突、几何、Plan184B、Views88B、Conflict88B、失败原子性和首次诊断保留。HPET/PM 也不能与其他设备共页或跨越原寄存器窗口。

设备页继续以独立 supervisor WRITE|UNCACHED、NX 映射。新 BSP 根只保留既有显式白名单，不增加宽 HHDM/WB 别名；RAM allocator 仍仅使用非 Runtime type7。当前 EBS 后不调用 EFI RuntimeServices 或 SetVirtualAddressMap。本次不改 PCI/DMA 的独立 Runtime 拒绝规则、USB-only 权限、EFI 服务、页表分配、原生定时或等待期限。后续如引入 EFI RuntimeServices，必须单独设计其映射与缓存所有权，不能沿用本寄存器规划器推定固件调用安全。

## 验证与发布

实际 planner/prepare 原生测试覆盖11槽、12种能力组合、全部设备同时 Runtime、两API、空诊断与输入不变、query 全部先于 map/invalidate、flags9。全部非11类型在 Runtime 和非 Runtime 两态均拒绝；HPET/PM 的 retained、重复和几何错误仍失败且保持原有副作用边界。旧的 Runtime 全拒绝、仅 LAPIC、仅中断控制器、仅拒 PM，以及误放 RAM/Reserved 等实际坏体必须由同一原生 oracle 正常拒绝。

完整证据位于 `build/hardware/usb-platform-mmio-20261026-r1/`。正常成品使用原 USB-only runtime7 两次桌面/HID/文件持久性/CPU 观察器；另外8CPU私有 EFI 同时标记 LAPIC、IOAPIC、HPET 的真实 Runtime 描述符，保存原地图完整快照并逐字节重建验证，核对实际 IRQ/线程契约、PTE、三处 HHDM 无别名及磁盘 SHA。私有 post-runtime cmp1→2 guard 的 S03 受控终态只用于部件取证，不发布，也不作为完整8CPU SMP/桌面通过。SystemMemory PM timer 由原生 prepare 测试覆盖；当前 q35 实际 PM timer 为 SystemIO，不冒称其已完成 MMIO 硬件测试。

独立复验、实际正常启动和定向回归通过后，核对原 SanDisk H: 的身份、旧 SHA，备份、flush/fsync、完整读回及只读 FAT32 检查后发布正常成品。入口保留 DIAG R4 和 S01–S14。实际 Intel 电脑能否越过 S01及进入桌面、键鼠是否正常，仍须用户真机复测。

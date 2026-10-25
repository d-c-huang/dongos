# LAPIC 被标记为 Runtime MMIO 的启动兼容

用户真机照片的确定字段为：S01、FIRST ERROR=0x03030002、CPU COUNT=8、DEVICE SLOT=0、DEV ADDRESS/DESC BASE=0xFEE00000、DESC PAGES=1、UEFI TYPE=0xB。属性最高位 RUNTIME 已设置；本次修复不根据模糊的低位转录固定属性串或设备地址白名单。

原策略要求所有已发现的平台设备页都是非 Runtime 的 MMIO，因此错误拒绝了这个仍为 type11 的 LAPIC 页。`EFI_MEMORY_RUNTIME` 表示调用 SetVirtualAddressMap 时的运行时虚拟映射要求，不将 MMIO 改为 RAM；描述符属性也不必等同于当前 PTE 设置。[UEFI 内存类型与属性定义](https://github.com/UEFI/UEFI-Specification-Release/blob/main/source/07_Services_Boot_Services.rst)

## 定向变更

仅将规划器拒绝条件改为 `kind != 11 || (runtime && slot != 0)`。slot0 来自已经校验的 MADT LAPIC 地址；不硬编码 FEE00000，也不按整串 attributes 接受任意地址。其他 Runtime IOAPIC、HPET、内存型 PM timer 仍拒绝；所有非11类型（包括 Reserved、Runtime Code/Data、Conventional RAM）仍拒绝。

Plan184B、Views88B、Conflict88B、输出原子性、retained页冲突、重复页、几何、原始地图只读和诊断均不改变。LAPIC与保留内核资源重叠仍报ResourceConflict，不因为 Runtime 位而绕过。user.devices 的PCI/DMA Runtime拒绝、USB-only策略、分配器与超时不修改。

## 缓存与固件边界

这个启动路径在 ExitBootServices 后不调用 EFI RuntimeServices，也不调用 SetVirtualAddressMap；BootInfo160未传入EFI服务表。电源模块中的runtime名称指内核自己的ACPI实现，并非UEFI运行时调用。

新的BSP页表只映射显式kernel、handoff、pool、stack、RSDP和framebuffer白名单，不为EFI Runtime范围批量创建WB别名。切换前拒绝PGE/PCID，执行既有WBINVD/MOV CR3流程，原宽泛identity/HHDM映射已退休。分配器和SMP低页选择继续仅从非Runtime type7取得可用RAM；type11不进入RAM池。

设备页仍通过既有 supervisor、WRITE|UNCACHED、NX 的独立页映射安装；原平台代码在首次LAPIC MMIO读取前核对IA32_APIC_BASE与MADT地址。属性低位不用于推断当前缓存策略，真实PTE的UC位和所有权由内核自身配置及验证。

## 验证与介质

原生测试保留原类型/别名/原子性与失败零映射检查，并增加 Runtime LAPIC 的成功、空Conflict、raw descriptor不变与UC权限验证；能力组合覆盖Runtime单独、0x1004、0x100D及UC/WC/WT/WB。实际恢复旧拒绝、误放所有Runtime、误放Reserved/RAM及吞错误等坏体均由同一oracle拒绝。

完整成品及实际虚拟机证据位于 `build/hardware/usb-lapic-20261025-r1/`。正常runtime7 USB-only继续完整两次桌面/HID/文件持久性强观察器；另用8CPU私有EFI提供Runtime MMIO LAPIC描述符，并在真实IRQ/线程证明返回后以私有cmp1→2 guard停于S03取证。此受控候选不发布：必须核对描述符属性原样、真实UC/supervisor/NX映射、无LAPIC宽HHDM/WB别名、原129ticks/65switches等线程契约、空Conflict和全盘SHA/停机。

只在独立复验与实际启动均通过后更新原SanDisk H:，先核身份/旧SHA并备份，再flush/fsync、全SHA读回与原卷只读审计。不格式化、改分区、写内盘或Git。入口仍为DIAG R4，内核保留S01–S14；下一次真机启动确认是否越过S01，若仍失败或停在后续阶段，记录完整最后画面。当前不将虚拟机结果等同于这台Intel电脑的桌面/HID已通过。

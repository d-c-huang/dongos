# 真机 Runtime IOAPIC 兼容

新照片仍在 S01 IRQ PREPARE，CPU COUNT=8、FIRST ERROR=0x03030002，但失败对象已从 LAPIC 槽0移到首个 IOAPIC 槽1。DEV ADDRESS/DESC BASE=0xFEC00000、UEFI TYPE=11、DESC PAGES=1、EFI ATTR=0x8000000000000001。规划器先处理 LAPIC 再处理 IOAPIC；这说明 LAPIC 的规划检查通过，尚不证明中断、8核启动或桌面完成。

属性最高位为 EFI_MEMORY_RUNTIME，低位1为 UC 能力。Runtime 位不将 type11 MMIO 改为 RAM；能力位也不等同于当前页表设置。[UEFI 内存属性定义](https://github.com/UEFI/UEFI-Specification-Release/blob/main/source/07_Services_Boot_Services.rst)

## 定向变更

原 `kind != 11 || (runtime && slot != 0)` 仅兼容 LAPIC，仍拒绝 Runtime IOAPIC。现在仅将 Runtime 兼容范围扩展到已经由 MADT 发现并校验的 IOAPIC 槽1至8；槽0的 LAPIC 兼容保留。未发现的 IOAPIC 不生成规划项；不按 FEC00000 地址或整串属性硬编码。

HPET 槽9与内存型 PM timer 槽10继续拒绝 Runtime。所有非11类型，包括 Reserved、Runtime Code/Data、Conventional RAM，仍拒绝。资源重叠、重复设备页、几何、Plan184B、Views88B、Conflict88B、失败原子性与原始地图只读契约保留。Runtime IOAPIC 与 retained 资源冲突仍返回 ResourceConflict。

设备映射仍为 supervisor WRITE|UNCACHED、NX；不新增宽 HHDM/WB 别名，不修改 EFI RuntimeServices、SetVirtualAddressMap、RAM 分配器、PCI/DMA 策略、USB-only 权限或原等待期限。当前 EBS 后路径不调用 EFI RuntimeServices，上次 LAPIC 修复的页表与缓存所有权审查继续适用。

## 验证与发布

原生测试使用实际 planner 与 prepare，两 API、多能力组合、首尾 IOAPIC 及同时 Runtime LAPIC/IOAPIC，检查输出与空诊断、raw 属性只读、先 query 后 map/invalidate、UC 权限及失败零映射。旧的仅 LAPIC 放行、拒绝全部 Runtime、误放任意 Runtime 或非11类型等实际坏体应由同一 oracle 正常拒绝。

完整成品及实际运行证据在 `build/hardware/usb-ioapic-20261025-r1/`。正常 USB-only runtime7 使用原完整两次桌面/HID/USB 文件持久性与 CPU 观察器；另以8CPU私有 EFI 同时提供 Runtime LAPIC 和 IOAPIC 描述符，核对真实 IRQ/线程契约、raw 属性、设备 PTE、无 HHDM 别名及全盘 SHA。私有 post-runtime cmp1→2 guard 仅用于 S03 终态取证，不发布，也不作为完整8CPU桌面通过。

独立复验和实际运行通过后，核对原 SanDisk H: 的身份及旧 SHA，备份、flush/fsync、完整读回、只读 FAT32 检查后发布正常成品。入口保留 DIAG R4 和 S01–S14 诊断。下次真机启动仍需确认越过 S01，桌面出现后测试有线 USB 键鼠；本机模拟结果不替代这台 Intel 电脑的物理验收。

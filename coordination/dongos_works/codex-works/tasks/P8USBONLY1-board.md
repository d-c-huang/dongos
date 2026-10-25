# P8USBONLY1 — 仅USB存储授权的真机桌面与键鼠测试版

负责人：codex。状态：待领取。

用户已报告真实DONGOS P3 THREADS PASS，继续准备同一SanDisk 8GB MBR FAT32的桌面/键鼠版。不格式化、不访问内置数据盘。显式usb_only正常runtime7构建：同一已哈希services快照给kernel和全部CPL3，默认profile保持旧行为；共享角色策略排除PCI BLOCK，kernel admit/grant在任何PCI写/BAR/DMA前拒slot2，block在PCI扫描前只走USB且失败不回退；USB含分区视图以适配原MBR FAT32，READ/WRITE相对偏移/容量严格边界、保留原proxy校验；必要时有界扩展USB-profile FAT审计bitmap，不删审计门。须只读核实H实际MBR/BPB和FSInfo，必要兼容修复可在已声明FS文件内最小实现，不能更改物理文件系统跳过错误。实际同一MBR USB启动/数据+键鼠2/3，混合可写NVMe/AHCI/VirtIO哨兵，证明backend4、内盘无授权/BAR/DMA，原内盘SHA未变；真实GUI与USB键鼠消费并验证启动文件保持。旧USB runner拓扑断言不放宽，新contract另实现。严禁自行更新H直到候选通过复验，插回后核身份/备份/flush读回，无Git提交推送；hardware待用户实际运行，不外推PCID/WC验收。

## 可修改文件

- `tools/build.py`
- `tools/user_services.py`
- `tools/usb_only_profile.py`
- `services/lib/hardware_profile.dg`
- `services/drivers/device_policy.dg`
- `kernel/user/devices.dg`
- `services/drivers/block_service.dg`
- `services/drivers/xhci_service.dg`
- `services/drivers/usb_partition.dg`
- `services/fs/fat32.dg`
- `tests/test_usb_only_profile.py`
- `tests/usb_only_policy_probe.dg`
- `tests/usb_only_policy_probe.c`
- `tests/test_usb_partition.py`
- `tests/usb_partition_probe.dg`
- `tests/usb_partition_probe.c`
- `tests/test_usb_fat32.py`
- `tests/usb_fat32_probe.c`
- `tests/run_usb_only_hardware_qemu.py`
- `docs/usb-only-hardware.md`
- `codex-works/deliveries/P8USBONLY1.md`

## 定向验收

- `module:tests.test_usb_only_profile`
- `module:tests.test_usb_partition`
- `module:tests.test_usb_fat32`
- `module:tests.test_usb_block_proxy`
- `module:tests.test_device_manager`
- `module:tests.test_usb_runtime_qemu`

交付：`codex-works/deliveries/P8USBONLY1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

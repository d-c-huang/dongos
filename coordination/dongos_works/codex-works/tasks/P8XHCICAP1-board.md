# P8XHCICAP1 — Intel xHCI首寄存器页能力与固件占用只读诊断

负责人：codex。状态：待领取。

用户真机USB INFO页扫描成功/X1/E-O-U0/Intel8086:A12F/ECAM E00A0000/BAR0 DF510004 BAR1 0/PA DF510000/FLAGS1103，首页无UEFI描述符，不可归因Runtime BAR拒绝。原U盘已插回H。下一明确主动停止版只读xHCI首4KiB能力/状态和页内扩展cap，定位现authority/controller的scratchpad/BIOS-owned/unsupported gates，未证根因不盲改正常门禁。新cap模块先复用原usb_preflight.run可信配置普查、读取PCI command，拒invalid/unaligned或不decode地址，不启用MEM/BME、不reset/ack/write任何控制器/PCI寄存器。private user.devices只append受guard的只读32b读取函数：原mmio_range(PA,4096,false)逐调用先guard、readonly supervisor UC/NX WINDOW，原map/replace+invlpg/TLB逻辑，私有cache确认RO；配置/CPU物理限制/RAM Runtime FB门保留，无用户cap/DMA。只读firstpage，CAPLENGTH/op bounds与extended64/相对next/8或16长度受限；跨页显式incomplete，绝不猜BAR总大小或map其他页。固定Report32u64/256B，once/done-last，原error原样。raw cap0/hcs1/hcs2/hcc1/pagesize/usbcmd/usbsts/legacy support/control/首未知cap、解码scratch/context/AC64。reject_mask仅当前代码可观测特征条件的对照，不冒充真实驱动错误或完整admission结论。工具strict复用前工具正常命令计划，private overlay增原usbinfo+新capmodule、private devices append、root import；三obj重编/真实link/双manifest/EFI单banner。正常所有源/默认策略/17服务不变。stage24新title DONGOS XHCI CAPS和15rows，marker后cli/hlt前无用户态，仍既有Gate/geometry；明确xhci-capability-probe.json无normal metadata。native真实新cap模块和真实append guard/map/load体（只hardware boundaries stub）debug/release/真实坏体验证，0skip正式独立。root8CPU真实首cap页PCI/MMIO/RO PTE/实际Report/15行pixels+code、无控制器写/新授权/用户态，wholeUSB/internal不变，通过后备份写原H/fsync/readback/readonlyFAT。用户下次拍全部字段，根因仍待真实cap数据。沿既有授权上传GitHub。

## 可修改文件

- `kernel/boot/xhci_capability_probe.dg`
- `tools/build_xhci_capability_probe.py`
- `tests/test_xhci_capability_probe.py`
- `tests/xhci_capability_probe.c`
- `docs/hardware-xhci-capability-probe.md`
- `codex-works/deliveries/P8XHCICAP1.md`

## 定向验收

- `module:tests.test_xhci_capability_probe`

交付：`codex-works/deliveries/P8XHCICAP1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

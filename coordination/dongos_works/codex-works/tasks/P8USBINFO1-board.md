# P8USBINFO1 — S14隔离版无响应后的只读USB硬件屏幕普查

负责人：codex。状态：待领取。

用户明确BSP DIAG在S14/0/8CPU等待60秒且F12无反应，原SanDisk已插回H。准备单次只读硬件普查诊断，在原BSP legacy入口、任何user_run前扫描可信MCFG，显示USB X/E/O/U计数、首个与device_manager同优先序的header0 xHCI ECAM/vendor-device/BAR0/BAR1/解码PA及其首4KiB页原UEFI描述符type/base/pages/64attrs、framebuffer范围及状态flags/scanerror。仅PCI配置读取，不写BAR/command、不sizing、不映射/读取BAR、不授DMA/角色/IRQ/不放宽Runtime BAR门、不调用固件服务。types/attr是观测数据，不误称真实驱动失败或确证根因。新DG模块仅私有kernel-profile图import并导出固定Report指针，正常源码/策略未改变。新工具复用已验证BSP构建工具的strict normal/log模板，私有DG overlay只加模块/import，重编actual dong_probe.o、services_run.o和entry.o，真实link/IMG/manifest双消费者EFI，私有EFI唯一banner USB INFO DIAG R1。private services_run在user_run前call诊断/HW_STAGE24后串口完成marker并CLI/HLT，intentional_stop明确，不进用户态；private entry沿现screen_draw与原Gate/geometry，只在精确stage24/version/done报告显示15行(640x480内)，报告地址固定getter、字段地址不解引用。不能恢复退休view/在AP用户deadline中绘图。不复制normal build-inputs、不冒充desktop可启动成品；专门verify诊断来源/仅三内核对象替换/单banner/overlay/IMG/17服务不变/输出安全。原生直接编译真实新DG体和实际View160，hardware边界stub只模拟config reads与startup；覆盖多USB类型/计数、多function/selection、32/64BAR/高PA/invalid BAR、原错误传播、MCFG非零first、完整descriptor64attr/FB/read-only及坏体oracle。实际NASM/ELF/EFI构建及root8CPU QEMU明确停止版，读实际Report/原map/MCFG/PCI/BAR/全部屏幕像素，验证无BAR MMIO/设备授权/用户启动，normal源码对象+17服务/全部内盘及USB整盘保持不变。root确认后只将明确只读诊断版备份写原H+fsync/readback/只读FAT，用户下一屏回传真实信息后再修，仍不声称S14故障已解决。沿既有授权提交GitHub。

## 可修改文件

- `kernel/boot/usb_preflight.dg`
- `tools/build_usb_preflight.py`
- `tests/test_usb_preflight.py`
- `tests/usb_preflight_probe.c`
- `docs/hardware-usb-preflight.md`
- `codex-works/deliveries/P8USBINFO1.md`

## 定向验收

- `module:tests.test_usb_preflight`

交付：`codex-works/deliveries/P8USBINFO1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

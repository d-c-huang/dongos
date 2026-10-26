# S14 后无响应的 USB 只读普查

正常多核版在8 CPU Intel真机停留S19；显式BSP用户态隔离版同样在S14停留，等待60秒后F12没有反应。两种路径都未显示桌面，将下一轮观察放到共用设备发现和地址属性；现有画面仍不能证明具体驱动、锁或CPU指令是根因。

## 本版会主动停住

入口标识为 `DongOS USB INFO DIAG R1`。在既有平台/多核自检和服务镜像准备完成后，任何用户程序开始运行前，扫描可信MCFG中的PCI配置头并显示 **DONGOS USB READ ONLY**。看到这张15行画面就是本次诊断到达了预期停止点，不需要按F12或继续等待桌面。请拍下从标题到最底部 **FLAGS** 的完整屏幕。

它只通过原配置读取器读取PCI配置，不写command或BAR、不做全1写入的BAR sizing、不映射/读取控制器BAR、不接管控制器、不授予设备角色/DMA/IRQ。原BAR Runtime拒绝、USB-only权限和正常启动策略均不修改。已由固件配置的设备状态不因此被宣称为零；这里检查的是诊断没有新增硬件权限或控制器操作。

## 画面字段

15行依次为CPU COUNT、SCAN ERROR、USB X/E/O/U、XHCI ECAM、VENDOR/DEVICE、BAR0 RAW、BAR1 RAW、BAR PHYS、UEFI TYPE、DESC BASE、DESC PAGES、EFI ATTR、FB BASE、FB BYTES、FLAGS。每个值都是64位十六进制，地址字段只绘制数值，不作为指针访问。

USB计数包含xHCI、EHCI、OHCI、UHCI；PCI类别编码核对了[Linux原始类别定义](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/pci_ids.h)。打包值从最低16位起依次是X/E/O/U，即画面最右四位是xHCI数量。例如 `0000000000020001` 表示xHCI=1、EHCI=2。原报告保留各自完整64位计数，画面超过16位时饱和并设置flags。

选择第一个header类型0的xHCI，与现有管理器同优先级时保留首项的顺序一致。BAR0/1为原配置值；64位BAR合并高32位。只查这个BAR首个4KiB页的原UEFI描述符，**没有测量BAR总长度，也没有证明整个BAR范围可用**。FB是已保留显示器的物理范围。

SCAN ERROR保留实际配置读取错误；`0x0b010001`为诊断自身的输入/视图校验错误。0仅表示这次只读扫描完成，不等同于驱动、USB或桌面运行成功。

| FLAGS 位值（十六进制） | 含义 |
| --- | --- |
| 1 / 2 | 选中eligible xHCI / BAR为memory而非I/O |
| 4 / 8 / 10 | 首页有完整覆盖描述符 / 描述符带Runtime / 描述符类型不是11 |
| 20 / 40 / 80 | 首页与FB重叠 / BAR无效 / 没有eligible xHCI |
| 100 / 200 / 400 | 扫描完整 / 多个完整覆盖描述符 / 还有其他USB接口类型 |
| 800 / 1000 / 2000 | 打包计数饱和 / 64位BAR / BAR未按4KiB对齐 |

如果位4没有设置，描述符字段全零表示**没有覆盖描述符**，不能把UEFI TYPE=0解读成真的Reserved描述符。类型不是11也不自动表示当前策略拒绝：原策略仍有受限的高地址Reserved UC例外；本版报告原数据，不虚构一次尚未发生的驱动错误。

## 构建和验收

`python -m tools.build_usb_preflight --normal-source NORMAL --normal-build-log LOG --output NEW_DIRECTORY` 基于已验证的正常USB-only构建生成独立停止版。正常源码不变；私有profile只增加本模块和导入，重新编译真实DG图。私有entry在现有screen_draw、几何检查和完整Gate内显示stage24数据，15行最后像素在y=470内，适配原640×480下界；私有services_run在user_run前读取报告、绘图、输出完成marker后停机。原1–23阶段保持原逻辑。

只替换entry.o、dong_probe.o、services_run.o三个内核对象；私有EFI仅改标识，两个IMG manifest消费者都重汇编，17服务保持原字节。使用专门 `usb-preflight.json` / `verify_preflight`，明确 `intentional_stop`，不复制正常build-inputs或冒充可启动桌面的普通成品。

原生测试直接编译真实DG扫描/BAR/描述符函数，只有配置读取和startup边界由只读模型提供；检查真实232B布局、View160、输入只读、重复run、坏体及错误传播。根协调器另运行真实8CPU QEMU，核对报告和实际PCI/MCFG/原图、完整执行代码与15行像素，确认没有用户程序、BAR映射或新增授权，单USB和三类内部哨兵盘整体哈希不变。正式结果以任务审查/集成记录为准。

验收后仅备份更新原SanDisk H: 的明确诊断文件，flush/fsync、完整读回和只读FAT32检查。真机下一屏的数据仍待用户回传，再据实修改。

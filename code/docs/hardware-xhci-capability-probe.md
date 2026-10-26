# xHCI 首页能力只读诊断

真机USB普查已返回：1个xHCI、vendor/device=8086:A12F、ECAM=E00A0000、BAR=DF510000，FLAGS=1103。BAR首页没有覆盖的UEFI描述符，不能把显示的零类型/属性当成Runtime拒绝的证据。多核与BSP用户态路径都曾停留在最后启动画面，本版继续获取共用设备路径的原始数据，不据此猜测具体故障。

## 操作

启动入口为 `DongOS XHCI CAPS R1`，随后主动停在 **DONGOS XHCI CAPS**。请拍完整15行到最底部FLAGS。此版不进入用户程序或桌面，也不需要F12响应。

复用原只读PCI普查选择的eligible xHCI。只读PCI Command低16位；如果MEM decode未开，明确跳过，不擅自打开。新增接口仅放在诊断构建的私有user.devices副本：每次先经过原mmio_range(..., false)守卫，再用现有map/replace/invalidate链建立BAR首页的supervisor、UC、只读、NX映射。首次缓存不能沿用旧的可写叶项。保留RAM/Runtime/FB/物理地址门，不写PCI、控制器、ownership、reset或ack寄存器，不授予新DMA/设备权限。

只读首4KiB页内CAP0、HCSPARAMS1/2、HCCPARAMS1、DBOFF/RTSOFF，以及版本适用时的HCCPARAMS2；检查CAPLENGTH后再读PAGESIZE、USBCMD、USBSTS。扩展链最多64条，只读取页内完整的已知8/16字节结构；超出首页就标记不完整。没有猜BAR总长度或访问其他寄存器页。

## 字段和判断边界

15行依次为READ ERROR、BAR PHYS、PCI COMMAND、CAP0、HCSPARAM1、HCSPARAM2、HCCPARAM1、PAGESIZE、USBSTS、XECP FIRST、LEGACY SUP、LEGACY CTL、OTHER CAP、REJECT MASK、FLAGS。每项为64位十六进制。USBCMD等其他原值也保存在固定256B/32u64报告中，read_count统计成功的32位MMIO读取。

Scratchpad数量按当前代码从HCSPARAMS2解码，Context大小和AC64来自HCCPARAMS1。扩展指针、类型和legacy拥有位核对了[Linux xHCI原始定义](https://raw.githubusercontent.com/torvalds/linux/master/drivers/usb/host/xhci-ext-caps.h)：legacy的BIOS/OS拥有位分别是16/24。此版只观察，不请求或伪造所有权转交。

REJECT MASK只对照当前authority/controller代码可观测的特征条件，**不是一次真实驱动调用的错误码**，也不验证BAR完整长度、DMA布局或未来重置后的状态。

| 掩码值（十六进制） | 当前代码中的对应条件 |
| --- | --- |
| 1 | 版本、CAPLENGTH或header条件不支持 |
| 2 | slots、ports、interrupters或偏移几何不符合检查 |
| 4 / 8 | Scratchpad数量非零 / restore特征位 |
| 10 | PAGESIZE不支持4KiB |
| 20 / 40 | legacy拥有/保留位或重复项不符合检查 / legacy control非零 |
| 80 | 当前代码不支持的扩展类型 |
| 100 | 已观测协议shape/重叠，或完整链的覆盖不符合检查 |

FLAGS中1/2/4/8分别表示有效普查、MEM decode、成功MMIO读、支持的header；10表示扩展链读完整，20表示发现legacy，40/80表示发现USB2/USB3协议。100表示超出首页，200表示没有eligible xHCI，400表示MEM decode关闭，800表示MMIO错误，1000表示重复legacy，2000表示64条限制，4000表示未知类型，8000表示协议重叠，10000表示BAR无效。以上位值均为十六进制。

链不完整时不会推断缺少协议覆盖；没有发现legacy或尚未读到它时，LEGACY字段零不代表拥有位已清除。掩码为零也不证明完整admission或桌面成功。Unknown只记录首个原始header，其低8位为类型，不解引用未知结构内容。READ ERROR保留原错误；0x0b020001是本诊断的输入/范围校验错误。

## 构建和验证

`python -m tools.build_xhci_capability_probe --normal-source NORMAL --normal-build-log LOG --output NEW_DIRECTORY` 使用受检正常来源和8命令模板。私有图只增加两诊断模块、一个根导入及devices末尾的只读接口；只重编三个内核对象和两个manifest消费者EFI，17服务、正常源和默认策略保持原字节。独立 `xhci-capability-probe.json` 明确主动停止，不伪装正常成品。

原生测试执行真实能力模块与真实私有reader/原守卫体，覆盖页边界、未知/legacy/协议、原错误、只读输入、once，以及先guard后映射和仅UNCACHED标志。根协调器另用真实8CPU QEMU核对原PCI/MCFG、寄存器、实际只读叶项及四级有效权限、代码和15行像素，确认无新增授权和用户入口，整USB与内部哨兵盘保持不变。正式结果以审查记录为准；真机下一屏仍待回传。

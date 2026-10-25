# P8USBONLY1 — USB 专用桌面候选

日期：2026-10-25。用户已报告真机 `DONGOS P3 THREADS PASS`，继续使用同一 SanDisk H 盘准备正常 runtime7 桌面与直接连接的有线 USB 键鼠。

## 实现

`tools/usb_only_profile.py` 生成完整 services DG 快照；内核和全部 17 个 CPL3 程序共用该根，build-inputs 保存原/快照源图 SHA。USB profile 固定 USB_ONLY=true / FAT_AUDIT_BYTES=2097152；默认模块保持 false / 32768。build 只允许正常 runtime7 USB profile，打包重复验证完整快照与成品。

共享 device_policy 排除 PCI BLOCK，kernel devices.admit/grant 在任何 PCI/BAR/DMA 操作前拒绝 BLOCK/slot2；block 初始化在 PCI 扫描前仅走原 USB proxy。失败不回退内盘。xHCI 要求恰好一个健康 512B BOT 存储设备。原 USB RPC 身份、epoch、计数、容量和错误校验全部保留。

新 usb_partition 为纯、无硬件模块：支持严格 FAT32 superfloppy 或唯一有效 MBR FAT32/EFI 分区。失败不写输出 View；READ/WRITE 相对 LBA 做两层减法边界检查后偏移，READY/FLUSH 保留 raw proxy 协议，FS 单独得到逻辑分区容量。

USB FAT bitmap 扩到 2 MiB，完整交叉链/循环/孤儿簇和双 FAT 审计保留。实际 H 主备 FSInfo 仅 hints 不同；USB 模式分别验证两副本范围，只允许 [488,496) 不同，其余 504 bytes、保留区和签名均不放宽。默认模式保持原严格行为。输入初始化和大卷 mount cache 的必要修复另登记 P8USBSTART1；旧测试/打包依赖另登记 P8USBADAPT1、P8USBFSTEST1。

## Native 与 host 证据

- `tests.test_usb_only_profile`：3 tests / 14.035s / 0 skip；`code/build/test/usb-only-profile/run-3a34ae465f76`。默认/USB native 62/63 checks，4 个真实坏体漏 rank/ledger/admit/grant 均正常拒绝；ELF/COFF。admit/grant 的 native 部分为实际入口早退片段与硬件回调计数，完整特权链以真实 VM 为准。
- `tests.test_usb_partition`：1 test / 30.049s / 0 skip；`code/build/test/usb-partition/run-7061adff058c`。正常 570 checks，28 次实际坏体执行拒绝，guard page、UINT32_MAX 末扇区、ELF/COFF。
- `tests.test_usb_fat32`：1 test / 93.750s / 0 skip；`code/build/test/usb-fat32/run-a42cb0bbb84b`。默认 3570、USB 8104 checks；2M 簇稀疏高位目录/文件真实读取，高位 seen、mirror/crosslink/orphan/cycle，504x2 个非hint差异与492个保留字节损坏拒绝，mark /8→/16 真坏体在两模式 rc1；源图稳定，ELF/COFF。
- 兼容 host 4 模块：28 tests / 22.951s / 0 skip，`code/build/hardware/usb-only-20261025-r1/host-compatibility.log`。
- 默认 FAT 3 模块：12 tests / 159.439s / 0 skip，`code/build/hardware/usb-only-20261025-r2/fat-default-tests.log`。
- 新独立 single-media runner `--selftest`：3 host controls / 0 skip。此项不运行 VM。

## 原 H 只读验真

磁盘 2，USB SanDisk Cruzer Blade，serial `4C530000010320109015`，7,798,784,000B，非系统/启动盘。Windows 设备分区 API 确认唯一 MBR FAT32 XINT13，offset 131072，size 7798652928。PhysicalDrive raw read 因访问限制未成功；未提权绕过，改读 `\\.\H:` VBR，并用分区 API 核对 MBR 几何来源。

BPB：512B/sector、8 sectors/cluster、reserved 3082、FAT sectors 14843 x2、hidden 256、total 15231744、1899872 clusters、FSInfo1、backup6。主备 VBR 相同，两 FAT 状态正常；主 FSInfo hints 为1899706/168，备份 unknown/2。R1 原严格 FSInfo 只读挂载失败保留在 `usb-only-20261025-r1/real-volume-mount-before.log`。

修复后 `usb-only-20261025-r2/real-volume-mount-after.log`：mount_error=0、ready=1、readonly=0、dirty=0、clusters=1899872、reads=45114、writes=0、flushes=0、bad_io=0、canaries=1、Scratch=2104040B。物理文件以 rb 打开，写/flush callbacks只计数并返回失败；未修复或写盘。原 EFI/IMG/TXT SHA 读回未变。

## 动态结果与待验范围

R2 成功构建但第一轮 mixed-run-1 **失败**：原输入服务对关闭 i8042 的 USB 拓扑先做 PS2 探测，INIT_FAILURE kind2/3 id4（input）报 0x05110007，随后 retry exhausted。保留完整 result/serial/command；该轮三内盘完整 SHA 未变，未声明桌面成功。此前初看日志误认为 FS 超时，已通过配置目录核实并更正为 input。

R3 包含 P8USBSTART1 的 USB 专用认证启动路径及大卷缓存资格适配，重新完整编译和复验。实际最终结果、成品 SHA、独立作业和 H 更新收据将在成功后追加。当前文档不声明真机桌面、warm PCID、物理 WC 或整个 P2/P8 验收完成。

R3 mixed-run-1 已确认 input READY，之后 FS config1 的10秒期限连续4次失败。原完整镜像中的 SERVICES.BIN 约33MB，512B cluster 链长约65k；mount 中 `mark_chain` 先做Floyd再单独标记存在重复遍历。USB模式改为单遍全局seen：首次bitmap索引前明确检查cluster范围，最多clusters次，next保留原值域检查，只有EOC返回长度；seen同时拒绝同链环与跨链汇合。默认仍先Floyd且I/O顺序保留，孤儿/大小/LFN/目录审计不变。独立静态复核通过；新增非法初始cluster、0xffffffff、多节点环、尾部汇合及size超链真实反例，失败Volume全零未发布。

单遍完整native：`usb-fat32/run-f9caa2ecd7f6` 107.238s/0skip/source_stable=true；随后只增C oracle复用完全相同DG objects，两模式各9151checks，`usb-fat32/single-pass-extra-fdd1400b081a`。真实H单遍只读挂载 `usb-only-20261025-r4/real-volume-mount.log`：44782 reads/0writes/0flushes、ready1/readonly0/dirty0、canaries1。后续仅做512B双FAT比较的64次unaligned u64比较、bitmap按8B清零且保留尾字节处理；所有512B/bitmap字节覆盖完整，不省略审计。

R4 mixed-run-1 已实际进入四窗口正常桌面，FS/SHELL/P7_CLIENTS全部READY，完整真实ELF代码和私有用户池检查通过；但hid焦点移动失败，故整轮仍是失败，三种可写内盘整盘SHA不变。R4 mixed-run-2 曾FS期限重试后出现 `DONGOS_P6_TLB_FATAL=0x06030004`；root停止该已fatal的独立QEMU进程，保留原serial/result，不把连接被关闭当作原始失败原因。runner新增fatal立即判错以及真实input/mouse/transport失败捕获；每个相对鼠标步必须观察USB mouse sequence增长、queue消费和实际pointer变化，保留原100步/终点阈值。

R5 mixed-run-1 仍有FS10秒期限重试，随后FS READY与TLB Timeout，整轮失败、所有QEMU已停、三内盘SHA不变。CPU复制/遍历优化不足以覆盖该卷完整I/O成本，另登记 P8USBAUDIT2，仅USB可信内核FS cfg1使用60秒有界启动预算，其余17配置与default保持10秒，所有hz乘法前防溢出且非法输入不写Catalog。原“不改期限”的优化尝试没有当作成功或删掉失败。R6重新全量构建，后续实际启动及独立作业仍须通过全部FAT/GUI/HID/FLUSH/重启和内盘SHA门槛。

## R6 观察器修复与不放宽的门槛

R6 原暂停式 mixed-run-1..5、mixed-no-pcid-1 的 HID 等待失败已保留。完整诊断证明鼠标事件在 actual DMA 的正确 head/cycle 等待消费，CPU0在共同 fail-stop；Bridge第一失败为BSP stage13 SERVICE_AFTER Held(0x06090004)，AP stage5 ACQUIRE Timeout(0x06090005)，clock已超过原1秒deadline约2.8秒。长时间 QMP stop 取证消耗了 WHPX 的时钟期限；旧 bootstrap exception 栈与SMP当前栈不同，曾提出的PIC向量推断已撤回，没有据此改PIC、GS或SMP源码。

独立无暂停对照 `usb-only-20261025-r6/live-pause-diagnostic-1/result.json` passed=true：相同R6/WHPX，首次停止在真实鼠标报告、F12/pwd完成之后，三内盘SHA不变。TCG原暂停路径确有实际HID source/GUI消费及MKDIR成功，长WRITE在30秒host UART期限失败；未把它算作完整通过。

新显式 `--live-capture` 在运行阶段不发stop，只做有界RO回执取证；真实HID、UART与磁盘命令、四窗实际focus/GOP像素完成后最后sync，稳定帧连读3次，再唯一stop_final。停止后禁止resume/key/focus/UART/FS动作，全部强检查在同一最终冻结epoch完成。活动期每窗GOP取证明确标记时间；冻结后重验全部client/cache样本与相同surface身份，对最后focus的Terminal再次读实际GOP，不伪装重叠窗在最终帧同时可见。host UART单命令120秒只用于约69k已占簇的完整真实分配扫描，不改变guest期限/命令/期望响应。

`live-full-gate-1` 已真实完成HID、write/append/remove/cat/sync，最终Bridge全零和CPU failed=0，但旧单CPU PCID collector读legacy globals而失败，未算成功。Live observer另实现源绑定的每CPU SMP PCID collector：Header布尔、CR4.PCIDE/PGE、真实tag/root、当前slot/token/incarnation/Domain.Process/Catalog一致，fallback只允许kernel或严格绑定的无tag用户root，disabled retained必须0，保留计数上界；Seen仅记录不冒作保留证明。旧collector保留未改。5项host controls含11种PCID错误拒绝、唯一停止及禁止恢复，0skip；R6全部17服务assembly/layout与160B kernel View重新只读核验通过。

R6冻结成品：BOOTX64.EFI 28160B SHA256 6399ab25bdb7c859f134b4545f934f37c069651601f6d044e918fd4141c5511e；DONGOS.IMG 2003058B SHA256 b263a40326c553762e86aa83d0ca8008909838b6b9b339453148cba94067cef0（低于2MiB）；SERVICES.BIN 33333248B SHA256 95ec41dd90b46517240c2a073aba0969863985a75eb593409ffce6aeb1a183e4。最终完整结果另见 `usb-only-20261025-r6/live-full-gate-2/result.json`；只有passed=true及两次启动全部停机、源图稳定、三内盘整盘SHA不变才允许发布H。


## AI交付 2026-10-25T12:17:02+00:00 · codex-mcp-14619bbd432c41a6

声明21文件的实现、真实坏体测试、文档与完整失败历史已落盘冻结。USB_ONLY同一已哈希快照给kernel/17CPL3、PCI block多层拒绝、单USB MBR视图与完整FAT审计/有界大bitmap/仅FSInfo hints兼容实现完成；默认保持，相关fixture/输入缓存/FS预算补充已独立验收集成。R6 SHA与17 assembly/Layout已核，原H1899872簇只读全审计通过0write/0flush。WHPX旧QMP暂停式观测诱发BKL/APdeadline，保留首失败；同镜像no-stop独立mouse+F12/pwd对照PASS。Live模式最终只停一次且绝不恢复，旧强契约、SMP全CPU健康与真实每CPU PCID状态检查保留，5项host控制0skip。live-full-gate-1完整HID+文件写追加删读sync已过，collector使用legacyPCID globals误报已改为源绑定SMP；此轮不算整体验收。当前live-full-gate-2完整两boot独立主测进行中，尚未完成；必须其passed true、两QEMU全部停、源图稳定、内盘完整SHA不变后才验收与发布H。现在提交实现以排6模块独立native/host复验，不声明整体完成，不写H/不提交推送。

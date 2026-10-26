# P8USBINFO1 交付

用户确认BSP隔离版S14/0/8CPU超过60秒且F12无响应，原SanDisk已插回H。实现显式用户态之前主动停止的只读USB硬件普查，不改任何既有正常生产源/安全门/默认策略。

新boot.usb_preflight使用真实配置读取器扫描可信MCFG，记录USB X/E/O/U和首个header0 xHCI、原BAR0/1及32/64位解码、BAR首4KiB页原UEFI描述符完整64位属性和FB物理范围。只写固定232B/29u64报告，once版本护重入、done最后发布、纯固定地址getter。无PCI写/sizeBAR/控制器MMIO/设备接管/新capDMAIRQ授权。各counter保留64位，屏幕pack16bit饱和显式flag；不存在描述符时found/fields明确为零，不能误认Reserved0或真实驱动错误。

新构建工具严格校验正常命令模板、对象和来源，private graph仅增加模块+import，真实编译DG及三内核对象、kernel/IMG/两manifest消费者EFI。private entry只在现有Gate/geometry下stage24/version1/done1绘15行，最底470；private services_run在user_run前run/draw/marker后cli-hlt，明确intentional_stop。17服务不变，正常512构建输入及全部既有源保持原字节，EFI仅改USB INFO DIAG R1标识，专用usb-preflight.json不冒充正常成品。

真实module debug/release编译及ELF64/Win64四次汇编通过；Report232/align8/29字段偏移逐项正确。真实完整normal→diagnostic8命令构建/verify_preflight通过，工具SHA6eeac3e0ef12f629cbfad58f15da953b4153b2a9fa939267c794c05f9359be88，新DG SHA6613ac31daca2bf969ca877700dbd8f55f9e0b9bcebc2fe58cbec8312465de5b。产物build/hardware/usb-info-20261026-r1/builder-preflight-r1。

原生预验1test18.960s/0skip，139来源稳定；debug/release×O0/O2各115cases/404730checks，9实际坏体×2mode正常oracle rc1拒，无panic/超时。40 ELF/COFF汇编和22原生执行，实际STATE两侧32B、真实View160/rawmap/config只读和零writecallbacks/sticky均通过。证据build/test/usb-preflight/run-cc7950a2e3e2/validation-summary.json，前三次夹具错误日志保留。

root实际8CPU QEMU只读checkpoint vm-r2已通过，stage24/error0/CPU8、实际232B报告/编译器ABI/原MCFG与PCI config/BAR/QMP、完整执行代码和80164像素(15行)一致。没有进入用户态、BAR映射或新增设备权限，VM已停止，USB整体和三类内部可写盘整体SHA不变。结果SHA c835b4762a3cc2e59e16a423121c7ad661d29ccf918695bcb0048648da2b46cc。r1观察器错误假设BAR必须有UEFI描述符而拒绝，原件保留；QEMU实际高BAR位于未描述洞，r2明确验证报告found0/字段0与实际原图一致，guest没有改动。

交付时正式独立定向复验及H发布尚待完成，不提前宣称通过或已写盘。root后续在审查/集成note补结果。真机只需拍完整标题到FLAGS的15行画面，不再等待桌面；这是主动停止版，故障根因与后续修复仍待真实数据。


## AI交付 2026-10-26T14:21:11+00:00 · codex-mcp-918a30d10dd649bf

6授权新文件完成并冻结，详情codex-works/deliveries/P8USBINFO1.md。真实只读PCI扫描/29u64报告/15行主动停止版，正常源策略不变，三内核对象private overlay和EFI单banner、17服务原字节。预验1test18.960s/0skip/139源稳定、115cases404730checks×4、9坏体×2/40汇编/22native通过，旧失败保留。root完整8命令实际build/verify及8CPU vm-r2报告/MCFG/PCI/BAR/80164像素/无user及新增授权/整USB与内盘不变均PASS。正式独立复验与原H发布尚待完成，未声称真机根因或桌面已修复。

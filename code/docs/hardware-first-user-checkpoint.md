# FIRST USER R1

真机AP CHECK R1已确认8CPU激活、READY=FF、PARKED=FE、队列中有初始线程且无报告错误。该版主动停车绕过了后续AP idle；本版恢复正常AP交接/idle/BKL/调度/返回和捕获路径，定位首次真实用户入口。

入口为 `DongOS FIRST USER R1`，停止页为 `DONGOS FIRST USER`。正常源文件、CPU数、锁与期限、17服务ELF和服务bundle保持。只在私有诊断图中验证初始队列仅INIT（槽位/配置5、affinity1）后保留原屏幕view，不在正常boot阶段retire它。其他服务虽已加载且帧缓冲映射已存在，但首次INIT事件被服务之前没有启动compositor或其他可执行的帧缓冲写者。因此此诊断窗口仍可由原screen_draw/cache Gate独占重绘，不能把它推广为运行中任意时刻的屏幕日志方案。

成功钩子位于真实 `user_bridge.capture()` 中：原checked、begin_entry、25u64 GPR复制、complete_entry（含XSAVE）和原kernel_xstate恢复全部完成之后，DEADLINE/POLL/ACQUIRE及任何服务callback之前。成功路径保留已有较深栈，不重置到栈顶，避免覆盖实际SYSCALL原始Frame。此处已完成用户CR3返回/IRET及用户事件入口，又切回内核根和kernel xstate。事件可以是SYSCALL=100（十六进制256），也可以是真实用户IRQ或用户异常；reason0表示成功捕获，不表示系统调用已经执行成功。若VECTOR<20（十六进制32），仍应按真实用户异常分析。

另外只在原可信BSP `user_smp_fail` 路径记录reason1：保留原Header.last_error及metrics.failed，保存失败前raw CR3，在已映射的user_entry代码中先切回内核根，再到诊断处理程序恢复kernel xstate。该不返回路径可以重置可信内核栈；untrusted-GS和AP失败路径继续原fail-stop。reason1没有“实际异常Frame”的承诺；可用的c.returned只是准备返回帧，报告frame_kind2明确区分它。未知/尚未选择时帧字段为零。

固定192B/24u64报告只读本CPU和永久拥有的结构，EMPTY全零落BSS、once捕获、done最后发布。校验实际Header/Domain/Bridge身份、INIT槽位、captured token/incarnation、逐25u64捕获副本和根身份，xstate指针必须64字节对齐且加法不回绕。15行显示CHECK ERROR、REASON、CPU、VECTOR、OPERATION、SLOT、USER RIP、USER RSP、FRAME CR3、CPU MODE、CAPTURED、SYSCALLS、USER ENTRIES、BRIDGE STAGE、FIRST ERROR；底部470像素。Token、raw CR3、Header错误、Domain/Bridge失败和frame_kind等保存在报告供VM独立核对。

通常首入口是INIT的首个SYSCALL，SLOT=5，token低字节6，CPU=0，CPU MODE=4（完成捕获后的内核模式），CAPTURED=1，SYSCALLS及USER ENTRIES非零。不要把其他真实vector强行改为SYSCALL。FIRST ERROR优先本CPU已发布的Bridge失败，否则显示Header.last_error；它不是全系统按时间排序的首错，零值也不能掩盖vector本身表明的用户异常。AP正常运行时全局lock/owner可能短暂变化，本报告不要求它们始终是0/16。

验证必须执行实际capture native正例/错误体、debug/release/O0-O2/ELF-COFF、真实结构布局/BSS/只读输入/once/畸形指针及reason1语义，并检查准确私有hook和fail边界。Root8CPU真实VM还要核对实际INIT唯一性、Frame/CR3/GPR、xstate捕获、Header指标、Bridge调用计数0、AP未停车的原路径、服务未启动、实际代码与15行像素、整USB和三可写内盘未变。正式复验/真实审查通过后才备份更新原SanDisk H、flush/回读和native FAT32 rb检查。

请拍完整屏幕到FIRST ERROR。此页主动停留，不进入桌面，也不响应F12；若仍是S19或其他失败页，等待60秒后同样拍完整画面。该诊断不证明完整服务启动或正常桌面已经通过。

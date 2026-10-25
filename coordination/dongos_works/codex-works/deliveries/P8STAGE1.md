# P8STAGE1：ACPI 画面后的真机启动阶段

用户已确认 R4 越过 GOP 后等待一分钟仍显示 P3 ACPI READY。源码证明正常 runtime7 仅在 BSP 线程验证前绘制该页；后续中断、SMP 或服务失败不会重画，因此不将该旧标题归因为 ACPI/USB 错误。

10 个声明文件已实现并冻结。runtime7 通过原两个 Framebuffer Gate writer 显示 S01–S14、CPU 数量和首个完整64位错误值；首次原 screen_draw 成功后才 arm immutable RuntimeView，helper 保留全部15 GPR/flags/DF、不触XMM，阶段和错误宏保留调用参数/返回值。timer arm→sched_start→timer_stop 无绘制，AP/TLB/parallel 调用内部无插入。S14 后紧邻首次 SMP/legacy CPL3 调用前 disable；以后只保留 RAM/串口，不重新 arm 或绘屏。Gate 四 qword、关闭拒绝、原几何与 panic writer 保持。失败 bool 入口的零值不被当作成功；硬件、超时、USB-only 权限和原算法均不放宽。

返修后 native 证据 `build/test/boot-progress/run-0e4cd1f386f4`：O0/O2 各84场景1101断言，真实宏/helper/原renderer与字体，独立字形像素oracle、两格式、所有GPR/flags/XMM、stack、未arm/disable/Gate拒绝/poison/guard、12几何、14阶段/unknown、64位与sticky零失败。截断错误值和遗漏DISABLE两实际坏体都正常返回并被拒绝，ELF/COFF均汇编，0skip/source稳定。还新增 whole entry+两个独立TU宏调用的真实链接夹具，未修改的generic ELF reader实际接受新命名函数实现，旧跨TU私有标签实际回归体正常汇编/链接后被拒绝。Gate 原完整回归 `run-2acde1fb96c5`（六级别×ELF/COFF整对象、原生全部坏体）通过，runtime结果协议3项通过。

默认级别实际契约比较 `build/test/boot-progress/default-contract-1704bd5b730a`：用上一轮真实已验收独立workspace的四ASM作为baseline，当前0/3/4/5/6全部20组ELF ALLOC节字节、BSS大小/对齐一致，未让测试依赖固定外部目录。

最终完整正常成品 `build/hardware/usb-stage-20261025-r2/source/esp`：runtime7、USB-only、test=false，完整源图前后一致；EFI仍为DIAG R4，kernel新增阶段，服务实际源码无改动。BOOTX64.EFI 29696B SHA `cb4df70207f2a5335e7dc58a688b40696d59b0ab673c05706c94d39992583c61`；DONGOS.IMG 2003058B SHA `2a2d0c55cf444c24ccb51ebe9bcbb94d576f53b9ed95f7a61f2cb5b704559dc3`；SERVICES.BIN 33333248B SHA `a7f463b897eef1c092a137f765e06a15d1cfb43933346cc6555d4808012061bf`。现有未改 generic reader 已真实读取最终kernel.elf共29681符号。

首轮 r1 两次 normal observer 被合法跨对象 NASM 宏私有 local 名 `..@34.recorded` 重复阻断，均已停机并保留；最初判断CPU reader后，实际trace确认normal链经过generic reader。P8SYMBOL1对CPU模块的合法标签适配已独立验收集成，但不冒称解决normal链。此主任务返修把错误宏收敛为唯一TU的 `boot_progress_record_error` 命名函数，宏仅call，不产生重复标签、不改已哈希generic工具、不降低任何检查。首个private失败候选因manifest搜索目录替换而缺bootinfo_layout也保留；脚本已改private优先并保留normal的生成include fallback。

返修提交时 r2 `live-full/` 完整两boot observer和 `bad-stage3/` 受控失败均在root实际执行。normal在全部原强契约后读取真实新状态（phase14/failed0/error0/view0/cpus4）。坏guard由private entry源码 cmp1→cmp2 重链真实kernel/配套EFI，要求materialized kernel仅一字节变化，证明真实线程完成后显示S03失败+error1、不越级SMP；不写guest内存/寄存器，不冒充正常profile。最终验收note记录真实结果。

提交时实际正常与受控失败VM尚未全部完成，不能宣布整体验收或更新H。必须独立三模块0skip/source稳定、P8SYMBOL1验收集成、root实际VM结果全过且全停后，才能验收/发布。H已再次插回并核serial4C530000010320109015、原USB非系统disk2/单MBR FAT32；发布前备份当前R4全文件并刷写全读回、原卷只读FAT审计，不格式化/改分区/写内盘/Git。真机仍需用户下一屏Sxx/错误码反馈，不登记桌面/HID/PCID/WC物理验收。


## AI交付 2026-10-25T13:46:38+00:00 · codex-mcp-14619bbd432c41a6

10声明文件已完成冻结，正常runtime7 BSP阶段屏S01..14/CPU/first64biterror，沿原2 writer+Gate+几何，首次draw后arm，所有GPR/flags/DF/XMM保全，timer/smp deadline区间无hook，首次CPL3前disable且不再arm。native O0/O2各84cases1101checks，实际截断error与删DISABLE坏体被拒绝，ELF/COFF通过，Gate完整回归及runtime协议3项通过；20组非7profile ALLOC与最新R4验收baseline完全一致。完整USB-only runtime7 source build稳定，三成品SHA详delivery。首observer因合法private local符号旧parser拒绝，失败全停保留，已独立登记P8SYMBOL1适配，正常live-full-2两boot+状态14/禁用读取在进行，实际坏guard失败屏候选在准备；尚不宣告OS gate完成，未更新H。请求独立3模块0skip/source稳定复验；最终accept/publish须所有VM真实通过且全停、P8SYMBOL1先集成。


## AI交付 2026-10-25T13:57:01+00:00 · codex-mcp-14619bbd432c41a6

返修已完成并10文件冻结。错误宏逻辑收敛唯一TU命名boot_progress_record_error，macro仅call，不产生跨对象private标签重复，不改generic ELF工具或原观察合同。新actualwhole-entry+2TU链接夹具由未改reader接受新实现/实际拒绝旧宏回归体；native全84cases/1101checks O0/O2及错误截断/漏disable坏体继续pass，0skip/source稳定。Gate完整6level/ELF/COFF与runtime协议均通过，默认级别contract保持。r2完整USB-only runtime7 build源稳定，现有reader已读取最终kernel29681symbols。P8SYMBOL1独立1项0skip/17旧protocol回归并已integrated，但不当作normal链解决方案。r2 actual normal live-full两boot+状态14/disabled审计与actual private guard S03失败体同步进行，尚未完成最终gate，未写H。r1两observer和private缺include失败完整保留。请求三模块重新独立0skip/source稳定复验，必须全部实际VM通过且全停后accept/publish。

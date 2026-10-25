# 无磁盘真机中断与线程诊断

2026-10-25：用户报告另一台具体型号未知的 Intel 电脑，使用 USB DIAG R3 正常 runtime0 后已显示 `DONGOS P3 ACPI READY`。这记录了用户观察到的基本引导／CPU内存／ACPI／GOP链路到达，不代表实际中断调度、USB运行时、暖PCID或物理WC性能已经验收。

下一轮使用正常 runtime3，无块设备驱动、文件系统、桌面或键鼠入口。先保持原ACPI画面；`runtime_begin` 实际成功返回后，才设置本项独立完成字节、重新走原Framebuffer Gate与边界校验，显示 `DONGOS P3 THREADS PASS`。完成状态和标题只编入runtime3，其它runtime级别的行为保持。原线程、时钟、栈保护、GPR／XSTATE恢复及停止定时器流程不修改。

真机操作：

1. 更新本轮介质后选择 UEFI: SanDisk。EFI入口横幅仍沿用已修复的R3高地址加载器。
2. 等待初始 `DONGOS P3 ACPI READY` 转为 `DONGOS P3 THREADS PASS`；只认后者为这次中断／线程诊断完成。
3. 拍摄完整成功画面。若只停在ACPI画面、出现panic、重启或黑屏，记录最后画面，不把ACPI字样作为本轮通过。
4. 本版没有交互命令，键鼠无反应属于预期；测试结束后关机，再移除U盘。

后续顺序为限制仅授权USB存储的桌面／键鼠测试，再做USB文件读写、sync及冷启动回读。当前普通runtime7会按VirtIO／NVMe／AHCI／USB选择存储，不能直接将它当作仅访问启动U盘的版本。USB使用实机接口和设备的限制另作验证；不从启动照片推断暖PCID或WC性能门通过。

本轮独立验证：

- `tests.test_runtime_qemu_result` 与 `tests.test_framebuffer_gate` 共4项零skip，16.543秒。后者真实执行原GOP写入与Gate，且汇编所有runtime入口，保证提取式旧夹具仍可用。
- 未修改的生产runtime3观察器在独立目录执行，通过完整原字段与硬件物理观察：129ticks、65switches、两worker各64ticks、失败0；98次独立物理读、4个guard页和3个MMIO页均验证。为补旧观察器闭包限制，另冻结所有boot ASM及kernel入口／runtime文件，前后SHA一致。
- 准备介质的ESP与生产观察器的正常ESP逐文件SHA相同。另在真实5GiB EFI位置执行正常和实际删除runtime调用的坏体：正常完成字节1并显示新PASS；坏体完成字节0、原kernel fail且不显示PASS。源未变、进程退出，物理完成字节、串口、截图和结果在 `build/hardware/p3-threads-20261025-r1/`。

当前硬件仍只报告runtime0成功，新runtime3尚待用户运行。宿主和QEMU结果不代替下一轮物理结果。

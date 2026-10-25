# P8BOOTDIAG1：真机黑屏的屏幕诊断

2026-10-25。用户在另一台具体型号未知的 Intel 电脑选择首轮 H 盘 UEFI 启动后，观察到黑屏但显示器有信号。此次没有获得原始串口或可见错误，不能宣称已定位或修复实际硬件失败。

已在六个声明文件实现可独立复验的诊断能力：入口在 UART I/O 前显示 `DongOS USB DIAG R2 S00 EFI entry`，读镜像／校验／GOP／ACPI／最终退出序列前显示阶段；早期 fatal 显示原有错误码。`SCREEN: ` 前缀避免固件控制台镜像到 COM1 时，破坏原串口 exactly-once 标记。独立 MS x64 helper 使用有界 UTF-16 缓冲，正确隔离 shadow space；最终 GetMemoryMap 之前封存，EBS 重试及其后 fatal 不调用固件控制台。原严格映像检查、4 GiB 资源界限、BootInfo、内核窗口和无存储 runtime0 保持。

已完成的验证：

- 独立测试作者运行 `python -m unittest tests.test_loader_console -v`：2 项／6.200 秒／零 skip，`build/test/loader-console/run-5c9e9e40773b`。实际汇编 ELF64／COFF，O0／O2 各 937 项原生检查、143 次回调；MS ABI、callee shadow 主动覆写、守页、截断、空指针、错误返回、封存与原串口指针／次数均覆盖。三个实际坏体正常返回1而被拒绝，源码前后稳定。
- 当前源码正常 runtime0 构建 `build/hardware/bootdiag-20261025-r3/source/esp`。内核与第一次镜像逐字相同，只更新 EFI 诊断。正常、实际篡改镜像、实际删除镜像三次 QEMU 启动全部通过；分别到达原 PASS、E08、E04，原阶段／错误精确一次，进程停止、所有输入文件前后 SHA 一致。
- 实际查看正常和 E08 的 GOP 截图：正常显示原 ACPI/内存诊断；E08 屏幕显示从 S00 到 S03 及 `SCREEN: DONGOS_P1_FAIL:E08_IMAGE_HASH`。三类串口、截图、命令与结果在该目录 `qemu-*` 和 `guest-results.json`。

最终 EFI SHA-256：`972dc5a5ed7b78110cf90b1d5dec0b7eb2192d43bb1c16cd156418a1d5be4307`，DONGOS.IMG SHA-256：`3c904bb48dfac9c1c8dab1861e392a68e1323eaed9eefff036bd81bb396a4455`。

R2 客体首次因固件镜像串口导致重复标记而失败，所有失败原件保留于 `build/hardware/bootdiag-20261025-r2/`。最早首启检查的只读vvfat接法失败亦保留，不重标成功。

提交时独立协调器作业尚待排队；本交付不自行标验收或集成。真实硬件结果仍未通过；当前 U 盘在测试电脑上，开发机没有 H 盘，最终字节尚未写回介质。需要用户插回同一 SanDisk 后，核实设备身份、备份旧 EFI、替换并读回校验。无 Git 提交或推送。


## AI交付 2026-10-25T09:12:41+00:00 · codex-mcp-14619bbd432c41a6

六文件诊断实现、独立作者原生2项零skip与三类实际客体/截图验证完成。正式作业待排；真机黑屏根因未定、未宣称真机通过。U盘未插回，介质待更新。见交付P8BOOTDIAG1.md。

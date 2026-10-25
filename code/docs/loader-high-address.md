# 高地址 EFI 与低地址交接

2026-10-25，用户在另一台型号未知的 Intel 真机读到 `S00`、`DONGOS_P1_START` 和 `E01_LOADED_IMAGE_RANGE`。此代码原来同时用于 LoadedImage 协议失败和自身地址越过4 GiB，原屏幕没有实际地址，因此用户那次结果本身不足以区分两者。

已独立检查首轮与 R2 的 PE：首选 ImageBase 为 `0x140000000`（5 GiB）。实际6 GiB QEMU 用未修改的原 R2 EFI 在该地址运行并拒绝 E01，停机 RIP 为 `0x140001d73`。当前生产对象自然加载到同一5 GiB地址，完整完成原 CPU／内存／ACPI及PASS，无需伪造协议、修改客体内存或重链接固定地址。该复现支持高地址兼容性修复，仍需用户再次真机启动确认。

`loader_image_range` 现在检查非零基址、非空尺寸、范围加法不溢出，以及实际EFI入口在半开区间内。合法高地址允许继续；无效协议先显示完整 `LOADER_PROTOCOL_STATUS`。屏幕及串口新增16位十六进制 `LOADER_BASE`、`LOADER_SIZE` 和 `HANDOFF_BASE`。

新的 `boot/loader_handoff.asm` 在最终 GetMemoryMap／ExitBootServices 之前准备一页低地址 EfiLoaderCode，复制284字节位置无关的交接块并填写唯一内核目标字段。整页必须对齐、完整低于4 GiB，目标必须位于原2 MiB内核窗口。此页以固件 LoaderCode 类型进入最终内存图，现有 allocator 仅接收 Conventional 类型，不能回收该页。

退出固件后，原高地址 EFI 代码先在固件 CR3 下装载服务及trace入口参数，然后跳进低页。低页自算私有GDTR地址，切换低栈、GDT、IDT、CR4／CR3及CS，最后保持 RDI／RSI／RDX／RCX 入口契约跳至高半区内核。所有RIP引用均在交接块内，切CR3后不访问原 PE、原EFI栈或原GDT。意外早期内核返回会在低页用有界 UART 报 E14 并停机；后续私有根移除低identity映射后，不承诺低页返回地址仍可达。

本修改保留原低4 GiB bootstrap映射、BootInfo160字节、2 MiB内核、GOP完整低地址限制、哈希／解包拒绝和最终内存图阶段的固件控制台封存。它没有放宽framebuffer或其它资源限制，也没有把桌面版写盘驱动加入首次测试介质。

验证证据：

- 原生独立测试 `tests.test_loader_handoff`，2项／8.885秒／零skip，`build/test/loader-handoff/run-881d139875ff`。正常O0/O2各36,969检查，ELF64／COFF实际汇编；8个RIP目标机器解码全内闭包，边界／canary／MS ABI保持，4种实际坏源码正常返回1被拒绝。
- `build/hardware/high-loader-20261025-r2/guest-results.json`：低地址正常、高地址正常、高地址真实篡改、高地址真实缺失、原R2高地址E01，五场景通过且进程退出。三个当前高地址场景实际基址均 `0x140000000`，失败仍为原E08／E04。
- 正常低／高两次均独立读回BootInfo和最终EFI memory map，交接整页被唯一type1 LoaderCode描述符覆盖，不与type7重叠；读回实际GDT基址等于低页内地址。读取真实CR3并物理走查原EFI虚拟地址，在当前私有根中确实没有映射。

此轮仍只验证正常 runtime0 介质；没有重新运行完整runtime7服务／trace客体矩阵。服务和trace参数的保持由逐指令审查与原生结构检查约束。真实硬件阶段状态仍待用户下一次结果。

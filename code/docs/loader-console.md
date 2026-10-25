# 真机启动阶段诊断

2026-10-25，另一台具体型号未知的 Intel 电脑从首轮 runtime0 U 盘启动后，用户观察到黑屏但显示器有信号。原引导器在多项检查失败后只向 COM1 输出错误并停机；尚未定位这台机器的实际失败点，也没有登记真机验收通过。

`boot/efi_main.asm` 现在在串口初始化前通过固件文本控制台显示 `DongOS USB DIAG R2 S00 EFI entry`。普通正常构建与原串口协议共用现有严格检查，屏幕消息加 `SCREEN: ` 前缀，以便固件也将控制台镜像到 COM1 时，原串口阶段和错误行仍各出现一次。

| 最后可见提示 | 到达的检查边界 |
| --- | --- |
| S00 EFI entry | 固件已调用这份新 EFI 程序；后续错误尚未知 |
| S01 Loader address OK | 引导器完整加载范围低于 4 GiB |
| S02 Reading USB image | 开始从该 EFI 程序自己的设备打开和读取镜像 |
| S03 Checking image and unpacking | 文件读取结束，准备校验与解包 |
| S04 Checking framebuffer | 准备检查 GOP 格式、尺寸及低地址范围 |
| S05 Checking ACPI tables | GOP 检查与引导图标绘制完成，准备检查 ACPI |
| S90 Leaving UEFI | 开始最终内存图及退出固件序列；此文字本身不证明退出或内核成功 |

退出固件序列之前发生的错误会上屏原有 `DONGOS_P1_FAIL:E...` 行。E01 表示引导器范围不满足要求；E04 为镜像文件打开失败；E08 为镜像哈希拒绝；E10 为 GOP 不满足要求，其中包含整个 framebuffer 必须低于 4 GiB 的限制。具体错误仍需以本机屏幕或原始串口记录为准，不根据黑屏直接判定某一个错误。

`boot/loader_console.asm` 使用 Microsoft x64 ABI，在独立于 32 字节 shadow space 的栈缓冲区将最多 127 字节 ASCII 转成 UTF-16。空控制台、空方法、空消息和固件返回错误不改变引导决定。`loader_console_seal` 在第一次最终 GetMemoryMap 之前清除固件控制台引用。此后即使 ExitBootServices 失败并重试、进入 fatal 或内核意外返回，也不会再调用控制台；失败的 ExitBootServices 也可能已部分关闭服务。

本修改不放宽引导器／framebuffer 的 4 GiB 限制，不改变 BootInfo ABI、2 MiB 内核窗口或映像校验。首次测试介质仍使用正常 runtime0，不包含块存储、文件系统、桌面或键鼠服务；EFI 文件服务只用于读取该 U 盘上的镜像。

独立原生测试实际执行生产汇编，检查 MS ABI、回调栈与 shadow space、长度截断及保护页、空值、控制台错误、封存后无固件访问，并执行删除封存和破坏缓冲区布局的实际坏源码。客体正常、镜像篡改和镜像缺失场景另记录在 `build/hardware/bootdiag-20261025-r3/`。客体或宿主通过不替代下一轮真实硬件观察。

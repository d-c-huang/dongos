# USB 真机 E10 与 GOP 模式回退

用户提供的 R3 屏幕证明：高地址加载器已通过低跳板检查、USB 镜像已校验，失败发生于 S04 的 `E10_GOP_MODE_OR_RANGE`，尚未退出 UEFI。照片本身不能区分缺少 1080p、SetMode 失败、格式或 framebuffer 地址问题。

原桌面加载器只接受 1920×1080；实际桌面和合成器已经支持宽 800–1920、高 600–1080、宽≤stride≤2048、RGB/BGR 32 位格式。本轮只改加载器和相应探针，保留 USB-only 内核、服务、存储隔离、低跳板和最终 GetMemoryMap/ExitBootServices 流程。

`desktop_graphics_mode` 最多查询 256 项，按合法像素面积从大到小尝试，面积相同时保持固件顺序。每项 QueryMode 的非空输出均 FreePool 一次，包括返回失败而提供缓冲的情况；释放失败立即结束。每次成功 SetMode 后重新读取实际 Mode/Info，核对模式编号、结构长度、版本、格式、几何和完整 framebuffer。候选失败会继续尝试，最终也可以使用通过同一套完整检查的当前模式。

首轮候选增加诊断文案后，原来依赖偶然布局的 UTF-16 路径成为奇地址，实际 OVMF 在 S02 的 Open 中触发 `BaseLib/String.c(37)` 对齐断言；此时尚未执行 GOP。失败现场与只读 QMP 捕获保留在 `build/hardware/usb-gop-20261025-r1/`。返修为 GUID 表显式 align8、CHAR16 路径显式 align2，并用四种服务/桌面编译组合的真实 COFF 符号地址检查及实际删对齐坏体防止复发；最终链接 map 也单独检查地址。该首轮候选没有发布到 H:。

完整原始 framebuffer 必须满足已有下游契约：base≥1 MiB，size 足够覆盖 stride×height×4 且≤16 MiB，包含首尾边缘的页数≤4096，末字节<4 GiB。不能只检查可见像素、丢弃地址高位、截短固件 size，或接受 PixelBitMask/PixelBltOnly。该任务未增加高于 4 GiB 的 framebuffer 映射。

## 新诊断

引导器首行为 `DongOS USB DIAG R4 S00 EFI entry`。S04 在模式选择前后输出完整 16 位十六进制的模式总数、当前编号、framebuffer base/size；只有 Info 非空、长度足够且版本为 0 时才读取宽、高、stride、format。诊断不分配内存、不解引用 framebuffer，均在 EBS 前执行。

失败时先输出 `GOP_FAIL_REASON` 和 `GOP_FIRMWARE_STATUS`，再输出原 E10。后一个字段在 LocateProtocol 阶段是完整 EFI_STATUS，在桌面选择阶段是选择器的归一化返回值（0/1），并非最后一次 Query/Set 的原始 EFI_STATUS。原因值为十六进制：

| 值 | 检查阶段 |
| --- | --- |
| 1 | LocateProtocol 失败或没有 GOP |
| 2 | 没有完整验证通过的桌面模式，或选择器的所有权检查失败 |
| 3 | Mode 为空 |
| 4 | SizeOfInfo 太短 |
| 5 | Info 为空 |
| 6 | Info 版本不支持 |
| 7 | 像素格式不支持 |
| 8 | 宽度非法 |
| 9 | stride 非法 |
| a | 高度或像素容量计算非法 |
| b | framebuffer 容量不足 |
| c | framebuffer base 为零 |
| d | 完整 framebuffer 溢出或超出低 4 GiB |

## 验证与真机操作

任务 `codex:P8GOP1` 的独立检查为 `tests.test_display_mode`、`tests.test_loader_graphics`、`tests.test_loader_console`、`tests.test_loader_handoff`。原生探针执行实际汇编体、真实 ABI 回调与缓冲所有权；错误释放、错误排序、漏实际模式验证和漏地址上界等实际坏体必须被运行时 oracle 拒绝。ELF64 汇编通过不等同于在当前 Windows 主机执行 ELF64。

返修后的完整构建和实际 QEMU 证据保存在 `build/hardware/usb-gop-20261025-r2/`，包括原模式与受限显卡回退。固件模拟通过仍须用户在原 Intel 电脑复测；不据此登记物理桌面/HID 已通过。

重建的内核镜像与旧版逐字节相同。17 个服务的实际汇编、ELF 入口、全部 program headers 和 SHF_ALLOC 段内容也逐项相同；服务 ELF 的非加载符号元数据包含生成文件的绝对路径，因输出目录不同而改变服务包 SHA。因此新版引导器与配套服务包必须一起更新，不能保留旧包冒充相同构建；详见 `service-identity.json`。

通过复验后只更新已核对身份的原 SanDisk H:，先保存旧文件，再写入新版引导器、配套服务包和测试说明，显式刷新并从 H: 读回 SHA256。保留原内核镜像，不格式化、不改分区。更新回执保留于该目录的 `usb-publish/receipt.json`。

安全弹出后使用前几轮成功的 UEFI 设置启动。进入桌面后移动鼠标、单击 Terminal、输入 `help`；再用 F12 进入 shell 执行 `pwd`、`ls /`。如仍为 E10，请拍下 S04 前后 GOP 数字、原因和状态；如停在后续阶段，保留最后一屏。

协议依据：[UEFI 2.10 GOP](https://uefi.org/specs/UEFI/2.10/12_Protocols_Console_Support.html)、[EDK II GraphicsOutput.h](https://github.com/tianocore/edk2/blob/master/MdePkg/Include/Protocol/GraphicsOutput.h)。

# P8GOP1：真机 E10 的 GOP 回退与诊断

用户照片显示 R3 的 S01 低跳板和 IMAGE_OK 已通过，S04 报 E10。确认原 runtime7 选择器强制 1920×1080，而桌面支持 800–1920 × 600–1080；照片仍不足以判定固件具体失败分支。

## 已完成实现与源码审查

- `boot/display_mode.asm`：最多 256 模式，按合法像素面积排序，稳定同面积顺序；失败后继续次优，最终完整验证当前模式。每个非空 Query pool 释放一次，FreePool 失败终止。每次成功 Set 后重新读取实际编号/结构/格式/几何/完整 framebuffer。保留 low4G、1MiB base、16MiB raw容量及4096页缓存所有权边界。
- `boot/efi_main.asm`：R4 入口，选择前后安全输出完整64位 GOP 数值，Info 长度/指针/版本守卫；失败原因1..d及阶段返回值，不在 EBS 后调用控制台。低跳板、ACPI、最终内存图与 EBS retry 契约不变。
- 两套 native 探针执行实际生产汇编，检测 Win64 全部 NV GPR/XMM、调用栈对齐及合法 shadow 覆写，汇编 ELF64/COFF。选择器66真实场景通过；collector默认/desktop分别37/38场景，O0/O2通过。实际缺FreePool、漏post-Set、错误ranking及漏低4G guard坏体均被正常运行的 oracle 拒绝。
- 控制台/低跳板4项回归通过。源码、契约、ABI、缓冲所有权和探针有效性已实际审查；最终验收仍等独立定向复验和实际 VM。

本机 native 证据：`build/test/p8-gop/run-4a488919b73e/summary.json`、`build/test/loader-graphics/run-4179fbc58869/`，另有 root 重跑 `build/hardware/usb-gop-20261025-r1/display-root.log` 和 `loader-regression.log`。当前 Windows 只实际执行 Win64 native 对象，不声称执行 ELF64。

## 冻结构建与行为边界

首轮 r1 实际启动停在 S02，root只读QMP现场抓到 OVMF BaseLib/String.c(37) CHAR16奇地址断言。新增诊断文字使原来隐式对齐的image_path变奇地址；最终map独立确认首轮image_path=0x1400083c7且5GUID亦奇。首轮的两个WHPX、一个TCG及只读watch错误/停机记录保留，未发布H。返修添加GUID前align8和路径前align2，四编译组合的实际COFF符号测试均过，删除对齐的4实际坏体均汇编成功但被oracle拒绝。完整native诊断/ABI回归重跑通过，证据 `build/test/loader-graphics/coff-bd3a9d1018b9` 和 `run-c544742d1ca9`，0skip/source稳定。

返修后新隔离完整构建 `build/hardware/usb-gop-20261025-r2/source/esp`，runtime7、usb_only=true、test=false，完整源图 before/after稳定。最终map GUID地址0x140008378/388/398/3a8/3b8、image_path=0x1400083c8，sb_path=0x140008660/sb_file_info_guid=0x14000867c均满足各自自然对齐。主源图仅两份 boot ASM 改变。内核 SHA 与旧R6逐字节相同；17服务实际汇编、ELF入口、program headers、所有 SHF_ALLOC 内容逐项一致（`service-identity.json`）。非加载符号元数据的绝对生成路径改变 ELF/SERVICES.BIN SHA，故需配套发布新服务包，不能把旧服务包配新引导器。

- BOOTX64.EFI：29696字节，SHA256 `ef523ac810db866f1df95983c4e5bdaf3ead54b3ed5cde6cc94c3265e1940874`。
- DONGOS.IMG：2003058字节，SHA256 `b263a40326c553762e86aa83d0ca8008909838b6b9b339453148cba94067cef0`。
- SERVICES.BIN：33333248字节，SHA256 `0402983df59e488e04b0dd18e11dd619902890dc7234306cb1a3c737af134c88`。

返修提交时 r2 的实际1080模式USB-only两启动混合内盘/HID/写入持久性 gate 和 Cirrus受限显卡真实 fallback 均在运行，不能据此宣告整体通过。最终证据固定在同目录 `live-full-1080/result.json`、`fallback/result.json`，验收 note 必须记录真实结果、清理和限制，不覆盖失败历史。四模块返修独立复验须重新完成7项（选择器1、GOP collector/COFF2、console2、handoff2），首轮6项通过不能代替返修复验。

H 已重新插回；fresh核对原 SanDisk Cruzer Blade、serial 4C530000010320109015、disk2、7798784000B、USB非系统盘、单MBR FAT32起始131072B，现有三成品与旧R6 SHA吻合。验收通过后才备份和更新引导器/配套服务包/说明、显式flush/fsync及全读回；不格式化、不改分区、不写内盘、不Git。发布回执 `usb-publish/receipt.json`。本次实际 Intel 机器的桌面/HID结果仍待用户重启后确认，不作物理 PCID/WC 验收。


## AI交付 2026-10-25T12:52:46+00:00 · codex-mcp-14619bbd432c41a6

声明8文件已完成并冻结：有界GOP面积排序/失败回退/真实post-Set及完整framebuffer验证，R4前后模式与失败原因诊断，actualnative ABI/ownership/坏体探针及文档。native选择器66case、collector两profile37/38case O0/O2、控制台低跳板4项通过；ELF64/COFF均汇编，Windows实际执行Win64。完整USB-only runtime7构建源稳定，两ASM之外kernel/服务源码不变，kernel字节相同、17服务汇编和ALLOC段一致，路径符号元数据导致服务包hash变需配套发布。实际1080两boot mixed USB/HID/FS gate进行中，cirrus受限fallback尚待root执行；最终真实VM结果必须通过并全部停止后方能accept/publish。H已核原SanDisk和旧hash，尚未写U盘。请求4模块独立复验0skip/source稳定；无Git。


## AI交付 2026-10-25T13:05:51+00:00 · codex-mcp-14619bbd432c41a6

返修已完成且声明8文件重新冻结。r1实际UEFIwatch确认CHAR16路径奇地址断言，显式GUID align8/path align2修复；新增四种真实whole-EFI COFF配置+实际移除对齐坏体，所有正常地址与字符串bytes核对通过，坏体均正常汇编后被oracle拒绝。collector native O0/O2+ABI/ownership/低4G坏体仍通过。r2完整USB-only runtime7重建 source_stable=true，最终PE/map所有GUID/路径实际对齐核对；kernel旧R6字节一致，17服务实际ASM/PHDR/ALLOC内容一致。r2实际VM均已越过S02/GOP进入桌面：1080主gate正在HID与写入持久性，Cirrus800x600已clientsready+sync，最终强审计与停机仍待完成，未据此宣告整体验收/未写H。请求重新独立4模块7项0skip/source稳定复验。所有r1失败历史保留，无Git。

# S19 后的 BSP 用户态隔离诊断

最新 Intel 8 CPU 真机照片为 `S19 USER DOMAIN LOCK`、STAGE=0x13、FIRST ERROR=0，等待超过两分钟仍没有桌面。它证明 PCI 预发现、用户域/CPU 头准备和 BSP 激活已经返回。S19 是正常路径最后一次绘屏；S20–S23 只记录 RAM，随后永久退休 view。因此画面不能定位为域锁死锁，也不能证明后续错误为零。

本诊断沿已有 `P6_USER_SMP=0` 编译选项，仅对照测试原 BSP 用户态路径。8 CPU 的平台、自检和原内核 AP 保留；CPL3 程序由 BSP 调度。正常 runtime7 多核策略、内核和服务生产源码、USB-only 存储权限、DMA/BAR/Runtime 门禁及原期限不修改。

## 构建与识别

`python -m tools.build_bsp_diagnostic --normal-source NORMAL --normal-build-log BUILD_LOG --output NEW_DIRECTORY` 从已完成且仍通过完整来源校验的正常 USB-only 镜像生成新诊断目录。日志只用于校验已知命令结构，实际执行由受检模板生成；不通过 shell 执行任意日志文本。

只将 `services_run.o` 的既有选择器从1改为0，再真实链接内核、打包 IMG。私有 EFI 源码仅替换入口 banner 为 `DongOS BSP DIAG R1 USER SMP OFF`；两个 manifest 消费者重新汇编，保留实际 IMG 的大小、入口和 SHA 绑定。原17服务 ELF、SERVICES.BIN、正常对象及来源保持原字节。没有固件地图或人为错误注入。

产物使用专门的 `bsp-diagnostic.json` 与 `verify_diagnostic(esp)`，不复制正常 `build-inputs.json`，也不作为普通多核成品冒充通过 `verify_build`。输出必须是新的普通目录，不能覆盖正常构建或设备路径；生成和验证检查全部对象、来源、唯一选择器和 banner 改动、IMG/EFI 绑定及前后输入哈希。

## 真机操作与结果含义

启动后先确认入口显示 `BSP DIAG R1 USER SMP OFF`。这版走原 BSP 用户态入口，最后启动画面可能是 **S14 CPL3 START**；这是隔离模式的识别信息，不代表原 S15 兼容修复丢失。

若进入桌面，检查有线 USB 鼠标移动和点击、Terminal 键盘输入，以及在本测试 U 盘中新建文件、保存、读取和 sync。若没有桌面，等待约60秒，按一次 F12，记录画面是否变化并拍摄完整屏幕。

隔离版成功只能说明共用硬件、USB/文件和桌面路径可以在 BSP 模式运行，将范围缩小到用户态多核入口、同步及相关差异；它不证明某个具体 AP、锁或指令是根因，也不等于正常多核故障已修复。隔离版失败则继续检查共用路径，不能仅凭停留画面认定域锁问题。

## 验证边界

构建工具的便携复验使用真实生产汇编体和实际 NASM/ELF/EFI 链接，明确的最小 synthetic provider 仅用于构建流水线测试，不作为完整 OS 证据。根协调器另对真实正常成品执行8 CPU桌面检查，并对真实诊断成品执行8 CPU完整单 USB、键鼠、文件、内核/服务代码及旧 AP 状态检查；内部三类可写哨兵盘逐字节哈希保持不变。正式结果和限制以任务审查记录为准。

通过后仅备份更新原 SanDisk H: 的诊断文件，flush/fsync、完整 SHA 读回和只读 FAT32 检查；不格式化、不改分区、不写内盘。此次真机隔离结果仍待用户反馈。

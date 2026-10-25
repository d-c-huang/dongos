# 仅使用 U 盘的桌面与 USB 键鼠测试

本轮承接用户报告的 `DONGOS P3 THREADS PASS`。目标是正常 runtime7 桌面；真机桌面和输入结果仍须由用户启动后确认，不代表 P2 warm PCID 或物理 WC 验收完成。

## 存储范围

必须用显式 `--usb-only --runtime-level 7` 构建。同一份带完整 SHA 的 services 快照同时供内核和全部 CPL3 程序使用，`lib.hardware_profile.USB_ONLY=true`。默认构建保持原策略。成品打包时重新核对原 services 源图、快照源图和成品 SHA，普通成品不能靠标志重新标记为 USB 版。

USB 模式在共享策略、内核 admit/grant 以及 block 初始化三处阻止 PCI BLOCK。没有 NVMe、AHCI、VirtIO block 的 BAR、DMA 或绑定；USB 失败即停止，不回退内盘。固件在启动前的磁盘行为属于固件，内核策略自 DongOS 接管后生效。

测试范围是一个直接连接的 USB BOT 512 字节扇区存储设备、USB 有线键盘和鼠标。当前驱动只覆盖首个受支持 xHCI 上的有界直接根端口设备；本轮不要连接其它 USB 存储或使用扩展坞。遇到多个健康存储设备会拒绝启动存储代理。

USB 可使用原 FAT32 superfloppy，或唯一一个有效 MBR FAT32/EFI 分区。分区层保留原 USB 代理的身份、epoch、完成数及原始介质容量检查；只在 READ/WRITE 中将相对 LBA 转为物理 LBA，并单独向文件系统报告逻辑容量。GPT、扩展分区、多分区或越界布局不在本轮范围。

## FAT32 挂载

USB 模式将审计 bitmap 从默认 32 KiB 扩为 2 MiB，保留 FAT 双副本、目录树、交叉链、循环和孤儿簇审计。该 bitmap 不是跳过检查的阈值放宽；上限依然检查，使用高位簇的真实坏体探针须失败。

Windows FAT32 备份 FSInfo 中的 free/next advisory hints 可以比主副本旧。USB 模式分别验证两组 hints 的范围，只允许字节 488–495 不同，其余 504 字节仍要求相同，保留签名及保留字节检查。分配仍以 FAT 审计为准，不使用 hints 授权。依据：[Microsoft FAT32 v1.03 原始规范，BPB_FSInfo](https://cscie92.dce.harvard.edu/fall2025/Microsoft%20Extensible%20Firmware%20Initiative%20FAT32%20File%20System%20Specification%2C%20Version%201.03%2C%2020001206.pdf)。默认模式保留原严格行为。

原 H 盘是 SanDisk Cruzer Blade，序列号 `4C530000010320109015`，7,798,784,000 字节，USB 非系统盘。原 MBR 分区起始 256 扇区，逻辑容量 15,231,744 扇区，每簇 8 扇区，1,899,872 簇。只读 native 原卷挂载已完成全部审计：45,114 次读，0 次写，0 次刷新。原分区和文件系统无需重新格式化。

仅 USB 专用版的文件系统启动审计预算为60秒，其他服务及默认版本仍为10秒。预算由可信内核配置固定，先检查时钟乘法上界；没有用户可调参数，也不改变磁盘、TLB或输入检查。先前10秒版本在持续读取审计期间被反复终止，失败记录保留；增加这项有界I/O预算用于完成同一份审计。

## 启动测试

完成候选验真、模拟完整桌面与 HID 复验、独立定向复验后，才更新 H 盘。更新前重新核对设备身份和旧引导文件 SHA，将被替换文件备份到本地；仅复制引导器、内核、服务包和测试说明，每个文件显式刷新并从 H 盘读回 SHA。不得格式化或写内置硬盘。

1. 在 Windows 安全弹出 U 盘，插到测试电脑。只保留测试 U 盘及直接连接的有线 USB 键盘、鼠标。
2. 通过固件启动菜单选择 UEFI SanDisk 项；使用前几轮成功的固件设置。
3. 等待桌面。先移动鼠标、单击 Terminal 窗口，输入 `help` 并回车；观察光标、单击和字符是否各出现一次。F12 切换控制台后可输入 `pwd`，再次 F12 返回桌面。
4. 桌面出现且键鼠正常后，再尝试在 U 盘中创建测试文本、保存及重新打开。正常关机/同步后再断电，避免 FAT32 脏卷。
5. 若停住，记录最后一行屏幕文字和 USB 键鼠指示灯反应。不要在其它系统弹出的格式化提示中格式化 U 盘。

模拟验证使用普通镜像文件：同一 MBR USB 同时启动 EFI 和承载 FAT，键鼠占另两个根端口，并实际连接可写 NVMe、AHCI、VirtIO 三个哨兵镜像。必须证明完整内盘 SHA 不变、真实 GUI 消费 HID、文件写入及 FLUSH、重启读回和启动 payload 保持；host 自测或单独枚举不能替代这些结果。

WHPX 的本轮验证使用 `tests/run_usb_only_hardware_qemu.py --live-capture`：运行阶段不发送 QMP stop，完成真实输入、文件操作和最后 sync 后仅停止一次，随后只读取状态且禁止恢复。旧观察器在持有 BKL 或 AP 等锁时长时间暂停，消耗了真实时钟期限；首失败记录为 BSP SERVICE_AFTER 的 Held 与 AP ACQUIRE 的 Timeout，USB 完成事件实际仍在环中。相同 R6 镜像的无暂停对照已完成鼠标报告及 F12/pwd 消费，故保留旧失败而修正取证流程，不修改 SMP 安全检查或超时。

最终冻结检查保留 ELF、用户池、页表与 DMA 隔离、逻辑卷容量和真实 CBW/CSW FLUSH，并检查所有 Bridge 首失败记录和四 CPU metrics.failed 为零。PCID 状态由实际每 CPU 的 SMP Header/CR3/CR4/进程身份读取，不能使用旧单 CPU globals；这些正常运行检查不构成独立的 P2 warm PCID 验收。

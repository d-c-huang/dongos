# P678USBBAS2 正常 USB 镜像复验

冻结当前生产来源构建正常 runtime7 USB-only 镜像，未使用 startup-console overlay。构建输入 SHA256 为 `4c5d88afcf53aeff15526a49c08b7272ded4ef43f5099a1fcfacc8712af9564b`。冻结脚本漏拷默认的 `kernel/build/storage_profile.dg`；runtime7 使用构建器生成的 storage profile 覆盖文件。本轮结果只归属于归档清单中的确切镜像。

实际四核 QEMU TCG 启动到桌面，收到键鼠 HID 事件，创建长名目录成功。长文件写入命令完整回显后未在既定时限内返回，第一轮失败，未执行第二次启动。三块虚拟内部盘的完整 SHA 前后一致，实际 QEMU 已退出。运行器宿主自测 5 项、USB 启动预算 1 项通过。

失败冻结数据中，CPU1 在 Bridge stage 5（ACQUIRE）记录 `0x06090005`（Domain.Timeout），owner=0、lock=1。BSP 在 stage 13 记录 `0x06090004`（Held），记录时刻稍晚。此时 xHCI 仍为 ready=1、fault=0，最后 BOT 状态为 0。证据把本次停止定位到 BKL 超时传播；尚未区分排队饥饿、长临界区和宿主调度延迟。已把 FIFO Bridge 候选发布为 `cursor:P6BKLBRIDGE1`。

- [完整运行结果](../../../../code/build/test/p678-usb-baseline/run-8fbbc5ada1d4/guest/result.json)
- [故障冻结快照](../../../../code/build/test/p678-usb-baseline/run-8fbbc5ada1d4/guest/boot-1/failure.json)
- [客体 UART](../../../../code/build/test/p678-usb-baseline/run-8fbbc5ada1d4/guest/boot-1/serial.log)

完整桌面输入及双启动持久化仍待复测。P6 原 KVM 时限和 P8 实机覆盖仍有各自验收项。


## AI交付 2026-11-05T12:39:05+00:00 · codex-mcp-50488d53a0084e80

正常runtime7 USB-only冻结镜像构建成功，runner 5项自测及启动预算1项通过。真实4核TCG进入桌面、键鼠HID和MKDIR；写长文件无响应，未执行第二次启动，三虚拟内盘SHA稳定，QEMU已停止。原始快照CPU1 ACQUIRE stage5 Domain.Timeout 0x06090005，BSP后续stage13 Held；xHCI ready=1/fault=0。已留档并发布P6BKLBRIDGE1候选，完整客体门失败，保留待复测。冻结拷贝缺默认storage_profile.dg，实际runtime7使用归档生成覆盖。

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


## AI交付 2026-11-06T06:49:04+00:00 · codex-mcp-e30a159488a44d74

2026-11-06 FIFO Bridge生产迁移后的全新正常USB完整构建与客体复验。冻结完整1729文件含kernel/build/storage_profile.dg，source-manifest-lf SHA bc0c8a847dec3fe9569ae9d6900a6144944aab9ad7a54f0e81cd98c17300021e，build-inputs SHA e5e8039b3cc052f134ae7f4180a1bdb6183d720484c47e457c6163e75805b1a4；独立逐项源/产物审计通过。普通runtime7 USB-only、4CPU TCG、无console overlay、原期限。runner自测5项、预算宿主1项通过。客体到xHCI/HID/block/FS/shell/desktop与两GUI_APP_READY，但cfg15/17启动Timeout0x05110007，被退休到state5，未出现P7_CLIENTS_READY，完整门失败、未执行HID/长文件/第二启动。冻结Bridge FAILURES全部448Q为0，四CPU progress仍正常；本次没有观察到旧BKL held，但不证明旧长文件问题已修复。QEMU已退出，原始失败位于code/build/test/p6-bkl-integration/run-20261106/usb-guest/result.json及boot-1/failure.json/serial.log。原2026-11-05失败记录完整保留；继续返修启动性能/完整桌面门，不验收阶段。


## AI交付 2026-11-06T07:28:55+00:00 · codex-mcp-e30a159488a44d74

2026-11-06追加真实旧Bridge A/B：相同冻结源码、QEMU/匹配固件、4CPU TCG和原runner/期限，仅kernel/sched/user_bridge.dg替换Git HEAD旧版eb25e153ab4462b70b45a568b6dee8144921faed0151e103c4a42da6963ff6d4；完整重新构建成功。usb-baseline/build/usb/build-inputs绑定SHA c0e9b961ef3fa487ed2a11c070b7f7f635208c8dfa7fb31a8b67a806c0690d9f。实际运行code/build/test/p6-bkl-integration/run-20261106/usb-baseline-guest/result.json仍files cfg15/settings cfg17 Timeout05110007，terminal/editor READY，未到P7_CLIENTS_READY/HID/文件/第二启动。新旧Bridge均448失败字段零；独立审查全部来源/7产物及六个64MiB保护虚盘完整SHA，前后均一致，所有客体已退出清理。A/B不支持将启动超时单独归因FIFO，但不证明FIFO无时序影响，更不关闭原长文件门。已发布cursor:P7STARTTRACE1先做只读超时前trace，定位真实初始化阶段；源码提示LIST重复扫描但小根目录下不能断言根因。宿主selftest5项和startup_budget1项此前本轮通过，A/B追加仅真实构建/运行与独立只读审查，无新宿主代码。旧失败、原P8BOOTCONSOLE1返修保持。

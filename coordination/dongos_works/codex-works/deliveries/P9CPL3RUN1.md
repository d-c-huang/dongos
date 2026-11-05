# P9CPL3RUN1 真实用户态语料运行

以冻结的正常 runtime7 ESP 启动四核 QEMU TCG。临时 FAT 数据盘预置真实语料构建的 `APP.ELF`，由既有 Shell `exec /APP.ELF` 加载。没有生产启动清单改动或客体内存和寄存器写入。

实测 token 268、Catalog generation 1、物理 slot 11。只读页表与物理转储确认已加载的不可写 ELF 段及其语料数据逐字匹配。实际内核捕获的用户 syscall 帧中，root 为 `0x74c52000`，保存的返回 RIP 为 `0x103733a1`，syscall 计数为 451，RIP 前两字节为归档映射中的 `0f05`。同一 token 和 generation 的 Shell WAIT 与 Catalog 终态均报告退出 0。

外部 UART 取得 258 条 P9LOG1 记录、20704 字节，包含全部 256 个逐例返回和终态。语料代际为 `11333830771346569718`，捕获 SHA256 为 `6b2c63d11389ba9532a66bdab560f7ad401989069ad2b09dbb631549a44e49d4`。重新从归档完整 UART 拆出同一字节串并通过严格验证。仅改第一例的一个实际返回位，验证以 `raw return mismatch at case 0` 拒绝。临时 FAT 数据盘哈希保持一致，QEMU 退出码为 0。

采集器按真实串口的原子 P9LOG1 写入还原 Shell 的拆分字段，分别检查完整回执和控制台进程身份。保留先前失败，包括旧 ESP 源图不符、过早采样、串口交错，以及无法从低频瞬时 CPU 寄存器采样命中短用户态窗口。最终改为读取生产内核实际保存的用户帧。已有宿主传输验证 API 的证明范围保持原合同，客体运行依据在 QEMU、页表和进程回执中另列。

- [最终运行结果](../../../../code/build/test/p9-cpl3-corpus/run-7ea8ba4067ee/guest-r8/result.json)
- [外部 UART 原始记录](../../../../code/build/test/p9-cpl3-corpus/run-7ea8ba4067ee/guest-r8/boot/serial.log)
- [严格语料回执](../../../../code/build/test/p9-cpl3-corpus/run-7ea8ba4067ee/guest-r8/p9.log)
- [归档语料构建](../../../../code/build/test/p9-cpl3-corpus/run-7ea8ba4067ee/corpus-r8/transport-manifest.json)

范围为已有 256 个无实时端点前置的确定性用例。IPC live endpoint、持续泄漏监测、24 小时门禁和硬件安全功能仍有各自的验收任务。


## AI交付 2026-11-05T12:54:59+00:00 · codex-mcp-50488d53a0084e80

真实四核QEMU TCG normal runtime7，以Shell EXEC运行归档ELF，物理PTE/不可写段和内核捕获用户SYSCALL帧匹配。token 268 generation 1 slot 11，真实WAIT/Catalog退出0。外部UART完整258记录/20704B，256例全部与既有oracle一致，原始UART重提取复算通过，改单例实际返回被语义拒绝。QEMU退出0、临时盘SHA不变。宿主观察器/原生传输5项零skip通过。交付保留早期失败、隔离源与完整原始证据；本项仅已有无实时端点前置语料，不关闭P9长期或硬件验收。

# P5RETIREGUEST1 客体观察交付

复用 P5CTX2 的只读物理转储与离线重放，新增显式 `--dma-retirement` 模式。正常对照要求准备位和续接状态为零，逐页确认原 DMA 用户映射。故障观察绑定旧 owner/incarnation、根、内存代际和完整租约，读取生产续接和退休回执，逐页检查旧 PTE 已撤销，并核对新退休序号、在线 CPU 集合及各 CPU 请求和确认。终态失败会保留实际错误和已取得的原始回执。

宿主定向 `python -B -m unittest tests.test_p5_recovery_context_guest tests.test_virtio_reset_guest -v` 实测 23 项通过，零跳过。旧 P5CTX2 的两份原始档案用新版观察器完整离线重放通过，仍报告原 context/reset/hold 范围。另用旧审查的刻意篡改档案确认 drain 伪造继续被语义校验拒绝。

冻结副本与运行证据位于 `code/build/test/p5-retire-guest/run-9fd1e53f3882`。首轮普通构建入口在独立副本缺少默认 `build/p1` 输出目录，失败日志保留；重跑使用显式独立输出目录。

两份正常 runtime7 构建均成功。除故障清单外，两份冻结输入的唯一差异为 `services/drivers/block_service.dg` 中既有的精确 UD2 注入。两次 QEMU TCG 使用四核、各自的临时数据盘及固件变量副本；各留存两次只读快照，源码及临时数据盘前后 SHA 相同，QEMU 都退出 0。

|组别|真实观察|原始档案|
|---|---|---|
|正常|两次均存在 32 页原映射；未尝试准备、续接状态 0|[结果](../../../../code/build/test/p5-retire-guest/run-9fd1e53f3882/control/build/test/p5-reset-guest/run-a6151bc589c24013b248044aceaefd35/result.json)，812 个物理转储|
|UD2|续接 state 2、stage 3；退休回执 state 3、32/32 页已撤销、online 0x0f、sequence 180→181；两次均无旧 PTE。四核 ACK 分别为 188 和 266，均达到退休序号。原租约仍 PINNED，held=1，drain=UNKNOWN|[结果](../../../../code/build/test/p5-retire-guest/run-9fd1e53f3882/fault/build/test/p5-reset-guest/run-895d30d7d7ab4998b6091cb20cdf4781/result.json)，844 个物理转储|

两组完整原始字节档案均以 `--dma-retirement --replay` 同一校验入口离线重放通过。复制故障档案，将第二次原始回执的 after 改成 before，随后同步转储 SHA、清单 SHA 和保存的 decoded view，完整重放仍以 `missing fresh post-unmap sequence` 拒绝。原始两组档案保持原样。

本次观察范围是 CPU 侧退休。设备在途 DMA 排空、第三方 owner 排除、物理回收、重新授权和驱动恢复仍需另行证明。


## AI交付 2026-11-05T12:05:30+00:00 · codex-mcp-50488d53a0084e80

P5RETIREGUEST1 实现可选真实客体后撤映射证据及离线重放，兼容 P5CTX2 旧档案。宿主23项零skip；冻结同源完整 runtime7 控制/故障均实际四核QEMU TCG通过并退出0，唯一源码差异为现有UD2注入。正常两次32页映射仍在，故障两次0页旧PTE，view 32/32、online=0x0f、180→181、全部ACK覆盖，PINNED/held/UNKNOWN保持。两组原始物理档案完整重放通过，实际重哈希旧序号负控被语义拒绝。交付保留首轮输出目录失败、构建来源、结果与边界。后续独立正式宿主复验和审查；无DMA排空/第三方owner排除/回收/重启证据。

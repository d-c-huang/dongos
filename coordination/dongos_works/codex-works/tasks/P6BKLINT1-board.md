# P6BKLINT1 — [P2/P5/P6/P7/P8] 已审查FIFO Bridge生产迁移与回归

负责人：codex。状态：待领取。

按用户继续研发/审查后集成授权，将已独立审查与正式复验的P6BKLBRIDGE1完整Bridge逐字迁移生产。迁移测试读取当前生产Bridge并保持18实际正常/坏体，保留baseline及指纹。正式复验实际entry/barrier/failure/P5调用和guest解码；独立审查迁移与范围。候选integrated只登记真实文件迁移，不代表运行门关闭。协调者在独立冻结源码、临时虚盘和匹配固件运行正常USB及P5控制/故障客体；USB用P678USBBAS2原任务记录。不延长锁期限、不改变fail-closed，不触碰物理盘。客体失败保留证据并分拆真实阻断，不伪报阶段完成。

## 可修改文件

- `kernel/sched/user_bridge.dg`
- `tests/test_p6_bkl_bridge.py`
- `docs/p6-bkl-bridge.md`
- `codex-works/deliveries/P6BKLINT1.md`
- `codex-works/reviews/P6BKLINT1.md`

## 定向验收

- `module:tests.test_p6_bkl_bridge`
- `module:tests.test_user_smp_entry`
- `module:tests.test_user_smp_barrier`
- `module:tests.test_user_smp_failure`
- `module:tests.test_p5_dma_retire`
- `module:tests.test_p5_dma_call`
- `module:tests.test_p5_recovery_context_guest`
- `module:tests.test_virtio_reset_guest`

交付：`codex-works/deliveries/P6BKLINT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

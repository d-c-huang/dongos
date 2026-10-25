# G6WAIT2 — [L3阻塞修复] VirtIO显式有界时间等待入口与真实FLUSH验证

负责人：codex。状态：待领取。

保留共享Ops/State/Lease ABI，新增显式timed read/write/flush入口接Now回调，block_service接现有milliseconds，旧轮询API及tablet语义保持。timed路径发布前取时，使用与AHCI/NVMe相同5000ms命令截止，在期限内完整used/status才成功；时钟错误/倒退/连续100000次不进展有界拒绝；迟到不得清fault，失败后DMA held直至真实reset。真实C模型覆盖超过100000poll但deadline内完成、恰到/超过deadline、clock失败/倒退/冻结、late completion和无发布失败原子性，保留原13场景及真坏体，新增deadline绕过/旧计数截断真坏体。新API不改FLUSH/cache，不扩大G6总3600秒或P2期限。debug/release两格式独立0skip/source stable后集成，再由G6RUN2新构建真实双启。旧G6两次编译成功但FLUSH Timeout，700文件raw审计各通过，历史失败不改。

## 可修改文件

- `services/drivers/virtio_blk.dg`
- `services/drivers/block_service.dg`
- `tests/virtio_blk_probe.dg`
- `tests/virtio_blk_probe.c`
- `tests/test_virtio_blk.py`
- `docs/virtio-blk-deadline.md`
- `codex-works/deliveries/G6WAIT2.md`

## 定向验收

- `module:tests.test_virtio_blk`

交付：`codex-works/deliveries/G6WAIT2.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

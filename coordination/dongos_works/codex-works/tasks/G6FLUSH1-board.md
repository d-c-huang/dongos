# G6FLUSH1 — [L3阻塞修复] VirtIO完成等待使用真实单调截止时间并保留DMA失败持有

负责人：codex。状态：待领取。

G6RUN2当前源码TCG实际两次seed均编译RESULT0/3/0/0成功但VirtIO FLUSH固定100000次轮询耗尽，两个700文件原始审计保留。原轮询次数不代表时间。参照现有AHCI/NVMe 5000ms命令契约，为VirtIO Ops增加单调milliseconds回调，block_service接现有milliseconds。发布前获得时间；完成只能在同一5000ms截止前接受，回调错误/倒退/无进展时有界拒绝；真实时限超时必须永久fault/held且不提前release，不扩大G6总3600s或P2屏障期限。不修改真实FLUSH命令或cache/no-flush配置。保留State/Lease布局，显式更新Ops ABI与所有调用方/探针；13旧场景及两个实际坏体保持，增加超过旧100000poll但在deadline内完成、deadline边界/迟到/clock错误/倒退/冻结、late completion不得清fault等真实C设备模型和生产坏体。debug/release ELF/COFF、原driver测试独立零skip源码稳定后集成，再由G6RUN2新构建实际两启，不沿用旧镜像。

## 可修改文件

- `services/drivers/virtio_blk.dg`
- `services/drivers/block_service.dg`
- `tests/virtio_blk_probe.c`
- `tests/test_virtio_blk.py`
- `docs/virtio-blk-deadline.md`
- `codex-works/deliveries/G6FLUSH1.md`

## 定向验收

- `module:tests.test_virtio_blk`

交付：`codex-works/deliveries/G6FLUSH1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

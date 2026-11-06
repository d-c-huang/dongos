# P5SOURCEBIND1 — [P5] 故障夹具保留kernel/build真实源码并完整绑定重放

负责人：codex。状态：待领取。

新BKL同源control/fault真实客体均通过，离线重放均正确拒绝build sources differ：旧fixture.hashes/prepare按任意层级build目录排除，漏掉真实kernel/build/storage_profile.dg。只排除源码根的输出build，保留嵌套真实build源码；prepare/哈希/符号链接检查规则一致。补真实目录副本/哈希及篡改负控，严禁放宽replay build-source匹配或补改旧失败档案。独立审查正式复验后，协调者可在同一已绑定机器码/构建输入上仅更新测试观察器，另建新control/fault运行档案并完整重放；记录观察器变更与原失败，新输入清单必须一致，不谎称旧档案通过。不修改内核或运行期限。

## 可修改文件

- `tests/p5_virtio_reset_fixture.py`
- `tests/test_virtio_reset_guest.py`
- `codex-works/deliveries/P5SOURCEBIND1.md`

## 定向验收

- `module:tests.test_virtio_reset_guest`
- `module:tests.test_p5_recovery_context_guest`

交付：`codex-works/deliveries/P5SOURCEBIND1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

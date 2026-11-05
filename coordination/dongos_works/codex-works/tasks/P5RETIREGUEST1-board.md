# P5RETIREGUEST1 — [P5] 同源客体故障与撤映射后的全核退休回执

负责人：codex。状态：待领取。

接续现有P5CTX2真实客体runner和P5DMACALL1生产集成，不修改内核、生产固件或故障注入。新增显式退休观察模式，兼容旧P5CTX2档案。用只读QMP和冻结构建在同源runtime7现代VirtIO正常/实际UD2故障中核对精确Context/lease/PINNED、DmaContinuation、DmaRetirementView的完整ABI与终态、所有旧DMA用户PTE和撤映射后新全核确认；正常对照要求原映射仍存在。按原始转储离线重放，宿主负控需拒绝旧/缺ACK、残留PTE、替换身份/回执及损坏布局；状态3回执永久保留真实错误，不当通过。执行方仅宿主验证；如本机工具链就绪由Codex协调者在独立冻结副本用临时虚盘/匹配固件执行control和fault，保留原始命令、来源、结果与故障，不接触物理设备。正式检查与真实证据均通过才可验收。本项只证明CPU侧映射退休，不授予设备DMA排空、第三方owner排除、解PIN/回收/重用/重绑定或驱动恢复。

## 可修改文件

- `tests/run_virtio_reset_qemu.py`
- `tests/p5_recovery_context_guest.py`
- `tests/test_p5_recovery_context_guest.py`
- `codex-works/deliveries/P5RETIREGUEST1.md`

## 定向验收

- `module:tests.test_p5_recovery_context_guest`
- `module:tests.test_virtio_reset_guest`

交付：`codex-works/deliveries/P5RETIREGUEST1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

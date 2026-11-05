# P5RECBOUND1 — [P5] 修复设备恢复事务输出跨度与别名校验缺口

负责人：codex。状态：待领取。

继续各阶段研发的P5前置修复：实际审查发现既有device_recovery.plan_ok先乘steps.len*16而未预检溢出，word_and_plan_ok漏查out_token与written的重叠，可能panic/跨度回绕或成功时覆盖计数。仅修真实生产模块这两个输入门，不重写已验收离线恢复状态机，不新增release/unpin/drain能力。新增实际Dong debug/release原生边界与失败原子性回归、零/最大/回绕长度、完整声明区间别名、reclaim/reauthorize输出重叠及相邻合法输出；用真实坏体验证断言有效，panic/崩溃不能算期望的拒绝。保留原随机模型、全状态转换及8类坏体。协调器执行宿主定向测试并绑定稳定来源；交付明确没有OS/VM/真机验证，不将此修复当作P5安全回收闭环或整阶段完成。不提交推送。

## 可修改文件

- `kernel/user/device_recovery.dg`
- `tests/test_device_recovery.py`
- `docs/device-recovery.md`
- `codex-works/deliveries/P5RECBOUND1.md`

## 定向验收

- `module:tests.test_device_recovery`
- `module:tests.test_dma_release`

交付：`codex-works/deliveries/P5RECBOUND1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

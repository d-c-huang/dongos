# P6BKLBRIDGE1 — [P2/P6/P7/P8] FIFO BKL 接入实际 Bridge 的候选

负责人：cursor。状态：待领取。

正常USB镜像进入桌面、真实HID、MKDIR，长文件写入时CPU1在stage5记录Domain.Timeout 0x06090005，BSP随后stage13 Held；证据code/build/test/p678-usb-baseline/run-8fbbc5ada1d4/guest/boot-1/failure.json。以真实user_bridge.dg完整副本为候选，记录基线SHA。在合法Bridge初始化未发布Domain上唯一bind，接两处运行时acquire和两处unlock，bootstrap原Domain锁原样保留；retire/global_barrier用外层票，不能二次排队。保留绝对期限、真实poll/ACK、原fail-closed、返回模式及诊断。不放宽期限，不假定公平性解释首因。测试编译完整真实生产Bridge两模式，补能拒绝遗漏/混用锁路径的实际负控。Cursor手动领取；协调者独立复验、真实迁移，再在正常USB与P5退休场景复测。

## 可修改文件

- `cursor-works/src/p6/bkl-bridge/user_bridge.dg`
- `cursor-works/src/p6/bkl-bridge/contract.md`
- `cursor-works/tests/test_p6_bkl_bridge.py`
- `cursor-works/deliveries/P6BKLBRIDGE1.md`

## 定向验收

- `discover:cursor-works/tests:test_p6_bkl_bridge.py`
- `module:tests.test_user_bkl`
- `module:tests.test_user_domain`

交付：`cursor-works/deliveries/P6BKLBRIDGE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

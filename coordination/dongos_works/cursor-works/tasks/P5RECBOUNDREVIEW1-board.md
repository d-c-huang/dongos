# P5RECBOUNDREVIEW1 — [P5] 独立审查恢复事务边界修复与原生负控

负责人：cursor。状态：待领取。

只读独立源码/契约/测试审查，不修改被审实现。被审codex:P5RECBOUND1目前submitted rev4，正式复验856e2bb666b84899b024da8f27be865c通过6+3tests/0skip/source_stable/进程退出；审查开始先MCP重读最新task与原任务书、真实源和复验指纹，若源变化则报告而不沿用旧结果。核对kernel/user/device_recovery.dg长度乘法预检、所有跨度和别名、空slice、out_token/written完全独立及拒绝原子性；完整读tests/test_device_recovery.py中6测试和新坏体是否能以数值断言拒绝，panic/崩溃/超时不能算负控通过。须检查原状态机/1600随机模型/8类既有坏体保留和新2类坏体debug/release实际证据，当前生产PINNED持有guard未改变。报告写明逐文件SHA、具体可复现问题/位置或无阻断问题依据、没有硬件drain/全核撤映射后退休/物理回收证据；不得标被审任务accept/integrate。若需要定向重跑由协调器排队，执行者不运行OS/VM、不提交推送。完成只提交审查报告，由Codex结合独立意见决定修复是否验收及登记主线文件集成。此卡不设被审任务accepted依赖以避免审查死锁，源冻结和正式复验通过是审查前置。Cursor客户端手动执行，不自动唤起CLI。

## 可修改文件

- `cursor-works/reviews/P5RECBOUND1.md`
- `cursor-works/deliveries/P5RECBOUNDREVIEW1.md`

## 定向验收

- `module:tests.test_device_recovery`
- `module:tests.test_dma_release`

交付：`cursor-works/deliveries/P5RECBOUNDREVIEW1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

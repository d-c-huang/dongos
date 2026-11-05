# P5DMAINT1 — P5 DMA退休接口主线迁移与关联原生回归

负责人：codex。状态：待领取。

已验收cursor:P5DMARETIRE1完整memory/device_host真实迁入生产，候选不变。迁移专项测试使CAND固定生产；修复集成检查发现GUI缺调度宿主符号及既有reuse/compositor startup View陈旧问题，保留实际受测生产代码和真实坏体；调度未使用边界fail-closed，DMA专项仍用真实Domain/bridge。独立审查适配与迁移指纹，全部声明checks真实原生零skip稳定后登记集成。只集成显式prepare/retire接口，services自动调用另任务，不能关闭P5/DMA drain/硬件门。不运行OS/VM、不提交推送。

## 可修改文件

- `kernel/user/memory.dg`
- `kernel/user/device_host.dg`
- `tests/test_p5_dma_retire.py`
- `tests/p5_dma_retire_fixture.dg`
- `tests/p5_dma_retire_probe.c`
- `tests/test_gui_font_portal.py`
- `tests/test_user_reuse_cursor.py`
- `tests/dma_scheduler_boundary.py`
- `docs/p5-dma-retirement.md`
- `codex-works/reviews/P5DMAINT1.md`
- `codex-works/deliveries/P5DMAINT1.md`

## 定向验收

- `module:tests.test_p5_dma_retire`
- `module:tests.test_gui_font_portal`
- `module:tests.test_framebuffer_ledger`
- `module:tests.test_user_reuse_cursor`
- `module:tests.test_compositor_pool`
- `module:tests.test_dma_lease`
- `module:tests.test_dma_release`
- `module:tests.test_p5_recovery_context`

交付：`codex-works/deliveries/P5DMAINT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

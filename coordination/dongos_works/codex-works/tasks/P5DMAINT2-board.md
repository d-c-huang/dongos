# P5DMAINT2 — P5 DMA真实集成及原生回归构建超时修复

负责人：codex。状态：待领取。

承接已confirmed paused/archived P5DMAINT1，原源码迁移和失败/取消记录保留。候选P5DMARETIRE1已非作者验收；完整memory/host逐字生产集成，显式接口不接services。解决GUI/FB默认NASM优化超时（同ASM -O0已实测47.83s成功）；所有受测函数体与静态数据必须保持编译器原样，可按全部export根+全部静态函数地址+传递符号依赖保留原体，未达函数陷阱，归档完整asm及reachability，不能隐藏受测代码/把崩溃当负控。补GUI/reuse等陈旧边界，以真实Domain类型、pointer=null/drain错误，不伪造成功。DMA专项仍真实Domain。八组checks完整零skip稳定，非作者审查迁移与测试有效性并复算汇编后才验收集成。不得提高超时/删测试绕过，不运行OS/VM、不提交推送。后续真实调用点另任务，P5不关闭。

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
- `tests/test_framebuffer_ledger.py`
- `tests/test_compositor_pool.py`
- `tests/native_reachable.py`
- `codex-works/reviews/P5DMAINT2.md`
- `codex-works/deliveries/P5DMAINT2.md`

## 定向验收

- `module:tests.test_p5_dma_retire`
- `module:tests.test_gui_font_portal`
- `module:tests.test_framebuffer_ledger`
- `module:tests.test_user_reuse_cursor`
- `module:tests.test_compositor_pool`
- `module:tests.test_dma_lease`
- `module:tests.test_dma_release`
- `module:tests.test_p5_recovery_context`

交付：`codex-works/deliveries/P5DMAINT2.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P5DMARETIRE1 — [P5] 故障DMA映射撤销与撤映射后全核退休事务

负责人：cursor。状态：待领取。

接续P5CTX1/2真实持有上下文，新增实际撤映射步骤而非重写离线恢复规划器。Cursor客户端手动领取执行，不自动启动AI CLI。先读取code/kernel/user/memory.dg、device_host.dg、services.retire_one/revoke_loaded、mm.paging/runtime_roots和smp翻译屏障现有契约，复制完整最新memory/device_host至本人声明副本，记录基线SHA；不直接改主线。范围：可信BSP/BKL内核入口绑定DmaContext的旧owner/incarnation、设备token/generation及memory root/generation和完整DmaLease。旧owner必须永久停机且禁止重新调度；核验整个实际地址空间森林（含preload/pinned根）及内部租约、全部声明页/舍入尾页、尝试/已映射计数，未知/错代/别名不完整不得成功。事务通过真实paging.unmap_live撤销CPU用户映射，在最后一次撤映射之后执行覆盖所有相关CPU/PCID的真实屏障并保留准确回执；不可拿已有stop/detach ACK或BSP-only失效充数。此任务始终保持PINNED和DMA物理块占用，不清零、不free/recycle、不授予drain，不重绑令牌/设备、不修改syscall ABI；设备仍可写的旧物理块不能复用。任何预检失败无写入，执行后任一步不确定则sticky hold，保留已撤映射及pending页表回执，不重试覆盖身份。复用已完成全森林和页表接口，不复制一套宽松检查器。实际Dong debug/release+独立C页表/轨迹oracle覆盖完整与partial/physical0租约、旧根/旧owner、别名、4K/2M未知映射拒绝、缺CPU ACK、旧ACK、屏障错误、逐步注入失败，证明未clear pin/未清零释放，至少2真实坏体正常编译执行后被断言拒绝。host硬件边界必须明确stub，执行者不运行OS/VM；主线接线、独立复验与真实客体验收由Codex后续完成。本项不得关闭P5；drain/回收复用/恢复发布另验，不提交推送。

## 可修改文件

- `cursor-works/src/p5/dma-retire/user/memory.dg`
- `cursor-works/src/p5/dma-retire/user/device_host.dg`
- `cursor-works/src/p5/dma-retire/contract.md`
- `cursor-works/tests/test_p5_dma_retire.py`
- `cursor-works/tests/p5_dma_retire_probe.c`
- `cursor-works/tests/p5_dma_retire_fixture.dg`
- `cursor-works/deliveries/P5DMARETIRE1.md`

## 定向验收

- `discover:cursor-works/tests:test_p5_dma_retire.py`

交付：`cursor-works/deliveries/P5DMARETIRE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

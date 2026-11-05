# P5DMACALL1 — [P5] 将准备与映射退休接入真实故障生命周期

负责人：cursor。状态：待领取。

接续P5DMAINT2主线接口，Cursor客户端手动领取，不自动启动AI CLI。复制完整最新services/device_host到声明候选并记录基线SHA。实际审查retire_one/revoke_loaded顺序：永久停机和真实Domain退出→硬件quarantine/ledger撤权→prepare一次→retire一次。只对可信完整DMA上下文接线，UP/未知/partial/错误身份继续永久hold且不得自动发布/重启；普通manager REVOKE与preloaded无owner路径不能误调用。必须明确准备或退休失败与原IPC/cap清理/级联退役的关系，避免失败跳过原必须清理；保留原错误与停机状态，不能利用第二次prepare覆盖第一次失败。不给DMA drain/reclaim/unpin权限、不清零旧物理页。新增实际Dong debug/release真实services分支的独立C轨迹oracle，覆盖正常顺序、全部前置/错误传播/重复故障、UP/manager/preload排除、partial、旧身份及级联；至少真实坏体跳prepare/先retire后stop/吞错误被数值断言拒绝。依赖未验收不得领取。独立审查/正式复验后由Codex真实集成，客体硬件执行另验，本项不关闭P5，不运行OS/VM或提交推送。

## 可修改文件

- `cursor-works/src/p5/dma-call/user/services.dg`
- `cursor-works/src/p5/dma-call/user/device_host.dg`
- `cursor-works/src/p5/dma-call/contract.md`
- `cursor-works/tests/test_p5_dma_call.py`
- `cursor-works/tests/p5_dma_call_probe.c`
- `cursor-works/tests/p5_dma_call_fixture.dg`
- `cursor-works/deliveries/P5DMACALL1.md`

## 定向验收

- `discover:cursor-works/tests:test_p5_dma_call.py`

交付：`cursor-works/deliveries/P5DMACALL1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

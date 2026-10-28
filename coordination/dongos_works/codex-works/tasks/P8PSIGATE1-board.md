# P8PSIGATE1 — PSI内核快照与DMA授权配套适配

负责人：codex。状态：待领取。

配套P8PSI1。保留Extension48B ABI，协议项legacy_control作为可信内核逐条验证后生成的PSI速度集合，原始range保留PSIC。只支持完整标准USB2三速/USB3单速且编号/速率/双工一致，校验PSI跨度及next边界、重复，授权检查集合与数量，非标准表仍拒绝。不放宽DMA/MMIO权限。实际内核producer及authority正反例复验。

## 可修改文件

- `kernel/user/devices.dg`
- `services/drivers/xhci_authority.dg`
- `tests/xhci_authority_probe.c`
- `tests/xhci_kernel_probe.c`
- `tests/test_xhci_kernel.py`
- `tests/test_xhci_authority.py`
- `codex-works/deliveries/P8PSIGATE1.md`

## 定向验收

- `module:tests.test_xhci_authority`
- `module:tests.test_xhci_kernel`

交付：`codex-works/deliveries/P8PSIGATE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

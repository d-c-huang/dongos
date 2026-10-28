# P8PSI1 — Intel xHCI显式PSI标准速度表兼容修复

负责人：codex。状态：待领取。

实机CHECK0D REG8008 VALUE30111001 AUX02000802确认USB2 SupportedProtocol显式3条PSI被一律拒绝。解析并验证标准速度ID/位率对应、PSI边界/链重叠/重复和保留字段；仅接受下游已实现的标准速度映射，不把非标准ID假装默认速度，不改ABI/DMA授权。真实原生正反例和独立复验/构建；完整实机成功仍待复测。

## 可修改文件

- `services/usb/xhci_controller.dg`
- `tests/xhci_precheck_diagnostic_probe.c`
- `tests/test_xhci_precheck_diagnostic.py`
- `docs/hardware-xhci-precheck.md`
- `codex-works/deliveries/P8PSI1.md`

## 定向验收

- `module:tests.test_xhci_precheck_diagnostic`
- `module:tests.test_xhci_controller`
- `module:tests.test_xhci_scratchpad`

交付：`codex-works/deliveries/P8PSI1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8XHCIPRECHECK1 — 真机xHCI预检拒绝分支与原始寄存器证据

负责人：codex。状态：待领取。

实机BOOT LIVE R2捕获08110002/phase0/held0，controller.precheck多个拒绝条件共用码，不能据此猜测legacy/未知cap/PSI后放宽门禁。保存固定版本reason/offset/raw/aux诊断，在实际失败服务xhci_error前输出四条短日志，现有sticky屏保留7行。只记录决策读取样本，不额外MMIO读取/写入，不改变预检谓词、enable/DMA/返回码或Setup/Caps/State布局。实际debug/release正反例、原始样本/原因/读失败/只读canary，旧controller/scratch回归与完整构建和rootVM屏幕检查。已有BOOTCONSOLE任务负责R3诊断版本标识，本任务不写其文件。用户已确认原SanDisk H插回，验证后四文件备份/fsync/回读/FAT rb；Intel根因仍待具体条件，不冒充修复成功。

## 可修改文件

- `services/usb/xhci_controller.dg`
- `services/drivers/xhci_service.dg`
- `tests/test_xhci_precheck_diagnostic.py`
- `tests/xhci_precheck_diagnostic_probe.c`
- `docs/hardware-xhci-precheck.md`
- `codex-works/deliveries/P8XHCIPRECHECK1.md`

## 定向验收

- `module:tests.test_xhci_precheck_diagnostic`
- `module:tests.test_xhci_controller`
- `module:tests.test_xhci_scratchpad`

交付：`codex-works/deliveries/P8XHCIPRECHECK1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

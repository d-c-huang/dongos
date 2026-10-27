# P8SCRATCH1 — Intel真机xHCI Scratchpad DMA布局与授权支持

负责人：codex。状态：待领取。

用户明确要求修改；真实hcs2=14200054，34个4KiB scratchpads及restore位；现驱动/authority拒绝，32页DMA不足。增加有界且共享的scratch布局（保持零scratch旧128KiB与ABI）；按硬件计算且双端复核所需页数，扩展独占pinned DMA allocator上限到128页、校验全部owned alias/物理页、动态内核快照、DCBAA[0]表及零scratch页校验再BME；控制器真正初始化地址表而非删守卫。支持最多64 scratch并明确超限拒绝，restore能力不等于发起save/restore，保留禁用命令检查。扩展链现有normal映射按真实BAR大小读0x8000，评估未知类型/固件占用但不猜测和跳过ownership。真实native新正负向和既有controller/authority/kernel/transport/async/BOT回归，完整编译并Root真实VM。通过独立复验审查后集成；真实硬件仍待测。当前不假设U盘已经插回。

## 可修改文件

- `services/usb/xhci_dma.dg`
- `services/usb/xhci_controller.dg`
- `services/usb/xhci_transport.dg`
- `services/drivers/xhci_authority.dg`
- `services/drivers/xhci_service.dg`
- `kernel/user/devices.dg`
- `kernel/user/memory.dg`
- `tests/test_xhci_controller.py`
- `tests/xhci_controller_probe.c`
- `tests/test_xhci_authority.py`
- `tests/xhci_authority_probe.c`
- `tests/test_xhci_kernel.py`
- `tests/xhci_kernel_probe.c`
- `tests/run_xhci_qemu.py`
- `tests/test_xhci_scratchpad.py`
- `tests/xhci_scratchpad_probe.c`
- `docs/hardware-xhci-scratchpad.md`
- `codex-works/deliveries/P8SCRATCH1.md`

## 定向验收

- `module:tests.test_xhci_scratchpad`
- `module:tests.test_xhci_controller`
- `module:tests.test_xhci_authority`
- `module:tests.test_xhci_kernel`

交付：`codex-works/deliveries/P8SCRATCH1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

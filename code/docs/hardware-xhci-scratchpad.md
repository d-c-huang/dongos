# Intel xHCI Scratchpad 修复

真机 CAPS R1 的原始字段为 CAP0=01000080、HCSPARAM1=18000840、HCSPARAM2=14200054、HCCPARAM1=200077C1、PAGESIZE=1、USBSTS=1、XECP FIRST=8000、REJECT MASK=C、FLAGS=10F。读取无错误；硬件需要34个4KiB Scratchpad，且声明Scratchpad Restore。此前两个正常执行端都拒绝这些能力。先前首4KiB诊断没有读取8000偏移的扩展链，legacy零不能解释为固件已释放所有权。

## 实际修复

- 新增共享纯布局 `usb.xhci_dma`：从两段5位字段解码数量，支持0至64，超过64明确拒绝。零数量保留原131072字节；非零在原128KiB之后放一页地址表及各4KiB缓冲页，并向上取整为与分配器一致的2次幂页数。34页使用128页/524288字节，原来的环、DCBAA及三个32KiB设备作用域均不移动。
- 驱动根据真实HCSPARAMS2申请完整独占租约；内核独立重读同一硬件字段并核对大小，用户不能任意扩充租约。原32页分配接口保持不变，新增仅供可信xHCI broker调用的128页入口，沿用先pin再分配、失败保留和禁止重试/回收协议。
- 控制器核对整个租约的物理范围和AC64限制，完成halt/reset后清零完整租约，写入DCBAA[0]、地址表和所有页指针，再进行原有fence、内核enable和启动顺序。新能力没有引入save/restore命令。Restore能力位不再单独导致拒绝，实际CSS/CRS等命令仍被授权检查拒绝。
- 内核按实际租约页数分配只供内核访问的快照，并逐页核对全部owned alias、物理身份和可写属性。authority在BME前校验DCBAA[0]、每个Scratchpad指针、完整表页、所有缓冲页和向上取整尾部的零值；损坏或不完整租约不能开启总线主控。
- 固件ownership、SMI、扩展类型和协议覆盖的原有门禁保留。正常路径已有按真实BAR长度检查的扩展链读取，允许链位于8000偏移；本修复不会用首页诊断的零值替代实际扩展链检查。

Scratchpad位与数量解码参照[Linux原始能力定义](https://raw.githubusercontent.com/torvalds/linux/master/drivers/usb/host/xhci-caps.h)，DCBAA[0]和缓冲地址表的关系参照[Linux分配实现](https://raw.githubusercontent.com/torvalds/linux/master/drivers/usb/host/xhci-mem.c)。这些来源用于核对结构和语义；DongOS的独占租约、门禁和测试使用本项目实现。

## 验证范围

`tests.test_xhci_scratchpad`执行实际控制器、authority及新增allocator函数体，使用独立C布局/寄存器/DMA模型。覆盖0、1、31、32、34、64页，65和1023超限、旧租约不足、首/末地址表项损坏、未清零页和尾部、save命令拒绝，以及128页分配各阶段和每页中断后的保留状态。debug/release、正常O0/O2、ELF/COFF汇编；缺失DCBAA指针、错误缓冲地址、未清尾部、跳过授权校验、允许restore命令、allocator超界或过早完成等真实错误源码必须被独立断言拒绝。

`tests.test_xhci_kernel`执行真实授权链，新增34/64页成功及表项、尾部、最后一页alias损坏拒绝案例。旧controller/authority/transport/async/BOT和旧32页allocator继续回归。完整正常USB-only桌面构建与实际VM验证单独执行；QEMU常规控制器的Scratchpad为零，不能将它的成功宣称为Intel真机通过。

真机仍须使用新版测试桌面及USB有线键鼠。若仍停机，应保留新画面继续定位；Scratchpad支持缺口已由本修复处理，但不是此前S14/S19唯一原因的证明。U盘写入需先通过独立定向复验、源指纹审查、完整镜像验证，再核对原SanDisk身份、备份、flush和回读；不格式化或改分区。

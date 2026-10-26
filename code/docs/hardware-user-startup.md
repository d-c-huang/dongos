# S14 后的用户态启动诊断

真机在 S14 CPL3 START、CPU COUNT=8、FIRST ERROR=0 停留超过两分钟。旧代码在调用 `user_smp_boot_begin` 前就清除了诊断 view，而实际 PCI 发现、用户域和 CPU 头构建都在此调用内；publish 的错误还会直接进入无屏幕反馈的 fail-stop。因此旧画面无法证明之后没有错误。

本次修复这两个诊断盲区。没有足够证据把真机故障归因为 CPU 数量、PCI 门禁、xHCI scratchpad 或固件所有权，故不猜测修改这些实现，也不宣称桌面故障已经解决。

| 阶段 | 含义 | 正常路径绘图 |
| --- | --- | --- |
| S15 PCI DISCOVERY | 进入完整 PCI 预发现 | 是 |
| S16 USER DOMAIN | PCI 预发现已返回，建立用户域 | 是 |
| S17 USER CPU CONFIG | 配置各 CPU 栈与头 | 是 |
| S18 BSP ACTIVATE | 准备激活 BSP 用户态架构 | 是 |
| S19 USER DOMAIN LOCK | BSP 已激活，准备取得用户域锁 | 是，期限开始前 |
| S20 USER SERVICES | 绑定用户态服务 | 仅记录 |
| S21 USER AP START | 发布并等待 AP 用户态入口 | 仅记录 |
| S22 USER QUEUES | 投影用户任务队列 | 仅记录 |
| S23 USER DISPATCH | 退休诊断 view，准备解锁放行用户程序 | 仅记录 |

旧 S01–S14 保留。prepare 及正常返回的 activate 错误沿原服务错误出口，显示原始64位首次错误；BSP 专用 publish 错误返回先经过同一错误记录器，再进入原 fail-stop，保留内部失败指标。通用 AP、IRQ、用户态调度故障入口不增加绘图。

## 计时、显示与架构边界

绘图仍仅调用现有 `screen_draw`，使用相同几何验证和四 qword framebuffer Gate，无新帧缓冲写者。SysV 包装保存所有 GPR、flags/DF、XMM 和对齐契约。S19 绘图发生在创建原 AP 等待期限之前；S20–S23 仅写内存 phase，既不画屏也不延长预算。BSP 已明确失败时才绘制终态，不能把诊断开销变成运行成功的前提。

成功路径在 `ud.unlock` 前以 store-only 清除 view，防止 AP 用户程序开始绘图后与启动诊断并发。legacy 分支仍在 `user_run` 前关闭。退休后的 unlock 自身失败、activate 内部直接 fail-stop 和后续用户态故障不能保证显示新的错误码，不为补画恢复 view 或改动通用故障入口。

正常启动最后留在屏幕上的诊断可能是 S19，内存 phase 则已到 S23/view=0；应由桌面随后覆盖。若一直停在 S15–S18，可据最后阶段定位准备环节；若显示 BOOT FAILED，则同时拍下阶段和 FIRST ERROR。若停在 S19/0，说明已越过前面的准备段，但仍不能判断用户态、USB/文件服务和桌面显示是否成功。

## 验证和发布

使用实际宏、包装器和 renderer 的原生守卫测试验证全部23阶段的像素、仅 mark 不触屏、退休后不重画、首次完整错误、ABI、栈及 Gate；hook 检查约束 AP 计时窗口无绘图、退休在放行前。真实坏体必须正常执行后由 oracle 拒绝，正式独立复验要求零 skip 和源稳定。

构建和实际 VM 证据在 `build/hardware/usb-user-diag-20261026-r1/`。正常 USB-only 两次完整桌面/HID/持久文件/CPU 观察器之外，另以私有实际 PCI preflight 返回错误，验证 S15 和完整错误显示；该候选不能写入 U 盘。正常产物通过后才核对原 SanDisk H:，备份、flush/fsync、全 SHA 读回和只读 FAT32 检查。真实 Intel 电脑的下一处阶段与最终桌面/键鼠结果，仍需用户复测。

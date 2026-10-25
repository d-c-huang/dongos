# 真机 ACPI 画面之后的启动诊断

用户确认 GOP 修复版已显示 `DONGOS P3 ACPI READY`，等待约一分钟仍保持该画面。该标题是 runtime7 进入线程验证前的最后一次绘图；只有旧 runtime3 专用诊断会在完成后改成 THREADS PASS。该照片不能区分 IRQ、AP、多核验证、ELF 加载或 USB/文件系统阶段，也不能直接认定 ACPI 失败。

任务 `codex:P8STAGE1` 增加正常 runtime7 的 BSP 同步启动检查点，保持 USB-only 构建及原来的所有硬件、隔离、算法与期限检查。引导器继续使用已修复的 `USB DIAG R4`；进入内核后以 `DONGOS Sxx ...` 标识本轮启动诊断。

## 屏幕阶段

| 阶段 | 含义 |
| --- | --- |
| S01 IRQ PREPARE | 开始 BSP 的设备/中断准备 |
| S02 IRQ PLATFORM | 开始 APIC/计时平台初始化 |
| S03 THREADS TEST | 即将 arm 定时器并验证真实抢占线程 |
| S04 THREADS PASS | runtime_begin 已真实成功返回 |
| S05 AVX CHECK | 检查可选 AVX 扩展；不支持仍沿原逻辑处理 |
| S06 SMP START | 开始 AP、多核和 TLB 验证 |
| S07 SMP APS READY | 原 SMP/AP 验证与报告成功 |
| S08 SMP LARGE TEST | 开始原多核大内存验证 |
| S09 SMP PARALLEL TEST | 开始原并行验证 |
| S10 SMP PASS | smp_runtime_begin 已真实成功返回 |
| S11 DESKTOP ENABLE | 启用已有桌面配置 |
| S12 SERVICES PREPARE | 检查服务保护页并准备 ELF/资源 |
| S13 ELF READY | dong_services_prepare 已成功 |
| S14 CPL3 START | 即将交接到用户态服务；尚不代表桌面或 USB 已就绪 |

阶段表示最后一次成功显示的边界。函数内部若停止或返回失败，会留下相应阶段；失败画面显示首个完整 64 位返回值和 ACPI CPU 数量。某些入口只返回布尔值，失败码可能为零，此时以失败标志判断，不能将零解读为成功。没有事实依据时不扩大超时、跳过 AP、关闭硬件校验或改变存储后端。

## 显示与时序约束

初始 screen_draw 成功后才保存已验证 RuntimeView。诊断绘图保存所有通用寄存器与 flags，不触 XMM，使用保存的 View，不依赖内部函数当前的 R12。所有文字仍在原 screen_draw 的 Framebuffer Gate 和几何校验内，Gate 的四个 qword 布局不变，仍只有原屏幕和 panic 两个外层 writer。未 arm、已禁用、Gate closed/closing 或非法几何时不写 MMIO，也不重新打开 Gate。

定时器 arm 到 sched_start/stop 之间不插入渲染。AP/TLB/parallel 的 deadline 临界区内部不插入渲染，只在原调用前后观察。S14 完成后、首次用户态入口调用前清除诊断 View；后续错误可以保留内存/串口信息，普通进度绘图不能再碰用户合成器拥有的帧缓冲。runtime0/3/4/5/6 的宏均为空，保留历史流程。

## 介质与下一次测试

只用显式 USB-only runtime7 成品。最终完整构建、原生实际汇编/坏体、独立复验、真实模拟启动证据保存在 `build/hardware/usb-stage-20261025-r2/`。首轮宏局部标签与观察器兼容失败、受控候选缺生成 include 的失败历史保留在 r1，均未发布到 H:。最终把首错记录集中到唯一命名函数，保持已有 ELF 观察器原检查；真实多对象链接夹具能重现并拒绝旧问题。原 SanDisk H: 更新前核对 serial `4C530000010320109015`、USB 非系统盘、原分区和旧 R4 成品 SHA；先备份，再刷新写入并全读回 SHA，不格式化、不写内盘。

安全弹出，在原 Intel 电脑用此前成功的 UEFI 设置启动。拍下最后停留的 `Sxx` 阶段、失败码与 CPU 数量；如果进入桌面，测试鼠标和 Terminal 的 `help`，再测试 F12、`pwd`。S14 之后仍可能发生 USB、文件系统或用户态初始化失败，需要实际后续画面再定向诊断。当前不登记真机桌面、输入、PCID 或 WC 性能已通过。

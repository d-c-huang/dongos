# P8BOOTCONSOLE1 — 真机连续启动的屏幕日志与首用户态进度

负责人：codex。状态：待领取。

R2实机仍残留S19/error0，不能归因锁或串口。已有首CPL3/F4真机证据，下一版将真实内存日志、BSP初次返回/捕获与syscall计数在首compositor入口前显示，继续执行正常启动而非成功checkpoint停机。使用原屏幕几何检查和cache Gate；仅可信BSP/内核根/已恢复kernel xstate，预定cfg3首次用户返回前永久关闭启动绘制，不能与compositor写者并发。只读永久owned输入与4096日志环，文本固定界限ASCII转大写、完整行/截断语义明确；保留原致命失败屏。建立显式不同profile和严格私有patch/源哈希/命令绑定，禁止冒充普通无hook版。实际producer/assembly路径正反例、布局与只读canary、独立0skip稳定复验，root连续8CPU桌面/HID/文件与故障日志显示验证。用户已确认原SanDisk H插回，验收后四文件备份/同步/回读/FAT rb。此任务是减少真机信息盲区，不宣称已修好真机根因。

## 可修改文件

- `kernel/boot/startup_console.dg`
- `tools/build_startup_console.py`
- `tests/test_startup_console.py`
- `tests/startup_console_probe.c`
- `tests/startup_console_shim.asm`
- `docs/hardware-startup-console.md`
- `codex-works/deliveries/P8BOOTCONSOLE1.md`

## 定向验收

- `module:tests.test_startup_console`
- `module:tests.test_user_runtime`

交付：`codex-works/deliveries/P8BOOTCONSOLE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

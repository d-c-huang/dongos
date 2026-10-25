# P8USBAUDIT1 — USB完整FAT审计的有界独立启动预算

负责人：codex。状态：待领取。

R3/R4/R5真实单MBR USB含33MB服务包需完整FAT镜像/目录/链/孤儿簇审计，固定所有进程10秒会在FS仍有真实I/O进展时强制退休/重启，R5保留3次FS超时后READY与TLB Timeout失败。先前P8USBSTART1不延长期限的优化未能覆盖真实I/O成本；本任务明确仅USB_ONLY正常profile的FS cfg1启动采用60秒有界预算，默认和其余17配置仍10秒；不删审计、不加重试、不放宽TLB/磁盘/HID oracles。共享hardware_profile决定可信内核catalog，不接受用户指定预算，所有hz乘法先做相应上界拒绝。真实native两profile全18cfg断言、非法hz零/溢出及输出不变，60->10坏体正常失败；旧service launch/process ABI回归。root重编译并实际同USB/三可写内盘/HID/两次启动验证，不VM或物理盘给worker。不把TLB失败或鼠标失败隐去，保留全部历史。

## 可修改文件

- `kernel/user/processes.dg`
- `tests/test_usb_startup_budget.py`
- `tests/usb_startup_budget_probe.c`
- `tests/test_processes.py`
- `codex-works/deliveries/P8USBAUDIT1.md`

## 定向验收

- `module:tests.test_usb_startup_budget`
- `module:tests.test_service_launch`
- `module:tests.test_processes`

交付：`codex-works/deliveries/P8USBAUDIT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

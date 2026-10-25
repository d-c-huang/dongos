# P8USBAUDIT2 — USB完整FAT审计的有界独立启动预算

负责人：codex。状态：待领取。

R3/R4/R5真实同MBR USB含33MB服务包需完整FAT镜像/目录/链/孤儿簇审计，固定全部进程10秒会在FS仍有真实I/O进展时强制退休/重启；R5保留3次FS超时后READY与TLB Timeout失败。先前不延长期限的优化不足，本任务明确仅USB_ONLY正常profile的FS cfg1启动采用60秒有界预算，默认及其余17配置仍10秒；不删审计、不加重试、不改TLB/磁盘/HID门槛。共享hardware_profile决定可信内核catalog，不接受用户指定预算，hz乘法前上界拒绝、失败不发布catalog。两profile全18cfg真实native断言、hz零/溢出与输出不变，60->10真实坏体失败；现有service launch及3套process catalog默认ABI回归，仅新增真实profile源指纹。root重编译实际单USB+三可写内盘/HID/两启动，不给worker VM/物理盘权限。所有失败保留。P8USBAUDIT1为未执行的声明模块名错误已归档。

## 可修改文件

- `kernel/user/processes.dg`
- `tests/test_usb_startup_budget.py`
- `tests/usb_startup_budget_probe.c`
- `tests/test_service_launch.py`
- `tests/test_process_catalog.py`
- `tests/test_process_catalog32.py`
- `tests/test_process_catalog_r6.py`
- `codex-works/deliveries/P8USBAUDIT2.md`

## 定向验收

- `module:tests.test_usb_startup_budget`
- `module:tests.test_service_launch`
- `module:tests.test_process_catalog`
- `module:tests.test_process_catalog32`
- `module:tests.test_process_catalog_r6`

交付：`codex-works/deliveries/P8USBAUDIT2.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8BOOTLOG1 — 消除串口诊断对桌面启动的阻断并保留服务失败现场

负责人：codex。状态：待领取。

最新USER RUNTIME R1真机仍残留S19/error0。只读审查发现服务管理器及启动服务将sys.log UART发送失败作为致命启动失败，services_write_bytes用百万次IN轮询且占用BKL，正常串口虚拟机不覆盖缺席/不响应场景；管理服务退出可静默只剩启动旧画面。先通过实际实现和失效UART模型复现，证据支持后修复可选日志后端不阻断真实启动；保留错误/退出证据并接入可信BSP失败屏，避免单个正常子进程退出误判。不得虚构Intel根因、修改锁时限/存储权限、引入成功checkpoint停机。实际正反例、现有init/桥测试、独立零skip稳定复验；root执行连续8CPU完整USB桌面/键鼠/文件持久性验证及负例，不以只新增诊断作为真实根因已解决。发布前实审验收真实集成，同一SanDisk确认身份/备份/仅四文件/校验，用户未插回前不得写盘。

## 可修改文件

- `kernel/services_run.asm`
- `kernel/user/services.dg`
- `kernel/boot/user_runtime_status.dg`
- `tools/build_user_runtime.py`
- `tests/test_services_console.py`
- `tests/services_console_probe.c`
- `tests/services_console_probe.asm`
- `tests/test_user_runtime.py`
- `tests/user_runtime_probe.c`
- `tests/test_init_lifecycle.py`
- `tests/init_lifecycle_probe.c`
- `docs/hardware-user-runtime.md`
- `codex-works/deliveries/P8BOOTLOG1.md`

## 定向验收

- `module:tests.test_services_console`
- `module:tests.test_init_lifecycle`
- `module:tests.test_user_runtime`

交付：`codex-works/deliveries/P8BOOTLOG1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

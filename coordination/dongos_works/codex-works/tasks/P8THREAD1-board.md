# P8THREAD1 — 无磁盘真机中断线程诊断的完成画面

负责人：codex。状态：待领取。

用户报告R3 runtime0已显示DONGOS P3 ACPI READY，只记录基础引导/CPU内存/ACPI/GOP用户观察，不外推P3中断线程或完整P8。准备正常runtime3无存储测试：仅当runtime_begin真实成功返回后设置完成状态并重新绘制THREADS PASS画面；尚未完成或失败不得显示PASS。原129ticks/65switches/两worker/GPR-xstate/guard时钟算法门保持，其他runtime级别预处理输出不改。仅三个声明文件，使用已集成高地址EFI交接；实际6GiB高载入客体验证完整原runtime串口oracle并目视新画面，坏体漏调runtime不得出现PASS。H介质待插回，测试版无块服务/FS/桌面/输入，不触内置盘。通过独立复验及主目录实物审查后分accept/integrate。

## 可修改文件

- `kernel/entry.asm`
- `docs/hardware-runtime-diagnostic.md`
- `codex-works/deliveries/P8THREAD1.md`

## 定向验收

- `module:tests.test_runtime_qemu_result`

交付：`codex-works/deliveries/P8THREAD1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8FIRSTENTRY1 — 正常AP调度后的首次CPL3捕获与BSP首错诊断

负责人：codex。状态：待领取。

真机AP CHECK全通过，继续正常AP idle/BKL/首次INIT用户入口。新增explicit FIRST USER R1私有profile，取消前卡APpark，保留normal AP/boot/unlock/entry路径；只在user_boot最后retire前保留view并验证唯一初始INIT slot5且affinity1/enginecount1，正常BSP调度后在真实user_bridge.capture完成checked/begin_entry/copy/complete_entry(含XSAVE)并恢复kernel_xstate后、deadline/poll/acquire/service前hook单次停机。无初始服务callback执行，因此无其他进程可启动，无compositor执行，虽既有FB映射仍存在但没有第二实际写者。成功不重置RSP避免覆盖rawFrame，kernel根/xstate已安全；BSP-only原可信user_smp_fail路径在原last_error/metricsfailed后先在已映射user_entry代码切回kernelroot再转诊断，保存rawCR3并恢复kernelxstate，reason1不冒充捕获异常帧；untrusted GS/所有AP fail路径保持fail-stop。记录192B/24scalar首次reason/vector/op/slot5 token/rip/rsp/roots/captured/mode/syscalls/entries/Bridge Progress/Failure/headererror，15行原Gate/geometry，完整normal services/默认/deadline保持。actualnative正负/ABI/BSS/once/只读输入/精确hook与fail边界，9真实命令+4对象/严格overlay与17服务，Root8CPU actual初始INIT/CPL3事件/CS或savedframe/CR3/xstate/capture/normalAP(无park)/无服务callback及新硬件authority/代码/像素/全USB+三内盘未变。独立实审后备份回读写原H。此卡不宣称syscall服务成功或桌面通过，所有诊断改变及局限明确。

## 可修改文件

- `kernel/boot/first_user_checkpoint.dg`
- `tools/build_first_user_checkpoint.py`
- `tests/test_first_user_checkpoint.py`
- `tests/first_user_checkpoint_probe.c`
- `docs/hardware-first-user-checkpoint.md`
- `codex-works/deliveries/P8FIRSTENTRY1.md`

## 定向验收

- `module:tests.test_first_user_checkpoint`

交付：`codex-works/deliveries/P8FIRSTENTRY1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

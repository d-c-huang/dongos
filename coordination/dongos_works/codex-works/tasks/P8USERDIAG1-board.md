# P8USERDIAG1 — S14后BSP用户态准备分段及真实失败显示

负责人：codex。状态：待领取。

用户真机Intel8CPU停S14 CPL3 START/FIRST ERROR0超过2分钟；用户最新明确修改，上一轮10分钟只读限制已结束。当前services_run在user_smp_boot_begin前HW_BOOT_DISABLE，prepare PCI/arena/context错误不可见，publish失败直接user_smp_fail吞原返回码。添加S15PCI/S16USERDOMAIN/S17CPUCONFIG/S18BSPACTIVATE/S19DOMAINLOCK/S20SERVICES/S21APSTART/S22QUEUES/S23DISPATCH，保留旧1..14。prepare中安全段可画；publish开始在until创建前画S19，之后所有正常阶段仅mark不draw，成功在ud.unlock前store-only retire view；legacy仍user_run前disable。BSP专用publish失败先记录原RAX并画一次再原user_smp_fail，保留metrics/停机；不改通用AP/IRQ故障入口。GPR flags DF XMM及SysV栈/Gate四qword/几何/首次error64/源稳定保留。纯诊断及失败传播修复，不把scratchpad/BIOShandoff/PCI Runtime门禁等未证根因盲改，不改安全限制/deadline/EFI/USB-only/allocator。native原宏helpers renderer全阶段像素与mark-only/retire门测试、hook时序及错误传播独立检查，实际坏体正常oracle拒绝，独立0skip。root正常USB-only两boot完整HID/FS/CPU强gate，以及私有真实PCI preflight失败S15错误原值/像素的实际VM取证；候选不发布。正常版本通过才备份更新原SanDisk H+fsync/readback/readonlyFAT。只修诊断盲区，真实Intel最终卡点需要下一次反馈，不能宣称桌面修好。沿原用户授权代码/记录推GitHub，公开JSON去claim_token保持本机状态不变。

## 可修改文件

- `include/boot_progress.inc`
- `kernel/boot_progress.asm`
- `kernel/entry.asm`
- `kernel/services_run.asm`
- `kernel/sched/user_boot.asm`
- `kernel/sched/user_boot.dg`
- `tests/test_boot_progress.py`
- `tests/boot_progress_probe.c`
- `docs/hardware-user-startup.md`
- `codex-works/deliveries/P8USERDIAG1.md`

## 定向验收

- `module:tests.test_boot_progress`
- `module:tests.test_framebuffer_gate`
- `module:tests.test_user_smp_integration`
- `module:tests.test_user_smp_normal_activation`

交付：`codex-works/deliveries/P8USERDIAG1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

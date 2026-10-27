# P8APCHECK1 — 真实AP交接与队列投影后的受控停机诊断

负责人：codex。状态：待领取。

真机preAP检查点字段全符，继续定位新AP发布/activate ready2及队列投影。新增显式AP CHECK R1私有profile：保持原锁/deadline/IPI/activate及BSP投影实路径，仅在私有user_boot.asm让AP成功activate之后park(IF0 cli/hlt)而不进入idle/用户域锁竞争；BSP真实等待全部ready2并投影成功后、retire/unlock之前捕获17u64屏幕主动停止。AP park是诊断行为改变，必须明确不能证明AP idle/BKL竞争/CPL3通过；避免在AP timed lock窗口慢速重绘。原错误路径保持，capture只读所有配置Header.ready/last_error，掩码/首错/boot/domain/owner/pub等15行；无用户进程/设备authority。完整私有图及第4个user_boot.o严格编译/recipe/2EFI manifest/17服务保持。实际native capture与真坏体/debug-release/O0-O2/ELF-COFF、exact hook及park边界；Root8CPU actualAP header/GS或ready/masks/IPI发布/投影/lock/无硬件authority/全代码/像素/整USB+三内盘不变验证；独立验收后按原SanDisk身份备份+flush+回读+native rb写H。

## 可修改文件

- `kernel/boot/ap_boot_checkpoint.dg`
- `tools/build_ap_boot_checkpoint.py`
- `tests/test_ap_boot_checkpoint.py`
- `tests/ap_boot_checkpoint_probe.c`
- `docs/hardware-ap-boot-checkpoint.md`
- `codex-works/deliveries/P8APCHECK1.md`

## 定向验收

- `module:tests.test_ap_boot_checkpoint`

交付：`codex-works/deliveries/P8APCHECK1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8USERCHECK1 — S19后锁与服务初始化的AP发布前独立停机诊断

负责人：codex。状态：待领取。

真机新版仍显示S19/8CPU/error0。S20-S23只mark不draw，不能猜锁死。显式私有diagnostic保持normal source/services/SMP=1，只在真实ud.acquire成功且services.enable_smp成功后、user_boot_publish及AP新Header发布前捕获Report并屏幕主动停止；无用户程序、USB DMA或桌面，不伪称运行成功。固定15scalar行展示INFO/domain真实状态及原call边界；原失败仍走HW_BOOT_ERROR。复用原geometry/cacheGate renderer，绝不在AP2s窗口重绘或改normal deadline。完整私有graph编译/strictrecipe/digest/normal-source+17service字节稳定；native真实capture和坏体/布局/完整patch断言，Root8CPU真实VM逐值/屏幕/无新domain AP发布/无用户设备authority/整USB及三可写内盘未变，之后独立验收写原H备份flush/readback/native FAT32 rb。正常桌面目标仍待定位，本卡仅intentional preAP checkpoint，USB首错尚未发生不构造伪值。

## 可修改文件

- `kernel/boot/user_boot_checkpoint.dg`
- `tools/build_user_boot_checkpoint.py`
- `tests/test_user_boot_checkpoint.py`
- `tests/user_boot_checkpoint_probe.c`
- `docs/hardware-user-boot-checkpoint.md`
- `codex-works/deliveries/P8USERCHECK1.md`

## 定向验收

- `module:tests.test_user_boot_checkpoint`

交付：`codex-works/deliveries/P8USERCHECK1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

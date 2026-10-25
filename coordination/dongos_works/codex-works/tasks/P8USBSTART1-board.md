# P8USBSTART1 — USB专用输入启动与大卷挂载缓存适配

负责人：codex。状态：待领取。

P8USBONLY1 R2真实混合磁盘启动失败保留mixed-run-1：INIT_FAILURE kind2/3 id4是input配置，原PS2探测在禁用i8042的USB拓扑下耗尽10秒时限。USB_ONLY应直接等原可信cfg13 READY认证，保持1024次有界等待及incarnation/tag验证，绝不发PS2端口/IRQ调用；默认PS2流程不变。现有mount_cache仍限定262144簇，在真实H1899872簇时降为逐扇区RPC，USB模式采用共享FAT_AUDIT_BYTES上限，仅扩大缓存资格、保留两条32sector只读mount-only缓存、原fat完整审计和fail-closed。不延长guest启动时限。增加真实main USBprofile探针，认证失败和PS2/IRQ触达反例，实际cache高簇回调计数/错误传递/边界测试，并兼容默认FS fixture依赖。由root真实VM复验，禁止worker VM/物理盘；无H写入。

## 可修改文件

- `services/drivers/input_service.dg`
- `services/fs/mount_cache.dg`
- `tests/test_usb_input_usbonly.py`
- `tests/usb_input_usbonly_probe.c`
- `tests/test_fs_service.py`
- `tests/test_usb_mount_cache.py`
- `tests/usb_mount_cache_probe.c`
- `codex-works/deliveries/P8USBSTART1.md`

## 定向验收

- `module:tests.test_usb_input_usbonly`
- `module:tests.test_usb_input_entry`
- `module:tests.test_input_service`
- `module:tests.test_fs_service`
- `module:tests.test_usb_mount_cache`

交付：`codex-works/deliveries/P8USBSTART1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8USBADAPT1 — USB-only构建验真与原设备测试夹具适配

负责人：codex。状态：待领取。

P8USBONLY1必要配套：新共享profile模块引入后，旧test_device_manager隔离坏体复制清单必须包含该真实默认模块；USB镜像verify_build必须只读验真声明的全services快照，不让伪造USB_ONLY元数据或缺失/改写快照沿旧通用路径通过。build_usb增加显式--usb-only normal runtime7便捷入口，复用--esp时声明USB-only必须实物profile有效。默认普通构建路径保持，未格式化/写盘，无OS/VM，本任务不重复USB实施。只四声明文件，独立定向测试后集成。

## 可修改文件

- `tests/test_device_manager.py`
- `tools/build_usb.py`
- `tests/test_usb_profile_packaging.py`
- `codex-works/deliveries/P8USBADAPT1.md`

## 定向验收

- `module:tests.test_device_manager`
- `module:tests.test_usb_profile_packaging`

交付：`codex-works/deliveries/P8USBADAPT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

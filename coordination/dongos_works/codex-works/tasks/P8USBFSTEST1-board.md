# P8USBFSTEST1 — USB容量策略引入后的原FAT坏体夹具适配

负责人：codex。状态：待领取。

P8USBONLY1使fs.fat32显式import lib.hardware_profile，旧FAT三个测试的私有源复制与指纹固定清单缺该默认模块。仅将真实默认模块纳入各source SHA与隔离roots，原坏体算法、错误断言、容量/布局/持久化门一律保持；不改生产源码或物理介质。独立正式复验后本地集成。

## 可修改文件

- `tests/test_fat32.py`
- `tests/test_fat32_paths.py`
- `tests/test_fat32_allocation.py`
- `codex-works/deliveries/P8USBFSTEST1.md`

## 定向验收

- `module:tests.test_fat32`
- `module:tests.test_fat32_paths`
- `module:tests.test_fat32_allocation`

交付：`codex-works/deliveries/P8USBFSTEST1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

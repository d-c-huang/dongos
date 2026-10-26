# P8BSPDIAG1 — S19停留的显式BSP用户态隔离诊断版

负责人：codex。状态：待领取。

用户8CPU Intel新照片S19 USER DOMAIN LOCK/0停留>2min，源码确认S19是最后正常绘屏，不能认定BKL死锁。仅增加显式BSP用户态隔离构建工具及验证/文档，不修改正常kernel/services/EFI生产默认/安全门/超时。复用已完成正常USB-only source，校验完整来源与对象，使用既有services_run.asm -DP6_USER_SMP=0重汇编仅该kernel对象并真实链接/IMG/manifest双消费者EFI。私有EFI源码唯一banner替换为明确BSP DIAG/USER SMP OFF，无地图/策略/错误注入；保留17服务原字节、8CPU平台/SMP自检，legacy CPL3仅BSP用于区分用户SMP交接与共用USB/GUI，不宣称正常多核已修复。输出专门bsp-diagnostic.json并verify，不伪装normal verify_build，不发布故障fixture；原normal无修改。构建命令来自受检正常日志只作数据，严格验证工具/参数/对象来源，不任意执行日志命令。新工具测试真实NASM/链接/有效诊断构建及manifest/单对象差异/原输入稳定，实际坏profile/篡改来源/改变对象/服务字节应拒绝，0skip正式独立。root先实际8CPU原normal完整gate观察，再实际BSP8CPU完整桌面/HID/FS/code/singleUSB/wholeinternal不变，并证明无用户SMP domain、所有8CPU仍存在；root通过后明确仅诊断版备份写原H+fsync/readback/readonlyFAT。用户已将原SanDisk插回H；下次实机成功仅缩窄范围，不代替SMP正常验收。沿既有授权代码/记录推GitHub。

## 可修改文件

- `tools/build_bsp_diagnostic.py`
- `tests/test_bsp_diagnostic.py`
- `docs/hardware-bsp-diagnostic.md`
- `codex-works/deliveries/P8BSPDIAG1.md`

## 定向验收

- `module:tests.test_bsp_diagnostic`

交付：`codex-works/deliveries/P8BSPDIAG1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

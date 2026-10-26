# P8USERTEST1 — 用户态SMP路由测试适配已生效内核源码快照

负责人：codex。状态：待领取。

P8USERDIAG1必要复验发现现存tests.test_user_smp_integration路由断言过期：runtime6/7实际builder早已使用kernel-profile-src/smp_probe.dg完整冻结快照，而测试仍硬编码原kernel/smp_probe.dg路径，报单项失败；实际全图编译/ELFCOFF和其它两项已经通过。仅适配测试断言：核真实入口等于output/kernel-profile-src/smp_probe.dg，字节与当前源一致；对生成完整kernel_storage_profile使用已有verify_profile核全图/sha/0静态表合同；保留真实程序集链接/normalselector/no kernel.elf/builtfalse等原断言。属于用户授权修复的必需测试维护，不改生产builder/内核/期限，不删测试。独立tests.test_user_smp_integration零skip/source稳定、实际源审查后验收集成。旧失败logs保留。

## 可修改文件

- `tests/test_user_smp_integration.py`
- `codex-works/deliveries/P8USERTEST1.md`

## 定向验收

- `module:tests.test_user_smp_integration`

交付：`codex-works/deliveries/P8USERTEST1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

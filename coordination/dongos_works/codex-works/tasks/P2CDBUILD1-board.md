# P2CDBUILD1 — P2CD1 零静态池构建身份适配补登记

负责人：codex。状态：待领取。

P2CD1最终范围审计发现原登记遗漏tests/p2_pcid_build.py，零静态池完整构建身份验证必须由1改为0；本项只补齐该必要适配，不改构建绑定、编译工具或失败条件。父任务隔离副本已保留修改，补登记后纳入移交；独立复验tests.test_p2_pcid_build及父项实际新构建/正负guest，源码稳定零skip后验收。与父项其他已声明profile/oracle适配共同复验，不能单独宣称P2CD1完成。无提交推送，不手改协调器索引。

## 可修改文件

- `tests/p2_pcid_build.py`
- `codex-works/deliveries/P2CDBUILD1.md`

## 定向验收

- `module:tests.test_p2_pcid_build`

交付：`codex-works/deliveries/P2CDBUILD1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P8ECAMTEST1 — ECAM相关既有只读与BAR/DMA探针适配当前依赖ABI

负责人：codex。状态：待领取。

P8ECAM1必要旧回归实际8测试中6错误，保留native-regression.log：readonly旧源副本UTF8/新增configuration_address记录helper缺失、xhci stub memory.DmaLease缺失、AHCI/NVMe native片段硬件profile import缺失。只修4测试夹具依赖，不改生产策略/删除断言/坏体/0副作用及原BAR DMA合同。显式UTF8构建source、真实ConfigurationConflict和helper/或硬件边界等效隔离、DmaLease新ABI和纯getter等接口采用真实定义，hardware_profile默认模块原样复制；保留实际原函数/实际坏体正常执行拒绝，标清没执行硬件的边界。独立4模块定向0skip/source稳定，审查实际assert/原函数不被替换偷放权限后验收集成；旧失败保留。

## 可修改文件

- `tests/test_user_smp_readonly.py`
- `tests/test_xhci_kernel.py`
- `tests/test_ahci_broker.py`
- `tests/test_nvme_broker.py`
- `codex-works/deliveries/P8ECAMTEST1.md`

## 定向验收

- `module:tests.test_user_smp_readonly`
- `module:tests.test_xhci_kernel`
- `module:tests.test_ahci_broker`
- `module:tests.test_nvme_broker`

交付：`codex-works/deliveries/P8ECAMTEST1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

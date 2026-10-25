# P2LMTEST41 — P2本地模型小任务独立夹具校验与接续状态校准

负责人：codex。状态：待领取。

用户继续P2并授权本地LM Studio完成简单任务。Codex编写独立fixture验证器，分别检查GOP页包络已知向量和runtime_cache真实错误常量映射；自测要求正常数据通过、错rounding/overflow/字段/重复ID/错错误码拒绝，LM不可修改验证器。同步P2实际剩余为ledger、C/D实际接线、独立warm-PCID，物理WC真机待验保留；不重复已integrated组件。本项不关闭P2。

## 可修改文件

- `lmstudio-works/tests/p2_fixture_contract.py`
- `lmstudio-works/tests/test_p2_fixture_contract.py`
- `lmstudio-works/tests/test_p2_rounding_vectors.py`
- `lmstudio-works/tests/test_p2_cache_errors.py`
- `codex-works/deliveries/P2LMTEST41.md`

## 定向验收

- `discover:lmstudio-works/tests:test_p2_fixture_contract.py`

交付：`codex-works/deliveries/P2LMTEST41.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

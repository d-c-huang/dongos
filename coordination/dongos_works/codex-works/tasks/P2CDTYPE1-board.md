# P2CDTYPE1 — P2CD1阻塞修复：按PAT×MTRR实际有效类型验证GOP准入

负责人：codex。状态：待领取。

用户授权完成P2CD1剩余修复。实际TCG C完成后D准入0x06150004；原始A硬件BOX证实PAT4=WC且GOP有MTRR UC。既有cache_type_plan.effective_type和Intel SDM表13-7规定PAT WC/MTRR UC实际仍WC、PAT UC实际UC。runtime_cache独立硬编码MTRR必须WB过窄，与已验收有效类型规划不符。按每页解析MTRR，再用既有effective_type分别证明WC、UC两轮目标，不修改PAT/MTRR或放宽保留位/未知类型/冲突/每CPU原始相等/期限/持有。新增UC/WT/WP/WC/WB原始MTRR正常模型和非法/重叠冲突/变化拒绝，真实生产坏体防止恢复WB-only或绕过有效类型判断；独立0skip源码稳定审查后集成。原错误不重标通过，主P2CD1仍待C/D客体正负证据；无提交推送。Intel依据https://cdrdv2-public.intel.com/868137/325462-089-sdm-vol-1-2abcd-3abcd-4.pdf 表13-7。

## 可修改文件

- `kernel/mm/runtime_cache.dg`
- `tests/runtime_cache_probe.c`
- `tests/test_runtime_cache.py`
- `docs/runtime-cache.md`
- `codex-works/deliveries/P2CDTYPE1.md`

## 定向验收

- `module:tests.test_runtime_cache`

交付：`codex-works/deliveries/P2CDTYPE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

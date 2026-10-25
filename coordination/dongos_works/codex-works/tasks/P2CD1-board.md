# P2CD1 — P2 C/D生产接线接手、零静态池适配与独立客体验证

负责人：codex。状态：待领取。

用户明确授权接手Claude独立worktree P2CD1，完成剩余修复与独立复验，通过后真实集成和更新进度。保留Claude原交付/补丁，冻结主目录基线应用补丁。审查B/C/D mux及C真实buddy/entry/trace绑定、D账本/资源/期限；错误fail-stop，不弱化根森林、缓存类型、池身份和源码绑定。修复runtime7零静态池oracle/runner/合成夹具语义、四类SMP夹具、runtime5/6构建预算回归，不扩大2MiB。全新release构建；宿主组件/接线/真实坏体零skip稳定。root协调者按用户本次授权运行受控QEMU取得C/D正负客体证据，执行者不自行启动VM。实际正负证据未过不得验收集成，不将warm-PCID或物理WC真机门标完成。额外组件缺陷需另明确范围；无提交推送。

## 可修改文件

- `kernel/user/services.dg`
- `kernel/user/memory.dg`
- `kernel/build/storage_profile.dg`
- `tools/build.py`
- `tools/kernel_storage_profile.py`
- `tests/test_user_smp_services.py`
- `tests/test_kernel_storage_profile.py`
- `tests/test_user_smp_poll_fast.py`
- `tests/test_user_smp_poll_wakes.py`
- `tests/test_user_smp_readonly.py`
- `tests/test_user_smp_fault_isolation.py`
- `tests/p2_pcid_oracle.py`
- `tests/run_p2_pcid_qemu.py`
- `tests/run_p2_runtime_large_qemu.py`
- `tests/p2_bulk_capture.py`
- `tests/test_p2_runtime_large.py`
- `tests/test_p2_pcid.py`
- `tests/test_p2_historical_capture.py`
- `tests/p2_runtime_large_build.py`
- `tests/test_p2_bulk_capture.py`
- `tests/test_p2_pcid_build.py`
- `tests/test_p2_cd_wiring.py`
- `tests/run_p2_cd_qemu.py`
- `docs/p2-cd-wiring.md`
- `codex-works/deliveries/P2CD1.md`
- `codex-works/reviews/2026-10-24-P2CD1.json`

## 定向验收

- `module:tests.test_p2_cd_wiring`
- `module:tests.test_kernel_storage_profile`
- `module:tests.test_user_smp_services`
- `module:tests.test_p2_runtime_large`
- `module:tests.test_p2_pcid`
- `module:tests.test_p2_historical_capture`

交付：`codex-works/deliveries/P2CD1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

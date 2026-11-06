# P6VERIFYADAPT1 — [P6] 旧DAG/KVM验证工具适配当前构建与页池契约

负责人：cursor。状态：待领取。

独立只读审查旧origin/codex/p6-input-irq-kvm-validation：真正差集为6个验证/文档文件，IRQ修复已在main，不复制旧input_service覆盖USB-only新逻辑。提取完整候选并记录分支/文件SHA。阻断1：verify_manifest强制恰好5产物，当前runtime7有7项及storage profile，须完整验证新增优化回执/生成源码图而非仅放宽数量。阻断2：InitialGuest调用当前validate_private_pools/verify_process缺uses_static_pool，去掉pid<4旧假设，依据可信profile。阻断3：workflow硬编码EDarcyWong/dongos PR#3，当前d-c-huang/dongos会跳过；明确门未执行不能计通过，不能继承旧临时KVM组权限授权。保留实际query-kvm、禁止TCG替代、连续启动保守500ms上界、首代双AP/CPL3/STARTING/init回执/trace连续门。补完整当前build回执和缺方法/旧假设负控。只宿主测试，Cursor手动；独立审查/正式复验/真实迁移后由协调者在合适Linux/KVM环境实际跑，历史未捕获窗口/权限前置失败保留，不提前关闭P6。

## 可修改文件

- `cursor-works/src/p6/validation/run_p6_initial_dag_qemu.py`
- `cursor-works/src/p6/validation/run_p6_kvm_qemu.py`
- `cursor-works/src/p6/validation/p6.yml`
- `cursor-works/src/p6/validation/p6-current-validation.md`
- `cursor-works/tests/test_p6_initial_dag.py`
- `cursor-works/tests/test_p6_kvm_runner.py`
- `cursor-works/deliveries/P6VERIFYADAPT1.md`

## 定向验收

- `discover:cursor-works/tests:test_p6_initial_dag.py`
- `discover:cursor-works/tests:test_p6_kvm_runner.py`

交付：`cursor-works/deliveries/P6VERIFYADAPT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

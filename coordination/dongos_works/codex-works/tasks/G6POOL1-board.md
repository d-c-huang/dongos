# G6POOL1 — G6 当前静态/动态页表池独立检查适配

负责人：codex。状态：待领取。

G6RUN2 实跑 run-662c6cec8a01 已完成编译与服务退出，但旧 P5 检查器固定前三进程均为静态池，拒绝当前 storage_profile 的动态 block 池。核对构建 profile 与真实物理记录，严格证明页表池容量、arena 归属、映射及互斥；保留失败原件，不放宽跨池检查。增加正负控并独立定向复验；G6 双启动另由 G6RUN2 重新运行。

## 可修改文件

- `tests/run_services_qemu.py`
- `tests/test_services_pool_ownership.py`
- `codex-works/deliveries/G6POOL1.md`

## 定向验收

- `module:tests.test_services_pool_ownership`
- `module:tests.test_compiler_guest_runner`

交付：`codex-works/deliveries/G6POOL1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

# P6BKLBRIDGE1 候选契约

基线 `kernel/sched/user_bridge.dg` SHA256: `32e9b1876c4e2a2fdd6f02a547af26f1794e0eb2a965c4f9af3b07d8716663f4`。

候选是完整生产 Bridge 副本，只新增 user_bkl import、发布 ACTIVE 前一次 bind，替换 capture/idle 两处 acquire 及 choose 两处 unlock。Domain、Cpu、Bridge、诊断结构及原绝对期限不变。bootstrap 保持原 Domain acquire/unlock；retire/global_barrier 复用外层票，不二次排队。错误继续进入既有 held 路径，不取消票、不恢复失败 Domain。

候选本身不证明实际桌面超时由不公平引起，也不保证长临界区在期限内完成。需独立审查、正式宿主复验、真实迁移后，再由协调者以当前完整源码构建并执行 USB/P5 客体回归；PCID/WC/KVM/真机阶段门不因此关闭。

测试将完整生产 Bridge/Domain/FIFO/queue 编译为 debug/release 原生程序。沿用真实入口夹具的合成硬件边界，并在每个实际 event/idle 周期检查票号和 Domain 所有权；覆盖两条获取路径、空闲/用户返回解锁、bootstrap 原锁、嵌套 barrier/retire 和 fail-closed。遗漏绑定、各单独接线、全体旁路及嵌套重入均用实际坏 Dong 编译运行拒绝。宿主通过不等于实际 AP/CPL3/VM 通过。

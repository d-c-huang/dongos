# P5 映射退休候选契约

本目录是待审候选，尚未集成生产代码。memory.dg 与 device_host.dg 以当前主线为完整基线，只新增标记段及 memory 的调度依赖：memory 基线 SHA256 `5f7bb7f5aee5f917093ae13eb474f4c71570a01dad88fd9e4638d36ce1614ba6`，device_host 基线 `3c57c8101c89284a8d082f894d2255ba12322767dd2d8add46cb95dd80a4a4e4`。

## 授权与前置

显式内核续接入口 `device_host.dma_retire_mappings(slot)` 只读取实际 DmaContext 和设备 ledger，不接受用户提供的观测。必须是原 slot/configuration、owner/incarnation、原 token/device generation、真实撤销后 generation、原 memory root/generation；stop/SMP retire/IRQ route/isolation/acquire/snapshot 全部成功且无错误，设备同一硬件身份已 revoked。drain 必须仍为 unknown=0、held=1。本入口不改变普通 manager REVOKE 流程，没有新增用户 syscall。

内存侧再次核对实际 DmaLease 的全部字段、PINNED、ready root 和独立 memory generation。只支持物理地址非零、对齐、1–128 页二次幂、attempted=mapped=pages 的 DMA_COMPLETE 全块；任何 partial、physical=0、大小/地址异常均拒绝。部分申请及未获物理页的失败租约继续永久持有，不猜测已提交页集。

必须有实际 runtime7 Bridge/Domain，当前处于 kernel CR3、BSP 持有 BKL、IF0，BSP capture 已 drain。使用现有 `user_domain.drain(d,0)` 的受检空 capture 路径验证实际 CPU/IF/BKL；capture 非零先拒绝，因此不会在预检中消费 capture。旧 Domain process 同 incarnation、token/root 已清空、无 retiring；在线 CPU 无旧 slot，其他 active process 无旧 root。旧完成序列只能作为 before，绝不能复用为新成功凭据。

## 完整映射检查与动作

使用生产 snapshot_roots/runtime_roots.audit，枚举实际整片页表森林，包括 ready/preloaded/pinned 地址空间及共享内核树。完整 DMA 物理块的每一页必须恰有记录中的 supervisor alias 和指定 owner user alias；逐页核对 Frame/RECYCLED=2、VA/PA、root/generation、WRITE/USER 属性、唯一性和完整性。未知 4K/2M alias、遗漏页、重复别名、森林格式/容量问题全部拒绝，退休预检不修改任何页表、allocator、租约或退休状态；audit仅写预先准备的私有工作区。

独立资源准备入口 `device_host.dma_prepare_retirement(slot)` 使用与退休入口相同的真实Context/ledger、完整租约与BSP/IF0/BKL/停机检查，在调用永久arena分配前锁存每slot唯一尝试。分配可能reserve后失败；此时尝试仍永久锁存，后续prepare与退休均拒绝，部分分配效果永久持有。准备阶段明确允许allocator/PTE变化，不属于退休事务。准备成功绑定root/generation/incarnation/pages；重复prepare无论成功或失败都拒绝。

`dma_retire_mappings` 不调用allocator，未准备或绑定不符拒绝。私有 scratch/receipt 来自先前准备，alias拒绝后仅私有audit工作区可能改变。成功快照后再次核对 roots 与停止状态，记录 state=1，再逐页调用真实 paging.unmap_live。每页 Retired receipt 永久保存，包含零 table-count 的 pending receipt。

所有 user PTE 撤销后才调用真实 `user_shared_barrier`。必须返回 1，Domain 指针和 online mask 不变、sequence 恰为 before+1、completed 相等，所有 online CPU requested/acknowledged 都是新 sequence、旧 slot Seen.valid=0。最后 query 确认每页精确 NotMapped；成功记录 state=3/after。即使汇编走到旧 UP fallback，没有新 Domain sequence/逐核回执也不能满足成功条件。

开始 mutation 后任何 unmap/barrier/回执错误进入 state=2，保存错误码和已撤页数。重复调用拒绝，不回滚、重绑或重用部分资源。完整成功同样不能重复执行。预检失败 state 保持 0，DMA 映射/lease/frame/pin 不变。

## 永久持有与证据边界

本实现不调用 paging.reclaim，不回收 table receipts，不清零 DMA 数据，不释放物理块，不清 PINNED，不将 Frame 标成可复用，不生成 drain=0 证明或新 token。成功仅表示用户映射已撤销并取得新的 CPU 翻译确认；设备在途 DMA 仍未知，因此 DMA 和页表存储持续隔离。pending metadata 可能使后续全森林操作安全拒绝，这是有意保守的单次退休限制，不是可重启恢复方案。

原生测试编译完整候选 module closure，执行真实 memory/host/paging/runtime_roots；仅替换 arena 分配和硬件边界，fixtures 在编译暂存区初始化真实私有状态。独立 C walker 直接遍历实际 PTE，检查撤销前后、supervisor aliases 保留、整份 lease/frame/recycled 不变、PINNED 保持及 pending table metadata。覆盖正常、8 类 host、10 类 memory（含其他 pinned root）、5 类 Domain、5 类屏障、4 个逐页故障点；三类真实坏 Dong（遗漏 ACK、遗漏完整 alias 检查、取消分配尝试锁存）须返回断言退出 1，panic/崩溃/超时不能当负控成功。debug/release 均执行；另编译无边界替换的生产依赖图。

完整 Dong 编译后，原生链接保留 fixture 出口、静态函数指针及其传递符号依赖的 可达函数原始汇编体，不可达函数入口替换为 ud2；静态数据原样保留。完整编译汇编及 reachability.json 同时归档，受测函数不被改写。这个收缩避免本机 NASM 汇编全量无关模块时超时；若错误地到达陷阱入口，进程崩溃导致测试失败，不会算作负控通过。无测试边界替换的完整生产依赖图仍在两模式下编译检查。

宿主屏障由 C 模拟真实 Domain/CPU 状态的结果，不能证明硬件 INVPCID/IPI 运行。本任务不启动 OS/VM，不声称硬件 DMA drain、物理安全回收、驱动重启或 P5 全阶段完成。真实调用点集成、客体/真机验证及非作者源码审查仍待后续。

返修回归另含未prepare、准备分配失败重试、全部host/Domain准备拒绝、同步Context的partial/physical0；退休前后核对allocator计数、完整kernel/owner/其它root页表及租约帧pin。

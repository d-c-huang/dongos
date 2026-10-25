# P2 C/D 实际接线（B/C/D poll mux、C 生产 bind、构建接线）

本项把已集成的 C（`mm.runtime_exec` + `sched.runtime_exec_entry`）和 D
（`mm.runtime_cache`）组件接到 `user.services` 的正常调度后路径。组件本身未改；
B（`mm.runtime_large`）的 `large_try`/`large_identity`/`large_check` 逐字保留。
未启动 VM，客体正负证据、warm-PCID 实际复用和物理 WC 性能不由本项证明。

## 一次性 B/C/D mux

`enable_smp` 仍在 AP 用户准入前分配 B 存储，但现在一次性注册
`runtime_poll` 而非 `large_poll`。`user_domain.poll` 保持 legacy 检查在前、
flush ACK 由 Domain 独占。mux 依次调用 B、C、D：

- B：`large_poll`，与原注册行为相同（未 ready 返回 0）。
- C：`exec_poll`，`RUNTIME_EXEC` 为空时跳过，否则调用 `runtime_exec.poll`。
- D：`cache_poll`，`RUNTIME_CACHE` 为空时跳过，否则调用 `runtime_cache.poll`。

第一个非零返回值原样返回，Domain 随即 fail；mux 不递归调用 `Domain.poll`、
不代替组件 ACK、不重试。`RUNTIME_EXEC`/`RUNTIME_CACHE` 只在对应组件 bind（C 还
包括 trace 与 PF entry 注册）全部成功后，经 `compiler_fence` 发布。

## 触发顺序与 BKL 占用

C/D 复用 B 的生产触发：slot0 shell 已提交的五个普通应用启动使 B 运行。
`dong_user_smp_project` 在调用 `large_try` 前记录 B 是否已经 `complete==1`；
只有在比完成 B 更晚的一次 projection 中才进入 `owner_try`。`owner_try` 每次
projection 至多推进一个 owner：先 C，C 完成后的下一次 projection 再 D。因此
没有一次 BKL 持有跨越两个事务。任何 bind/run 错误与 B 相同：置 bridge/Domain
failed 并返回，不恢复用户、不选择 legacy 回退。未请求 B 的启动不进入 C/D。

每个 owner 使用独立的新 `LargeTicket`（`owner_ticket` 重新 `snapshot_roots`
并冻结 Catalog/Domain/root 身份，再经 `large_identity(frozen)` 核对），不复用
B 的历史冻结数组。各 owner 存储由 `boot.service_memory` arena 分配，BSS 只保存
指针。

## C 生产 bind

`exec_try` 依次：

1. 分配 `ExecStorage`（Context、ticket、order0 PA、trace Block）并发布存储指针；
   另行分配 4 页（32×512 B）独立 trace Block，保存其 Block 收据。
2. `owner_ticket` 冻结新 ticket。
3. `buddy.alloc(startup allocator, 0)` 取得真实 order0 buddy 租约；组件没有
   transfer/free API，租约在完成后保持 held。
4. `runtime_exec.bind`：真实内核 Space/allocator、ticket 的完整 root 快照、
   `exec_check`、`runtime_exec_hardware`/`runtime_exec_action` reader、CPU0
   Header 的 `deadline_ticks`。
5. `runtime_exec_entry.bind_trace` 绑定上述独立 Block，headers 为 `user_boot`
   发布的真实 16 项 Header 指针表（离线项为 0）。
6. `runtime_exec_entry.bind`（生产 API，内部读取真实 GS/CR0/CR3/CR4/RFLAGS
   快照；不使用 host `bind_snapshot`），generation 固定为 1，callback 为
   `runtime_exec_entry.dispatch`。
7. 发布 `RUNTIME_EXEC` 后 `runtime_exec.run`。

`exec_check(cookie)` 只接受本 ticket 地址，重新执行 `large_identity(frozen)`
（含 `memory.recheck_roots` 完整 16 槽重枚举、Catalog/Domain/队列核对），再核对
Context 内 root 副本与 ticket 快照逐项一致。

## D 生产 bind

`cache_try` 仅在 `GRAPHICS` 下运行；每个 Domain 只尝试一次：

1. 首次分配 `CacheStorage`（Context、Work、Config、ticket、FramebufferSnapshot、
   Page Block）。
2. `cache_freeze`：新 ticket + `memory.snapshot_framebuffer`（真实 forest 审计与
   独立账本相等）。账本少于 2 项（尚无私有 compositor alias）时本次跳过，不分配
   收据、不报错。
3. 按账本实际页数（全部 alias 的 bytes/4096 之和，≤`MAX_LINEAR`）分配 `Page[]`
   收据区。分配会建立新的内核映射，因此再冻结一次，并要求页数不变。
4. Config：真实内核 Space、`runtime_boot_info` 的 BootInfo、ticket 根集合、账本
   快照、收据区、Work、`kernel_framebuffer_gate_get()` 的永久 Gate、
   `memory.framebuffer_epoch_pointer()`、`cache_check`、`runtime_cache_hardware`
   和 CPU0 `deadline_ticks`。
5. `runtime_cache.bind` 成功后发布 `RUNTIME_CACHE`，再 `runtime_cache.run`。

`cache_check` 只接受本 ticket、本 ticket 的 root 数组与本快照的 ledger 数组，
重新执行 `large_identity(frozen)` 与 root 副本比较，再调用
`memory.recheck_framebuffer` 重核已发布授权、epoch 及账本记录的 root 集合（该
recheck 不要求事务中 PTE 仍为 WC）。

## 构建接线

`user.services` 在 runtime≥5 的全部图中导入 B/C/D，因此 `tools/build.py` 在同一
runtime≥5 分支各链接一次 `kernel/sched/runtime_exec_reader.asm` 与
`kernel/sched/runtime_cache_reader.asm`。`runtime_exec_entry` 的 `user_smp_exec_*`
来自已链接的 `user_entry.asm`；Gate getter 来自 `entry.asm`。Dong 侧没有重复
声明这些共享 ASM extern。

## 2 MiB 预算

C/D 新增约 131.6 KB 代码（runtime_cache 54 KB、runtime_exec_entry 31 KB、
runtime_exec 31 KB、services 接线 9.7 KB、memory 已有但此前被 GC 的账本函数
4.7 KB），编译器已是 release+O1+函数分节+链接 GC；runtime7 原余 118,384 B，首次
完整构建超出窗口 20,880 B。经用户决定，沿用 P2SIZE10 先例：runtime7 的
`STATIC_USER_POOLS` 由 1 改为 0，最后一个 32 页静态用户页表池改走已有 arena
动态池路径（与 pid≥1 相同的 `prepare_tables` 分配、零初始化与物理归属）。

Dong 不允许零长度数组，因此 profile 另外显式给出 `STATIC_TABLE_SLOTS` 与
`STATIC_TABLE_PAGES`：有静态池时为 (count,32)，与原布局相同；零池时为 (1,1) 的一页
占位。`uses_static_tables()` 额外要求 id 小于槽数且每槽页数等于 `POOL_PAGES`，零池
时永不选中占位页。默认源 profile 与 runtime0..4 的静态池数和对象大小不变。Codex接手后，runtime5/6同样采用零静态池，避免C/D导入带来的窗口回归；三个服务级别均使用既有prepare_tables动态池路径。

完整 release runtime7（339 输入，source_unchanged=true）：kernel.bin=1,991,056 B，
2 MiB 窗口余 106,096 B。runtime5/6 在未改动的主线上本已超窗（runtime5 基线超
8,592 B），本项不处理。

## 宿主夹具

`tests.test_user_smp_services` 现抽取真实 `runtime_poll`，C/D slot 与
`owner_try` 为计数桩：B 未武装时 mux 必须到达 C/D slot、`owner_try` 不得被调用。
新增两个坏体：mux 跳过 C slot、在 B 未完成时进入 owner。两种模式下 6 个正常与
24 个坏体执行。

`tests.test_kernel_storage_profile` 改为 runtime7 零池：实际 ELF64/COFF 对象中
`TABLES` 分别为 393216/4096/4096/4096 B，Process/Frame/Space/Allocator 布局
不变。`tests.test_framebuffer_ledger` 使用 runtime7 profile 编译真实 user.memory，
零池下通过。

## Codex 接手后的构建与验证

runtime5/6/7 均使用零静态池，runtime4 保留三个静态池。源码绑定的 PCID、历史采集、bulk 和大页 runner/oracle 已同步零池语义；slot0 也必须由实际 service arena 分配，物理区间、虚拟指针、代次和分配回执一致，拒绝旧静态池身份。四类 focused SMP 夹具补齐真实 mux/LargeStorage/RootSnapshot 依赖；夹具明确保持 B 未武装，不能作为 C/D 客体完成证明。

`tests/run_p2_cd_qemu.py` 提供显式 build/execute/replay。构建冻结生产源码、五个实际工作负载 overlay、编译工具、布局、ELF、服务 bundle 和启动镜像。两种负例分别只移除生产 exec/cache poll，并记录实际执行标志。不得以合成状态替代运行。

启动审计复用已封存 bootstrap 历史镜像，不额外暂停。关闭四个 GUI 和启动五个工作负载通过原有 slot0 UART 协议连续执行，不在命令之间暂停。回放逐份检查 UART 新鲜 echo、prompt、字节边界、hash 和次序；初始及最终 Catalog 以实际 ELF 地址读取，GUI 只允许同代次 KILLED，核心服务身份保持。完成采样只读，并保留原有 stop-to-cont 预算、AP/Domain/Barrier 期限；允许在正常调度屏障内采样后继续运行寻找空闲采样点，失败状态和超时不能重标成功。

正例需同时证明 C/D complete、无 poison、held；C 的 13 次屏障、两份消费回执、页表数恢复、四 CPU 42/43 调用及拒绝写入、原始 PF 与 ticket 消费；D 的 5 次屏障、两轮类型切换、每 CPU 五次读取和两次维护、完整撤销/回收/重映射页数。负例要求实际 marker、首次 STORE/READ 阶段、C 仅 BSP STORE 请求1、其它 CPU 请求0，D 四 CPU READ 请求1，全部 ACK0、精确 BSP 投影失败链、Domain failed 且 held 保留。若 owner 本地期限先到，要求精确 Timeout/Deadline；若 AP 等锁期限先到，C 记录 Reader、D 透传 Domain Held，且必须另有实际 AP WAIT 记录证明 wait_started < deadline <= clock、acquired=0、原 owner/lock 和精确 Timeout。任意错误、未到期记录或无关联失败均拒绝。原始内存与寄存器来自同一有界 epoch，离线重放校验完整来源。

P2CDTYPE1 已独立验收集成，修复 D 把原始 MTRR WB 误作唯一有效 WC 条件的问题；按既有有效类型规划器和 Intel SDM 表13-7分别证明目标 WC/UC，保留 MTRR 冲突、每 CPU 原始状态、维护和期限检查。组件模型验证不替代实际客体门。

## 范围边界

本项不代表 warm-PCID 实际复用或物理 WC 性能/真机门通过。最终构建、客体正负证据、正式独立复验与集成状态以 P2CD1 交付和协调器登记为准。失败诊断和 Claude 原始交付均保留。

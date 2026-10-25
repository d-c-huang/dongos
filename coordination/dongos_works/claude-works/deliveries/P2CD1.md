# P2CD1 交付：P2 C/D 实际接线（B/C/D mux、C 生产 bind、构建接线）

- 授权：用户 2026-10-24 在 Claude 客户端明确授权“直接实现 P2 C/D 实际接线（B/C/D mux、C 的生产 bind、构建接线），在独立 worktree 里做，不自行验收或集成”。协调器中没有对应任务卡，本交付未经 claim/submit；状态为**待 Codex 复验**，不是验收或集成。
- 预算决定：首次完整构建超出 2 MiB 窗口 20,880 B，经用户选择“静态池 1→0（沿用 P2SIZE10 先例）”。
- 工作位置：worktree `D:\projects\2026\dongos-p2cd`（分支 `claude/p2-cd-wiring`，基于 HEAD 4e3e0b8，并逐字节复制了主目录 code/ 的全部未提交改动作为基线）。主目录 code/ 未被修改。没有提交、推送，没有启动 VM。
- 补丁：`claude-works/deliveries/P2CD1.patch`，相对主目录当前工作树，`git apply --check` 通过（未应用）。
- 契约说明：`code/docs/p2-cd-wiring.md`（含在补丁中）。

## 修改文件（相对 code/）

| 文件 | 内容 |
|---|---|
| `kernel/user/services.dg` | 一次性注册 `runtime_poll`（B→C→D，首个非零返回原样上报）；`exec_poll`/`cache_poll` 只在发布指针后调用；`owner_ticket`/`owner_roots`/`exec_check`/`cache_check`；`exec_try`（真实 order0 buddy 租约、`runtime_exec.bind`、独立 4 页 trace Block 的 `bind_trace`、生产 `runtime_exec_entry.bind`）；`cache_freeze`/`cache_try`（按实际账本页数分配 Page 收据，分配后再冻结一次）；`owner_try`；`smp_project` 只在比完成 B 更晚的 projection 中、每次至多推进一个 owner。B 的 `large_try`/`large_identity`/`large_check` 文本未改。 |
| `tools/build.py` | runtime≥5 分支各链接一次 `runtime_exec_reader.asm`、`runtime_cache_reader.asm`。 |
| `tools/kernel_storage_profile.py` | runtime7 静态池 1→0；新增 `static_table_shape` 及生成的 `STATIC_TABLE_SLOTS`/`STATIC_TABLE_PAGES`。 |
| `kernel/build/storage_profile.dg` | 默认 profile 增加 (3,32) 两个形状常量，静态池数不变。 |
| `kernel/user/memory.dg` | `TABLES` 由 profile 形状决定；`uses_static_tables` 额外要求槽号和每槽页数。 |
| `tests/test_user_smp_services.py` | 抽取真实 `runtime_poll`；C/D slot 与 `owner_try` 为计数休眠桩；新增坏体 `mux-skips-exec-owner`、`owner-before-settled-large`；期望 30 次执行（6 正常 + 24 坏体）。 |
| `tests/test_kernel_storage_profile.py` | runtime7 期望零池（TABLES 4096 B 占位）。 |
| `docs/p2-cd-wiring.md` | 新增接线契约。 |

## 实际执行（均在 worktree）

1. 基线 runtime7 构建（修改前）：成功，kernel.bin=1,978,768 B（与 P2LEDGER44 记录一致）。
2. 接线后 runtime7 首次构建：编译和链接成功，`materialize` 拒绝（超窗 20,880 B）。新增代码约 131.6 KB：runtime_cache 54,192 B，runtime_exec_entry 31,104 B，runtime_exec 30,816 B，services 9,680 B，memory 账本函数 4,704 B（此前未被引用、被 GC 掉的代码）。
3. 改 profile 后 runtime7 完整 release 构建：成功，339 输入，source_unchanged=true，kernel.bin=1,991,056 B（余 106,096 B）。
   - kernel.bin SHA256 `6c98866cec8f449f341e7f2c8c2e195f54b51d51bf5553a6e4fdaf0bf439c5b1`
   - kernel.elf SHA256 `209f0012962a9c22a051b7bf3a8e5e0dbcbfb59c4ff1cd904b0ca99ea78bfe60`
   - DONGOS.IMG SHA256 `06a2453f8bc2f6aee9894c645900b0cf9d38653753b756c3c1941010743069d1`
   - 输出在 scratchpad，未保留到仓库。
4. runtime5/6 接线后构建：链接成功但超窗 147,856 B。**未改动的主线 runtime5 本已超窗 8,592 B**（实际构建确认），属于既有问题，本项不处理。
5. `python -B -X utf8 -m unittest tests.test_user_smp_services -v`：1 test OK（324 s），证据 `build/test/p6-cpl3-service-native/run-f55dd368994e`（worktree）。该测试在改 profile 之前运行；其 memory 为夹具桩，与 profile 无关；之后 services.dg 未再改。
6. `python -B -X utf8 -m unittest tests.test_kernel_storage_profile tests.test_framebuffer_ledger -v`：4 tests OK（177 s），证据 `build/test/kernel-storage-profile/run-ba5eb44ad9cf`、`build/test/framebuffer-ledger/run-505a1f60c83c`（worktree）。
7. `tests.test_user_smp_poll_fast`：编译期 `unknown type 'LargeStorage'`。该类型在本项之前就已存在，因此推断这四个夹具（poll_fast/poll_wakes/readonly/fault_isolation，均未包含 B 的 DORMANT 声明）在本项之前就已无法编译；未在未改源码上单独复跑确认。

未运行：component 测试（runtime_exec/entry/cache/framebuffer_gate，组件未改）、test_p2_runtime_large、test_p2_pcid、任何 QEMU/客体 runner、完整回归。

## 已知后果与待办（交 Codex）

- **客体工具需同步零池 profile**：`tests/p2_pcid_oracle.py`（`pool_identity`、`decode_snapshot` 断言 `static_pools==1`）、`tests/run_p2_pcid_qemu.py`（`==1`）、`tests/run_p2_runtime_large_qemu.py`（`validate_pool_provenance` 要求 >0）、`tests/p2_bulk_capture.py`（binding `static_pools=1`）、`tests/test_p2_runtime_large.py`（构建断言 1）及 `tests/test_p2_pcid.py`、`tests/test_p2_historical_capture.py` 的合成数据。我曾试改计数常量，因涉及合成数据中“slot0 在静态池”的语义而撤回，这些文件保持主目录原字节。
- **B 既有客体 runner 期望变化**：B 完成后的下一次 projection 现在会运行 C，再下一次运行 D；任何 bind/run 失败都会 fail-stop Domain。
- **需要客体验证的风险点**：pid0 改用 arena 动态池；C 需要启动 buddy（1024 页）中仍有空闲 order0；D 需要 QEMU GOP 的 MTRR 为 WB（runtime_cache 的准入要求）；D 事务较长（约 4,000 页撤销/回收/重映射两轮 + 两轮 WBINVD），AP 等待 BKL 的期限可能不足。
- warm-PCID 实际复用、物理 WC 性能和真机门不在本项范围。

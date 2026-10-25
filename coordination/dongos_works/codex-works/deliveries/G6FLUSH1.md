# G6FLUSH1 恢复后的复核与替代关系

2026-10-24（北京时间）。本轮恢复并领取旧卡后，查明原问题已由后继 G6WAIT2 实现、独立验收并集成；G6RUN2 已使用修复后新构建完成真实同盘双启。G6FLUSH1 原共享 Ops 扩张设计没有实施，不把后继显式 timed API 方案冒记为原设计验收。

## 源码与契约审查

- `virtio_blk.dg` 的 timed read/write/flush 在发布前取时，使用同一 5000ms 差值截止，拒绝时钟失败、倒退与连续 100000 次不进展；完成字段验证后再次检查时间。
- 发布后的超时与时钟错误保持 fault/published/held，迟到完成不能恢复 ready；DMA 仅在真实 reset 成功后释放。
- `block_service.dg` 的三个生产操作均使用 timed 入口和已有 milliseconds。State/Ops/Lease 保持 288/40/32B，tablet 共享 ABI 不变，真实 FLUSH/cache 配置和 G6/P2 期限不变。
- 当前 G6WAIT2 七个交付文件的 SHA256 全部匹配其正式复验指纹（作业 e8510c2b91054ebe941e0c6d0eec57af，4 项、零 skip、源码稳定）。原 G6FLUSH1 暂停记录由 G6WAIT2 替代的事实也已写入 G6RUN2 原审查报告。

## 本轮实际测试

协调器 snapshot 函数生成独立源码副本：`coordination/dongos_works/.local/manual/G6FLUSH1-20261024/workspace`，1604 文件；测试前后源码清单完全一致。

命令：`python -m unittest tests.test_virtio_blk tests.test_virtio_tablet tests.test_compiler_guest_runner -v`。

结果：22 项通过，46.082 秒，零 skip。包含 debug/release 下原 13 个块设备场景、新增 11 个计时场景、五类实际生产坏体、ELF/COFF、布局/栈检查，以及 tablet 回归和 G6 runner 门禁。runner 测试末尾两条 `L3 actual guest FAIL` 是预期的故障回执测试输出；对应测试通过，本轮没有启动真实 OS/VM。

机器可读摘要：`coordination/dongos_works/.local/manual/G6FLUSH1-20261024/verification-summary.json`；模型逐场景构建/运行回执位于该副本的 `build/test/p5-virtio/host/` 与 `build/test/virtio-tablet/host/`。

## 已有真实客体证据与处理结论

G6RUN2 integrated rev6：run-b54a8a8d615b 同盘两启通过，原独立审计每启 961 个原始文件、FAT 固定点及 128 页退休闭合；正式 runner 复验 15 项零 skip。证据保留于 `codex-works/reviews/2026-10-23-G6-current-run.md/json`，本轮没有重跑客体，也不把宿主回归当作新的双启证据。

本轮不新增生产源码修改。保留用户对必要 ABI 适配文件的范围授权，但现有已验收方案无需这些适配。旧卡应以“已被 G6WAIT2/G6RUN2 替代”归档，保留本轮复核与测试记录，不重复标记原 Ops 扩张设计 accepted/integrated。正式协调器定向复验另见任务作业记录。


## AI交付 2026-10-24T09:58:34+00:00 · codex-mcp-5f95564a50c4415d

恢复复核发现此卡已被 G6WAIT2 integrated rev6 显式 timed API 方案替代，G6RUN2 integrated rev6 已完成新镜像同盘双启；原共享 Ops 扩张设计不实施、不冒记验收。实际审查生产计时/DMA持有及接线，G6WAIT2七交付文件SHA全部与正式复验指纹一致。本轮协调器snapshot隔离副本1604源码稳定，python -m unittest tests.test_virtio_blk tests.test_virtio_tablet tests.test_compiler_guest_runner -v：22项/46.082秒/0skip通过，含两模式24块场景、5坏体、ELF/COFF及tablet回归。本轮无生产源码修改、未运行OS/VM、未提交推送。详细真实交付见本任务交付报告；请求定向复验后以被后继替代归档，不将原ABI方案标为accepted/integrated。

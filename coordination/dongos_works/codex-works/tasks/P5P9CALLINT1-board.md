# P5P9CALLINT1 — [P5/P9] 集成故障生命周期续接与有界日志传输

负责人：codex。状态：待领取。

在P5DMACALL1和P9RAWTRANSPORT1独立审查及正式复验验收后领取。P5候选services/host逐字到生产，三测试文件改生产路径；P9五源码逐字迁入独立log_transport包，补__init__，测试固定生产路径并重新生成真实ELF/身份。更新文档已接线与日志边界，保留初审BLOCK闭环、非作者指纹及实测。未参与实现者分别复核迁移及生产tests，再正式定向零skip源稳定复验；真实文件迁移后才登记integrated。保留既有改动，不运行OS/VM、不提交推送，不关闭P5/P9硬件/客体阶段。

## 可修改文件

- `kernel/user/services.dg`
- `kernel/user/device_host.dg`
- `tests/test_p5_dma_call.py`
- `tests/p5_dma_call_fixture.dg`
- `tests/p5_dma_call_probe.c`
- `tools/guest_corpus/log_transport/__init__.py`
- `tools/guest_corpus/log_transport/corpus_guest.dg`
- `tools/guest_corpus/log_transport/corpus_entry.asm`
- `tools/guest_corpus/log_transport/corpus_log.dg`
- `tools/guest_corpus/log_transport/corpus_log.py`
- `tools/guest_corpus/log_transport/build_log_corpus.py`
- `tests/test_corpus_log.py`
- `docs/p5-dma-retirement.md`
- `docs/guest-corpus.md`
- `codex-works/reviews/P5P9CALLINT1.md`
- `codex-works/deliveries/P5P9CALLINT1.md`

## 定向验收

- `module:tests.test_p5_dma_call`
- `module:tests.test_p5_dma_retire`
- `module:tests.test_p5_recovery_context`
- `module:tests.test_corpus_log`
- `module:tests.test_guest_corpus`
- `module:tests.test_syscall_corpus`
- `module:tests.test_framebuffer_ledger`

交付：`codex-works/deliveries/P5P9CALLINT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

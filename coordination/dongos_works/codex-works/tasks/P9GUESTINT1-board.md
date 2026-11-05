# P9GUESTINT1 — P9 已独立验收消费端真实迁移主线并复验生产路径

负责人：codex。状态：待领取。

依据已验收cursor:P9GUESTCORPUS1与非作者P5P9AUDIT1-corpus报告，将实现真实复制到tools/guest_corpus，固定ROOT并用包导入避免缓存冲突；移测试至tests，保留候选不变。生产路径重新构建与验证，不复用候选回执。保留host-only边界，不运行VM、不接入生产服务清单、不提交推送。独立审查迁移差异与CLI/module入口后正式复验，再登记真实集成。

## 可修改文件

- `tools/guest_corpus/__init__.py`
- `tools/guest_corpus/corpus_guest.dg`
- `tools/guest_corpus/corpus_entry.asm`
- `tools/guest_corpus/build_guest_corpus.py`
- `tools/guest_corpus/guest_corpus_receipt.py`
- `tests/test_guest_corpus.py`
- `docs/guest-corpus.md`
- `codex-works/deliveries/P9GUESTINT1.md`
- `codex-works/reviews/P9GUESTINT1.md`

## 定向验收

- `module:tests.test_guest_corpus`
- `module:tests.test_syscall_corpus`

交付：`codex-works/deliveries/P9GUESTINT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

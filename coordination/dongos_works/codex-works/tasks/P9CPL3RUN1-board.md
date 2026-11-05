# P9CPL3RUN1 — [P9] 真实 CPL3 语料执行与外部 UART 回执核验

负责人：codex。状态：待领取。

利用正常runtime7和现有shell EXEC、临时FAT APP.ELF及外部UART，启动生产语料ELF在CPL3执行；只读观察进程身份、加载映射与归档ELF，核对真实退出状态、完整P9LOG1及语料逐例返回。重用严格传输验证，单独区分观察证据与已有host-only声明，原API不得将日志自称客体证明。保留实际构建/输入/串口、成功与失败证据。宿主负控覆盖缺失或伪造日志、篡改文件/身份；协调者可在冻结副本和临时虚盘运行QEMU，不触及物理盘，不加入普通启动清单。此项只做已有有界语料，不扩大IPC前置或24小时阶段。

## 可修改文件

- `tests/run_p9_corpus_qemu.py`
- `tests/test_p9_corpus_qemu.py`
- `tools/guest_corpus/log_transport/corpus_log.py`
- `codex-works/deliveries/P9CPL3RUN1.md`

## 定向验收

- `module:tests.test_p9_corpus_qemu`
- `module:tests.test_corpus_log`

交付：`codex-works/deliveries/P9CPL3RUN1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

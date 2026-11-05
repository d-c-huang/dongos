# P9HOSTCRT1 原生夹具编译

在现有 C 夹具里以 `uint64_t` 和 `PRIu64` 打印计数及退出值。Windows TDM GCC 在原 `-std=c11 -Werror` 选项下拒绝的硬编码格式已替换。原寄存器断言、日志字节检查、负控、退出码和编译告警选项均保留。

`python -B -m unittest tests.test_guest_corpus tests.test_corpus_log tests.test_p9_corpus_qemu -q` 实测 7 项全部通过，零跳过。此前失败仍保留在 `build/test/p9-corpus-log/run-df2aa2fc80c7`。


## AI交付 2026-11-05T12:39:06+00:00 · codex-mcp-50488d53a0084e80

仅将现有C夹具计数/结果日志改为uint64_t与PRIu64，保留严格告警及所有功能断言。实测原生消费者、原生日志传输及新宿主观察器共7项零skip通过，原TDM GCC格式错误留档。

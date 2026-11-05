# P9HOSTCRT1 — [P9] 修复原生语料夹具的 Windows 严格格式编译

负责人：codex。状态：待领取。

本机 TDM GCC 在 -std=c11 -Werror 下将 printf 的 %llu 判为不支持，导致已有宿主 ELF/日志回归无法链接。使用可移植的 uint64_t 格式或不依赖宽整数格式的等价日志，保留全部 C 寄存器/退出/负控及严格告警；不修改生产实现。用本机现有工具跑两模块。

## 可修改文件

- `tests/test_guest_corpus.py`
- `codex-works/deliveries/P9HOSTCRT1.md`

## 定向验收

- `module:tests.test_guest_corpus`
- `module:tests.test_corpus_log`

交付：`codex-works/deliveries/P9HOSTCRT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

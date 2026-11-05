# P9GUESTCORPUS1 交付

2026-11-05，按用户要求由 Codex 接手原 Cursor 任务，保留编号与文件范围。

已完成有界 Dong 用户服务、真实 SYSCALL 汇编入口、隔离 ELF builder、严格原始回执校验及原生反控。复用正式语料解析器，当前仅 none 子集；不支持的前置整批拒绝。

协调角色实际运行：`python -m unittest discover -s ../coordination/dongos_works/cursor-works/tests -p test_guest_corpus.py -v`，2 tests / 0 skip，32.798 秒通过。证据目录：`code/build/test/p9-guest-corpus/run-9c07c69d24f6`。debug/release 均生成真实 ELF 并检验只读数据段；各执行正常与四类真实坏体，保存命令、退出码、raw receipt 与 host 验证结果。新增代码文件测试期间 SHA 稳定。

仅宿主受控 syscall 边界，无 OS/VM/真机执行，无生产服务接线；回执固定 guest_verified=false。不是 P9 全阶段完成。提交后等待独立源码审查和协调器复验；执行者未自行验收或集成。


## AI交付 2026-11-05T02:06:39+00:00 · codex-mcp-891e96b2a2a74c41

已落盘7项声明文件。真实Dong+ASM PIE ELF、只读固定语料、严格绑定和逐例raw receipt；正式解析器复用，none子集之外整批拒绝。协调角色定向实测2tests/0skip通过32.798秒，debug/release正常+四类真实坏体及完整性反控，证据code/build/test/p9-guest-corpus/run-9c07c69d24f6。无VM/guest通过声明；待独立复验/审查，未自行验收集成。


## AI交付 2026-11-05T02:18:30+00:00 · codex-mcp-891e96b2a2a74c41

首次正式复验02d6dda35bb840b5b6b88419a3bf1a53因复制期间其他任务源码变更取消，未执行测试，非实现测试失败。P5/P9候选及报告现已全部完成并冻结，本项代码无需修改，重提相同已通过2tests/0skip的候选排队独立复验。仍仅host-boundary证据，未自行验收/集成。

# P9GUESTCORPUS1 独立审查

2026-11-05，用户明确授权；非作者子代理 `/root/review_corpus` 只读审查，协调器转录。结论 PASS，submitted rev8，仅限有界消费端及宿主边界证据。

核对完整原任务书、六项候选、生产解析器及syscall ABI。正式复验 bf205646263444d882a9b86735e894d6 为2 tests/0 skip/source_stable。独立额外测试2项/64.360s/OK/0 skip，证据 code/build/test/p9-guest-corpus/run-e1c79ec48e17。

builder复用verify_bytes，整批1–256项，拒绝全部未支持前置。七参数SysV→syscall映射含[rsp+8]正确；两模式ET_DYN不可写数据检查通过。正常12调用/14emit；漏末例exit42、错R10 exit41、错RAX exit3；漏END虽exit0仍拒绝。返回/emit故障均1调用后停止。严格raw长度、标签、连续索引、generation、返回与终态；外部可信manifest SHA绑定语料、源与产物。独立附加探针拒绝count0和正常480字节回执的全部480个严格前缀。

证据边界：归档program.elf只构建未执行；运行的是另编译CORPUS_HOST native体。只输出host-boundary-only/guest_verified=false，execution=guest拒绝。调用方负责外部可信SHA、真实退出/超时与代际不复用。未证明CPL3/真实内核/24h/泄漏监控。

六文件SHA256：corpus_guest.dg 77ed343869e3dcf8a2e9c8cc8f37820e1cfdfeddf28db1732d5cbea4ec769daf；corpus_entry.asm a6b1e037ee9ca8bd1c440633411bdd0e49e71a247ec99f595879a7d74dd175e3；build_guest_corpus.py 84c77e6f36361e247085c096b48131542f29d5086926710e97a97db13c746aa2；guest_corpus_receipt.py b3b76c06567653f888defc7b0cf4bfd8d94d2f36ea95e182bc448047a2b90364；contract.md f90a1fffed81ac892fa78f11a47f3126b314b6a5751c021801e62941c8e4fb22；test_guest_corpus.py 20c3a68b236ef0388315e7ee155e3cef3e3a743b8b7ab8b3a3da165a1deb45ab。测试前后稳定。

集成建议tools/guest_corpus整组落地，tests/test_guest_corpus.py。修正测试路径、避免裸模块名缓存冲突、固定生产ROOT关系；迁移改变source binding，必须重新构建复验，不能复用候选产物当生产验证。

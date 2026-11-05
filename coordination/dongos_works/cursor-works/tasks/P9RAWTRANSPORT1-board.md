# P9RAWTRANSPORT1 — [P9] 客体回执的有界日志封装与严格离线采集

负责人：cursor。状态：待领取。

接续已集成P9GUESTINT1，补真实客体采集前缺口，不重复语料/parser/receipt。先核对生产log syscall实际边界及串口格式；在候选为固定binary BEGIN/CASE/END设计带明确版本/长度/序列的有界ASCII日志封装，实际Dong编码与现有syscall汇编相接；Python解码器仅收合法专属行并回还原始raw交给现有严格receipt验证。每批1..256、总长度上限、截断/重复/乱序/混批/前后噪声/坏hex/额外终态/输出失败等严格拒绝，进程退出/超时不得由日志自称成功代替。保留外部可信manifest SHA及单次generation；从档案和文本无法证明归档ELF执行时仍guest_verified=false，不允许execution=guest绕过原拒绝。真实Dong/ASM宿主边界下逐字与独立Python编码oracle对照，两模式真实坏体改case/漏尾/混代被断言拒绝。完整来源快照含新封装器/解码器，生产consumer源不直接改。Cursor手动，不运行OS/VM/宿主系统调用、不写启动清单；真实内核串口采集/CPL3/24h另独立任务，不关闭P9。

## 可修改文件

- `cursor-works/src/p9/raw-transport/corpus_guest.dg`
- `cursor-works/src/p9/raw-transport/corpus_entry.asm`
- `cursor-works/src/p9/raw-transport/corpus_log.dg`
- `cursor-works/src/p9/raw-transport/corpus_log.py`
- `cursor-works/src/p9/raw-transport/build_log_corpus.py`
- `cursor-works/src/p9/raw-transport/contract.md`
- `cursor-works/tests/test_corpus_log.py`
- `cursor-works/deliveries/P9RAWTRANSPORT1.md`

## 定向验收

- `discover:cursor-works/tests:test_corpus_log.py`

交付：`cursor-works/deliveries/P9RAWTRANSPORT1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

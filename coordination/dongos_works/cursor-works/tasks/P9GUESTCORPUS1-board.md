# P9GUESTCORPUS1 — [P9] 将已验收syscall语料接入有界CPL3执行与回执

负责人：cursor。状态：待领取。

P9既有tools/syscall_corpus.py及tests/test_syscall_corpus.py已经集成，不重写生成器/解析器。补实际CPL3消费端及严格回执：读取原docs/syscall-corpus.md，复用正式解析器验证种子/index/数量/寄存器/形状oracle；有界最多256case/单批，不在内核处理不可信JSON。私有builder按已验证语料生成固定只读数据，编译真实Dong+ASM用户服务，通过既有SYSCALL ABI提交原始寄存器并记录每例返回及连续进度。只能使用明确定义前置的none或可独立核对的absent_handle_entry等子集；未实现live endpoint/映射前置的case必须显式拒绝整批或标为未执行，不能按accepted_shape伪造调用成功，也不能静默跳过后宣称完整语料覆盖。禁止调用宿主OS syscall、传shell命令或运行VM。回执绑定原语料SHA、源码/ELF/生成数据SHA、执行次数、case索引和实际返回值；离线解析拒绝缺项/重复/乱序/过期代际/超时/崩溃/丢失终态/截断记录，不能接受passed布尔替代实际逐例比较。host测试实际编译执行受控SYSCALL边界替身，核对SysV寄存器到用户SYSCALL汇编路径/计数/停止规则和真实坏ASM或坏Dong反控；替身明确标为host，不得签发guest通过。至少真实坏体漏执行一例、篡改寄存器或返回值、接受缺失结尾被精确断言拒绝。builder只写显式输出的新隔离目录，不能修改生产内核/服务或现有镜像；默认不启动任何进程型VM。后续真实内核集成/客体执行/24小时门槛、资源泄漏监视及安全启动/IOMMU/CET均由独立任务承担，本项不代表P9完成。Cursor客户端手动领取，测试由协调器运行，不提交推送、不自动启动AI CLI。

## 可修改文件

- `cursor-works/src/p9/guest-corpus/corpus_guest.dg`
- `cursor-works/src/p9/guest-corpus/corpus_entry.asm`
- `cursor-works/src/p9/guest-corpus/build_guest_corpus.py`
- `cursor-works/src/p9/guest-corpus/guest_corpus_receipt.py`
- `cursor-works/src/p9/guest-corpus/contract.md`
- `cursor-works/tests/test_guest_corpus.py`
- `cursor-works/deliveries/P9GUESTCORPUS1.md`

## 定向验收

- `discover:cursor-works/tests:test_guest_corpus.py`

交付：`cursor-works/deliveries/P9GUESTCORPUS1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。

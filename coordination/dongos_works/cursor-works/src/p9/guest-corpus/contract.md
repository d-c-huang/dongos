# P9 有界语料消费候选

复用生产 `tools/syscall_corpus.py.verify_bytes`，整批 1–256 项。当前只接收 `requires=none`、非 `accepted_shape`、无 message 数据的用例；`absent_handle_entry` 和所有 live endpoint 前置均拒绝整批，绝不静默过滤。生产解析器继续校验种子、连续 index、ABI 描述、所有原始寄存器及 oracle。

`build_guest_corpus.py CORPUS --output NEW_DIRECTORY --generation POSITIVE_U64 [--mode debug|release]` 从源码根运行。先完成输入校验，再创建新的显式输出目录；已有目录或文件拒绝。调用真实 Dong 编译器、NASM 和 ld.lld，生成 PIE ELF，固定数据在只读 LOAD 段。所有命令用参数数组执行；无 OS/VM 启动、无生产文件覆盖。该 ELF 尚未加入生产服务清单。

Dong 循环调用真实汇编 SysV→SYSCALL 路径：RAX/RDI/RSI/RDX/R10/R8/R9 七个输入保持原始值，第七个 SysV 参数从栈读取。只读记录的第八字为正式解析器校验后的预期原始返回。每例执行后立即输出实际返回，首次不同即输出失败终态并停止。日志输出失败则立刻返回 2，不伪造结束；成功返回 0。宿主构建仅在 `CORPUS_HOST` 下将特权边界和日志输出替换，完全不执行宿主 syscall。

原始回执是小端 u64 二进制：64 字节 BEGIN（魔数、版本、generation、count、四字绑定 SHA），每例 32 字节 CASE（魔数、generation、index、actual），最后 32 字节 END（魔数、generation、已执行数、status）。长度必须恰好 `96+32*count`。原始串必须完整捕获；生产 RAM 日志环容量不构成本工具的持久采集保证，截断必拒绝。

绑定 SHA 覆盖语料 SHA、固定数据 SHA、完整源快照 SHA、模式、代际、数量。manifest 进一步记录 ELF、生成 Dong、汇编 SHA。验证调用方必须提供独立保存的 manifest SHA 和本次预期 generation，验证器重新核对归档输入、数据、ELF 与原始回执；不能由回执自报 `passed` 代替。调用方须真实提供退出码/超时状态，并在外部保证 generation 不复用；本模块不提供调度器或硬件签名。

`verify_receipt` 仅签发 `host-boundary-only`，固定 `guest_verified=false`，请求 guest 证明直接拒绝。宿主证据核对编译执行路径及回执完整性，不能证明真实内核分派、CPL3 启动或硬件状态。后续仍需独立客体加载、完整日志采集、24 小时运行、泄漏监控以及安全启动/IOMMU/CET 工作。

原生测试采用独立 C 寄存器和返回值判断；debug/release 均执行正常、漏最后一例、错 R10、篡改 RAX、遗漏 END 的真实编译体。负控按明确退出码/回执异常拒绝，崩溃不算成功。另测返回不符与日志失败停止、乱序/重复/截断/过时代际/超时/退出失败、产物篡改、拒绝未实现前置及不覆盖输出。

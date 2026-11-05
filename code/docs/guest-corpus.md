# P9 有界语料消费候选

复用生产 `tools/syscall_corpus.py.verify_bytes`，整批 1–256 项。当前只接收 `requires=none`、非 `accepted_shape`、无 message 数据的用例；`absent_handle_entry` 和所有 live endpoint 前置均拒绝整批，绝不静默过滤。生产解析器继续校验种子、连续 index、ABI 描述、所有原始寄存器及 oracle。

`build_guest_corpus.py CORPUS --output NEW_DIRECTORY --generation POSITIVE_U64 [--mode debug|release]` 从源码根运行。先完成输入校验，再创建新的显式输出目录；已有目录或文件拒绝。调用真实 Dong 编译器、NASM 和 ld.lld，生成 PIE ELF，固定数据在只读 LOAD 段。所有命令用参数数组执行；无 OS/VM 启动、无生产文件覆盖。该 ELF 尚未加入生产服务清单。

Dong 循环调用真实汇编 SysV→SYSCALL 路径：RAX/RDI/RSI/RDX/R10/R8/R9 七个输入保持原始值，第七个 SysV 参数从栈读取。只读记录的第八字为正式解析器校验后的预期原始返回。每例执行后立即输出实际返回，首次不同即输出失败终态并停止。日志输出失败则立刻返回 2，不伪造结束；成功返回 0。宿主构建仅在 `CORPUS_HOST` 下将特权边界和日志输出替换，完全不执行宿主 syscall。

原始回执是小端 u64 二进制：64 字节 BEGIN（魔数、版本、generation、count、四字绑定 SHA），每例 32 字节 CASE（魔数、generation、index、actual），最后 32 字节 END（魔数、generation、已执行数、status）。长度必须恰好 `96+32*count`。原始串必须完整捕获；生产 RAM 日志环容量不构成本工具的持久采集保证，截断必拒绝。

绑定 SHA 覆盖语料 SHA、固定数据 SHA、完整源快照 SHA、模式、代际、数量。manifest 进一步记录 ELF、生成 Dong、汇编 SHA。验证调用方必须提供独立保存的 manifest SHA 和本次预期 generation，验证器重新核对归档输入、数据、ELF 与原始回执；不能由回执自报 `passed` 代替。调用方须真实提供退出码/超时状态，并在外部保证 generation 不复用；本模块不提供调度器或硬件签名。

`verify_receipt` 仅签发 `host-boundary-only`，固定 `guest_verified=false`，请求 guest 证明直接拒绝。宿主证据核对编译执行路径及回执完整性，不能证明真实内核分派、CPL3 启动或硬件状态。后续仍需独立客体加载、完整日志采集、24 小时运行、泄漏监控以及安全启动/IOMMU/CET 工作。

原生测试采用独立 C 寄存器和返回值判断；debug/release 均执行正常、漏最后一例、错 R10、篡改 RAX、遗漏 END 的真实编译体。负控按明确退出码/回执异常拒绝，崩溃不算成功。另测返回不符与日志失败停止、乱序/重复/截断/过时代际/超时/退出失败、产物篡改、拒绝未实现前置及不覆盖输出。

## 生产源码位置

已迁入 `tools/guest_corpus/`，使用 `python -m tools.guest_corpus.build_guest_corpus CORPUS --output NEW_DIR --generation N`；也支持直接执行builder文件。回执API从 `tools.guest_corpus.guest_corpus_receipt` 导入。此迁移不把服务加入启动清单。生产路径的源快照及binding重新生成，不复用候选产物。

## P9LOG1 日志传输

只封装现有 binary BEGIN/CASE/END。每行严格为 `P9LOG1 ssss ll hex\n`：四位小写十六进制零起序号，首行长度40（64字节），其余20（32字节），payload为原始内存字节的小写hex。首行144字节，后续80字节；1..256案例对应3..258行，总量最多20704字节。无CR、空格变体、前后噪声、重复、跳号、截断或额外记录。真实Dong编码器使用固定数组，避免字符串slice静态指针破坏PIE链接。输出失败锁存，consumer返回2，不继续宣告完成。

corpus_entry.asm实际将日志送往0x70 syscall，CORPUS_HOST才转独立C边界；原七寄存器case syscall映射不变。生产services.dg的0x70限制4096B并copy_in后交给services_write_bytes；kernel/services_run.asm维护4096B环形缓冲，UART缺失/超时会丢输出但仍返回0。因此完整捕获必须来自外部且包含全部专属行；成功syscall不能证明完整交付，256例不能依赖环形缓冲保留。缺行在严格检查中拒绝。未添加内核捕获、启动清单或执行OS/VM。

构建只生成一个实际链接的PIE ELF，归档真实编译sources及五个transport实现，后者SHA集合规范序列化后写入真实编译guest源注释，故原BEGIN binding也覆盖编码器、解码器和builder。外层transport-manifest.json绑定该集合与内层原receipt manifest，调用者必须提供可信外层SHA及generation。来源文件、生成data、assembly、ELF、corpus和原始回执全部由原验证器复核。不存在参考ELF替代实际执行档案的做法。

离线verify_log只接收bytes，最多20704B；文件读取有界，manifest严格schema及重复键拒绝；解码后交给既有verify_receipt，依然核对每个raw return、顺序、generation、终态、外部退出码/超时。execution仅host，guest无条件拒绝；文本和归档不能证明归档ELF在客体执行，结果始终guest_verified=false。

五份实现逐字迁入tools/guest_corpus/log_transport，构建命令：python -m tools.guest_corpus.log_transport.build_log_corpus CORPUS --output NEW_DIR --generation N。严格校验API：from tools.guest_corpus.log_transport.corpus_log import verify_log；expected_manifest_sha256必须是外部可信保存的transport-manifest.json SHA。原binary接口保留。tests/test_corpus_log.py固定生产路径，重新生成ELF与binding，未复用候选产物。非作者独审包含输出失败直接复调仅写一次探针；生产迁移结果见coordination/dongos_works/codex-works/reviews/P5P9CALLINT1.md。未加入启动清单，仍无客体执行证明。

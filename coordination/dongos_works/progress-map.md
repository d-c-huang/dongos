# DongOS 整体任务图：当前检查点

更新时间：2026-10-24 22:48 +08:00。控制台图源 `roadmap.json` 已同步以下结果。

| 阶段/任务 | 当前状态 | 验收范围 |
| --- | --- | --- |
| L3/L3A | complete | 保持已验收的完整纯ELF矩阵结论 |
| P2CD1 | integrated rev6 | C/D生产接线；正式172项零skip；正常、遗漏EXEC poll、遗漏CACHE poll三个实际WHPX客体及独立回放通过 |
| P2CDTYPE1 | integrated rev6 | PAT×MTRR有效类型修复，正式1项零skip |
| P2CDBUILD1 | integrated rev6 | 零静态池完整manifest适配，正式10项零skip；与父项合计182项 |
| P2VEC42 / P2ERR43 | integrated rev15 / rev8 | Codex接手完成两项DeepSeek遗留数据任务，各1项正式零skip，真实移交完成 |
| P2整体 | partial | C/D门已关闭；剩暖PCID实际复用与物理WC真机验收 |
| P5 | partial | 保持既有验收范围，按既定顺序接续 |

P2CD1最终正常及两类真实错误客体分别488/478/491份raw独立回放通过；1121源码输入与最终冻结客体及主目录一致，父项26份加builder两份文件已实际集成。runtime5/6/7内核分别1,986,960/1,991,056/1,995,152字节，原期限、ACK规则和2MiB限制保持。旧失败与中间构建全部保留。以上为本地集成，本轮没有提交或推送Git。

当前证据以协调器最终状态及审查说明为准：[P2CD1](codex-works/tasks/P2CD1-board.md)、[P2CDTYPE1](codex-works/tasks/P2CDTYPE1-board.md)、[P2CDBUILD1](codex-works/tasks/P2CDBUILD1-board.md)、[P2VEC42](lmstudio-works/tasks/P2VEC42-board.md)、[P2ERR43](lmstudio-works/tasks/P2ERR43-board.md)。父项正式作业 `8cf746e3518145219278173a593dafbc`；builder正式作业 `ebf434eb7c83402fa6ddf6e51632b4df`。暖PCID及物理WC未由这些结果代替验收。

## 历史检查点

下方内容按原时间留存，其中“最新／当前／待完成”仅代表当时状态，不覆盖上表。

2026-10-24 早前任务同步（Codex接手完成两项数据任务）：

- `lmstudio:P2VEC42`：负责人 Codex，`integrated rev15`。12 条 GOP 页包络向量已修正；正式独立复验 `94b5d018570144e08c2d8eb8bd279120`，1 项通过、零 skip，源码稳定且进程退出。
- `lmstudio:P2ERR43`：负责人 Codex，`integrated rev8`。8 种缓存错误码中文对照与真实 `kernel/mm/runtime_cache.dg` 一致；正式独立复验 `9868d94f74e745a38c6bb924ee380ae3`，1 项通过、零 skip，源码稳定且进程退出。
- 四项契约及错误数据负控测试通过。两项各自数据/交付已真实移交并复算 SHA，与正式复验指纹一致；旧失败与改派历史保留。稳定 ID 的 lmstudio 前缀不代表当前负责人。
- DeepSeek 的这两项未完成任务已清结；下方“DeepSeek已领取／待验收”等为历史记录。P2 整体仍 partial，后续仍为 C/D 实际接线及客体证据、暖 PCID 实际复用与物理 WC 验证；本次数据交付不替代这些阶段门。

交付：`lmstudio-works/deliveries/P2VEC42.md`、`lmstudio-works/deliveries/P2ERR43.md`。状态以协调器最新 rev 为准。

---

2026-10-24T17:25:08+08:00 P2接续完成一个组件：P2LEDGER44已独立验收并集成rev9；正式六组9tests/0skip，source_stable且进程停止/退出。真实memory+paging账本在debug/release合计20正常场景与10真坏Dong拒绝；R1完整runtime7 release构建339输入、99暂存内核源、7产物SHA一致，kernel=1,978,768B，2MiB窗口余118,384B。P2REG45亦integrated6，旧启动/桌面回归夹具正式2tests/0skip。未执行新镜像客体运行，P2整体仍partial：下一步C/D实际接线及客体正负证据，另有暖PCID实际复用和无真机条件下的物理WC待验。DeepSeek继续本人P2VEC42，P2ERR43依赖前项验收。
证据：coordination/dongos_works/reviews/2026-10-24-P2-ledger-verification.json、2026-10-24-P2-ledger-native.json、2026-10-24-P2-ledger-build.json；契约：code/docs/p2-framebuffer-ledger.md。以下为历史检查点。

2026-10-24 17:17 +08:00 P2：P2REG45已integrated rev6（两项旧回归夹具独立2tests/0skip）。P2LEDGER44已实现独立授权账本并submitted rev6，R1补HHDM溢出前置拒绝，正式冻结作业85481e0d327745dab512a9a646576cf5运行中，尚未验收/集成。前轮本机18正常+10真坏源通过；原正式作业主动取消，不算通过。R1前runtime7构建成功（kernel 1,978,768B），R1同源构建进行中。DeepSeek已领取P2VEC42 rev7，P2ERR43待前项验收；不抢占其文件。P2整体仍partial，C/D实际接线、warm-PCID与真机WC保持待验。

2026-10-24 最新改派：按用户要求，LM Studio运行已取消并停止；P2VEC42（rev6）与P2ERR43（rev2）负责人均已改为DeepSeek，状态todo待Harness领取。保留稳定ID lmstudio:P2VEC42/lmstudio:P2ERR43及原write_paths，前缀不代表当前负责人；先完成P2VEC42独立验收，再执行依赖项P2ERR43。独立测试仍由Codex维护。P2LEDGER44保留Codex负责，尚未实施。

2026-10-24 P2接续：L3/L3A完整纯ELF矩阵已完成。P2仍partial；ROOT13/PCID12/WC14/EXEC19/CACHE20/RAW38/OBS36/LARGE16均已集成。当前剩独立GOP授权账本（P2LEDGER44已发布未实施）、C/D实际接线、暖PCID实际复用证据及真机WC。LM Studio按单并发执行P2VEC42边界向量，随后P2ERR43错误码对照；Codex编写的独立校验门P2LMTEST41已integrated rev6（4tests/0skip）。数据交付不能替代生产/客体验收。以下均为历史检查点，状态以协调器最新rev为准。

# DongOS 整体任务图

## 当前完成状态（2026-10-24T16:26:44+08:00）

2026-10-24 L3完成：L3ELFMATRIX1 已独立验收并集成本地主线 main 工作树（integrated rev6）。正式作业 ed37c79515f94c87a488e538ea6ba20d：51项/27组全部通过、零skip，963.657秒，source_stable及进程停止/退出均确认。148份目标ELF、166次实际观察运行和六类错误源码通过独立产物审计；157主目录源码与复验一致，G6的456源仍逐字绑定已验收的2,062,984字节编译器。因此L3/L3A剩余纯ELF矩阵门关闭，整体状态更新为complete。

完成回执：code/docs/l3-pure-elf-matrix.md；永久机器可读证据：coordination/dongos_works/reviews/2026-10-24-l3-closure.json。后续按既定顺序回到P2/P5；本次没有执行Git提交、推送或关机。下方“待验证/partial”等为历史检查点。

2026-10-24 最新：L3ENC1、G6ENC1 均 integrated rev6。编码扩展正式4项零skip（486.25秒），G6正式15项零skip（0.813秒），源码稳定且进程退出。XMM/movdqu、32/64位原子和后端受限asm编码已实现；1017条字节对照及两模式真实纯ELF执行通过。新编译器2,062,984字节、源码494,247字节，fresh固定点与实际同盘两启通过；独立965+965原始转储、FAT/退休页审计通过，主目录456源与运行冻结输入一致。L3仍partial：剩完整语言矩阵通过纯ELF路径的覆盖验证，不再将上述编码缺口或新版G6列为待开发。证据见 coordination/dongos_works/codex-works/reviews/2026-10-24-G6-encoding.md/json；下方旧状态保留为历史。

## L3接续（2026-10-24）

最新：L3ENC1 integrated rev6，正式4项零skip/486.25秒，独立源码稳定；主目录生产与测试指纹匹配。G6ENC1 in_progress rev2，开始新版fresh固定点及客体复验；源码包494,247字节。此处未宣称新G6或完整L3通过。

L3ENC1 submitted rev3，独立四项复验运行中；补齐内建assembler中后端实际生成的XMM、原子、受限asm编码。预检及补完整目标runtime后的纯ELF执行已通过，但尚未登记验收。下方G6成功仍属旧冻结源码，新编译器固定点预算和客体门待复验。没有把编码子项或旧G6外推为整个L3完成。

## 最新优先级：先 L3，再接续 P2/P5（2026-10-23）

最终检查点：G6RUN2 已独立验收并集成 rev6。真实同盘双启 run-b54a8a8d615b 全部通过，离线独审每启961原始文件、冻结输入、FAT固定点与128页退休清零；正式15项零skip复验通过。G6WAIT2/G6POOL1修复分别已集成rev6，G6DOC1集成rev8。L3当前G6门已关闭，更广L3A纯ELF覆盖仍未完成，继续优先于P2/P5。详情见 codex-works/reviews/2026-10-23-G6-current-run.md/json。以下“正在/待验”为本轮历史过程；尚未推送，不关机。

接续实测：G6WAIT2 驱动计时等待已独立复验并集成 rev6；fresh 镜像的编译与服务退出成功，但旧检查器静态池假设导致原 run-662c6cec8a01 整体失败，700 个原始文件审计留存。G6POOL1 已以20项零skip正式复验并集成 rev6，严格验证当前构建的动态块服务池；正在冻结检查器上重新执行同盘双启动。G6RUN2 仍在途，尚未验收；L3A 更广纯ELF仍待完成。

用户要求比较剩余工作并先完成较少的一组。按实际阶段门禁归组，L3剩新G6客体回归、L3A更广纯ELF覆盖两组；P2剩framebuffer账本、C/D接线、独立warm-PCID三组软件工作，另有物理WC真机待验。组数不是工时估算或任务卡数量。先恢复L3，G6DOC1已通过15项零skip独立复验并集成rev8；G6RUN2 in_progress rev2，正在当前冻结源码上全新构建；G5及历史L3C不重复开发。当前12个内核/构建文件相对G6PREP1快照有变化，后续G6必须fresh构建，不外推旧准备证据。

## 当前结果：OBS/B 已独立验收并本地集成（2026-10-23）

协调服务已恢复。P2OBS36 integrated rev37、P2LARGE16 integrated rev68：正式复验110/65项、零skip；同一R15冻结版本的正常、漏AP刷新、flush返回错误三场景各实际双启动，严格回放和独立raw审计全部通过。六启分别核对1930/1894、979/1087、981/980文件，owned进程均退出0，无PFLASH错误。主目录12/18个声明文件均匹配正式指纹后，分别登记accepted和integrated。

负控证据已补齐；正常wire1采集干扰失败和此前启动/oracle失败仍保留，未放宽客体期限。详情见 `reviews/2026-10-23-P2OBS36-P2LARGE16-R15-review.md` 及同目录evidence.json。下方接续块为历史过程。P2其余ledger、C/D和独立warm-PCID消费者任务、P5及物理WC真机待验仍保留；本项内后续PCID检查通过不替代其他任务。本地新进展尚未推送，不关机。

## 最新复验接续：R15（2026-10-23）

补充：同源 `omit-r15-wire1` 已通过原runner实际双启动和严格回放。独立raw审计分别闭合979/1087文件，确认动态漏刷命中、AP1 stale-A而实际映射B、reader未ACK及旧2MiB保持；两个QEMU正常退出，无PFLASH错误。结果SHA256 `b021868d2ebbf6e21771c926c05940554c1935a875f98baeda531101506780a4`。两类负控已补齐，正在核对同源正常双启动；最终验收/集成尚未登记。

P2LARGE16 R15 已 submitted rev66，正式作业 `4363ad07fc1145dbba775a2d817710b6` 通过65项、零skip，源码稳定且执行进程退出；三类镜像均从冻结源码构建。OBS R9 保持 submitted rev35，正式110项通过。两任务尚未登记验收/集成。

R15 的 `flush-error-r15-wire3` 已通过原runner实际双启动及独立严格回放；AP1实际flush返回0、注入返回1，两轮均形成同事务失败持有且旧2MiB保持。独立原始审计分别闭合981/980个文件，两个QEMU正常退出，无PFLASH错误。此前两次启动未在原90秒内出现P1_START，失败归档保留；生产等待期限未修改。当前继续同源漏刷负控和正常双启动，尚不以返回错误负控代替stale-A漏刷验收。P2其余软件工作、P5及物理WC真机待验项仍保留。

## 最新接续：协调服务恢复与负控证据（2026-10-23）

用户关机后重新要求继续，协调服务已恢复并经MCP核对：P2OBS36 submitted rev31，正式110项零skip通过；P2LARGE16 R12 submitted rev55，作业 `e4ee7de582284b38b40e504e5d7f1e6e` 于北京时间16:09:39完成57项零skip，源码稳定、执行进程退出。两任务均未accepted/integrated。

后续P2LARGE16已按R13返修并领取，当前in_progress rev57：新增动态命中记录、独立flush-return-error用例及完整代码范围绑定。早期独立检查通过12个ELF/COFF汇编对象及安全记录发布器C探针；这些不是R13完整复验或实际来宾验收。R13仍在实现与审查，尚未冻结、运行正式复验或新实际双启动。

R13首轮独立兼容预检157项出现B夹具字符串转整数错误及OBS反控同tick无篡改问题，两项均已定位并修正。第二轮157项/7.306秒/零skip通过，四实现文件前后SHA一致；原50个B测试全部保留，新增7个。OBS仅反控改为sealed_ns-1，生产不变，R9 submitted rev34，本机110项通过。两任务均待新正式复验，不沿用旧轮次通过结果宣称新代码验收。

随后OBS R9正式作业 `0553d178506e4026bec83d2adc021e7c` 通过110项、零skip、源稳定、进程退出，当前submitted rev35。B R13全部六路径冻结、submitted rev58，正式作业 `cd564952ad754918b1e70d44693da265` 正在运行64项及三镜像构建。新源actual双启动尚未进行，两任务尚未accepted/integrated。

B R13随后正式64项全部通过、三镜像完成、零skip/源稳定/进程退出。首轮error实际记录完整AP1 real0→1及同事务Hardware，但AP2/3历史requested先于当前发布，旧相等断言拒绝；R14修正该单调历史关系但未单独执行复验。omit实际完整命中且观察到AP1 stale-A/PTE-B、reader未ACK、旧2MiB逐字节保持，独立978文件scoped审计闭合；原runner仍因metrics.failed=1与旧强制0规则矛盾拒绝。两次原result仍false，owned进程退出0、输入稳定、无PFLASH错误。现R15 in_progress rev64：保留R14并只在严格首Failure归因后允许omit的预期failed指标，normal/legacy门不变；待新正式复验及实际双启动，不提前验收。证据详见 `code/build/test/p2-historical36-review/b-r13-omit-wire1-stale-scoped-raw.json`。

此前OBS R8/B R11冻结源的正常实际双boot、严格回放及独立raw审计通过；omit负控读到新值，未形成原stale门，后来无关超时不算通过。R12已修负控owner完成后立即失败退出，避免继续重复采样混入无关故障。本轮继续动态skip命中记录与独立flush-return-error负控，保持原stale要求和guest期限；新增负控不替代旧负控。P2剩余ledger/C-D/warm-PCID、P5及物理WC真机门尚未关闭。详见工作区 `UPLOAD_CHECKPOINT.md`；下述较早状态为历史记录。

## P2 优先，随后 P5（2026-10-23T02:55:00+08:00）

用户最新顺序：先完成 P2，再完成 P5。P2FLUSH11 已 integrated rev6，
正式独立作业64cf4d5d11454dfebd38a28ec54136b8通过3项、零skip；190原始
产物SHA及三正/三真坏ASM独审通过。P2仍partial：调度后多根大页/EXEC/WC
消费者、支持环境的AP PCIDE=1及物理WC性能仍须完成。普通多根变更协议和
BSP/逐CPU PCID已有实现，既有11项P2任务不重复派发。

P2PCID12、P2ROOT13、P2WC14和进度接续P2SYNC15在途，未提前验收。
ROOT13首轮因快照期间源变化而未执行测试，已保留记录并准备重排。
本检查点190项=161 integrated+24 accepted+4 in_progress+1 paused；
实时以MCP为准。G6PREP1宿主22项0skip已integrated6，未运行新G6来宾；
G6DOC1按用户优先级paused2。P5尚未开始本轮实现。没有运行OS/VM或提交推送。

详见[当前P2检查点](codex-works/reviews/2026-10-23-P2-current.md)。
以下带日期的数量、候选和“当前”均保留各自历史范围。


## G5 完成与主线集成（2026-10-23T01:34:42+08:00）

G5FULL1 integrated rev16、G5CLOSURE1 integrated rev21、G5INT1 rev24；
G5METHODFIX1、G5DOC1、G5DOC2均integrated rev6。七生产模块已按
accepted字节实际写入本地主线，永久测试、旧契约回归和文档同步完成。
当前协调器活动任务 **183项：159 integrated、24 accepted**，
0 todo/in_progress/submitted/rework。状态与代码完成范围分别判断，
24个accepted不等于24个尚未实现组件。

| 当前门禁 | 结论 |
| --- | --- |
| G5完整语言/NASM宿主门禁 | 已完成；51项/27组、scope_complete=true |
| G5完整编译器闭包 | 已完成；四ELF逐字节相同，每份2,046,376B，56MiB/64KiB/2MiB预算保持 |
| 主线独立集成复验 | 正式0856作业51+1+18共70项，零skip、源稳定、退出/停止确认，原始产物独审通过 |
| L3整体 | 继续partial：扩大编译器新G6客体自编译/FLUSH/同盘双启 |
| L3A更广纯ELF | 继续partial：内建assembler无XMM/atomic/受限asm等编码，NASM覆盖不等于通用纯ELF覆盖 |
| 历史L3C | 原head/runtime5/49模块profile继续已完成，不外推本轮2,046,376B产物 |
| P2/P5/P6/P7/P8/P9及KVM/真机 | 保留各自既有完成与真实余项，本轮不扩张 |

详见[完成回执](codex-works/reviews/2026-10-22-G5-completion.md)、
[完整门禁](../../code/docs/g5-differential.md)与[roadmap.json](roadmap.json)。
候选交付、旧失败和中断全部保留；下方164项及八类gap为历史快照，
不再代表当前待办。本轮未运行OS/VM/AI CLI，未提交/推送。

## 历史检查点：新开发机恢复与收尾（2026-10-22T09:18:41+08:00）

本轮17份缺失任务书、CX6同号异义和CX14/CX15旧状态均已处理完成。CX14 integrated rev7，CX15 integrated rev8；CX6 integrated rev9，已恢复读取器契约，分离5条原NASM事件，耗时恢复为1轮/265秒，原始事件全部保留。协调器issues=0；核对时间2026-10-22T09:18:41+08:00。

当前MCP快照共164项活动任务：19 accepted、140 integrated、3 submitted、1 in_progress、1 rework。本轮同时观测到其它客户端新增5项并行任务，其状态按实时MCP继续变化，本轮没有接管或改动它们。

| 本轮处理项 | 结果 |
| --- | --- |
| 原缺失17份任务书 | 全部按固定Git原文恢复，并核对契约/原交付/历史验收指纹；issues=0 |
| CX6同号异义 | 读取器规范契约恢复；旧NASM单独归档且后继CXNASM3不变；5条旧NASM事件从派生统计分开，原事件保留 |
| CX14旧在途 | 正式3项零skip及原G6限定profile证据审核通过，integrated rev7 |
| CX15旧提交 | 正式1项零skip完整固定点/391.284秒通过，integrated rev8 |

逐文件来源、正式job/指纹、身份分离和最终状态见[恢复报告](reviews/2026-10-22-task-recovery/README.md)及[完成回执](reviews/2026-10-22-task-recovery/completion.json)。本轮未重启OS/VM，原G6客体验收继续绑定原head及49模块profile。

```mermaid
flowchart LR
  A["固定Git原文及现有代码"] --> B["17份任务书恢复：零校验问题"]
  A --> C["CX6读取器 / CXNASM3身份分离：原事件保留"]
  A --> D["CX14 / CX15正式复验后分别验收、集成"]
  D --> E["整体阶段继续：完整G5 / P5安全恢复 / 硬件与外部验收"]
```

| 阶段 | 当前结论 | 真实剩余范围 |
| --- | --- | --- |
| P0 工具链与构建环境 | 已通过既有验收 | 本项既定范围无待办 |
| P1 UEFI 引导器 | 已通过既有验收 | 本项既定范围无待办 |
| P2 CPU 与内存 | 部分完成 | P2SMP3只覆盖调度前固定共享内核根并永久封存；任意调度后多用户CR3动态修改及PCID/PGE启用范围继续另验。；受控真实碎片order9 OOM已由P2OOM4完成；任意固件碎片拓扑不作穷尽保证。TCG不证明WC真实性能；最新正常装载余量102704B，后续增长继续复核。 |
| P3 中断与抢占线程 | 已通过既有验收 | 本项既定范围无待办 |
| P4 用户态与 IPC | 已通过既有验收 | 本项既定范围无待办 |
| P5 基础服务 | 部分完成 | P5CTX1/P5CTX2已实际集成并随4e1fede进入当前源码；独立源码、宿主和真实客体核验不替代DMA安全回收闭环；可信outstanding DMA排空、持续旧owner排除、全别名撤映射后的全核TLB退休、unpin/free/reuse及恢复发布仍需真实闭环；现有ACK位于撤映射前，不算撤映射后退休证明；同boot设备重授权/驱动重启及旧句柄/旧DMA/旧IRQ负控与持久化回归；reset-hold和两次稳定持有观察不能充作drain或安全回收；分配错误、partial mapping、physical=0客体注入未执行，相关证据仍限P5CTX1原生测试；不重复开发已完成的账本/日志/精确身份/别名拒绝/reset-hold |
| P6 多核与快速启动 | 部分完成 | PR#3 head288d65c的focused39425166102失败：首代AP/STARTING观察窗口未捕获，KVM权限探测因sudo需密码失败；合并独立暂缓，不重写已接线scheduler/init，也不记为KVM性能超时；新正常镜像GUI/键鼠/USB回归和实验验证工具差集集成；合法Linux/KVM环境下loader→interactive shell≤500ms；设备权限前置失败尚无成功性能结果 |
| P7 图形桌面 | 部分完成 | 当前R6完整GUI及输入回归；输入修正已有原生、输入/USB专项及常规boot记录；新正常镜像的完整GUI/键鼠回归仍待关闭 |
| P8 USB 与真机 | 部分完成 | 至少一台台式机和一台笔记本实际启动验收；物理设备、Hub与热插拔等范围另验；当前新镜像USB集成回归待关闭 |
| P9 安全加固 | 尚未完成 | 自有密钥签名、OVMF与真机安全启动；IOMMU限制驱动DMA；CET影子栈/间接跳转检查与内核基址随机化；系统调用/IPC模糊测试及原阶段24小时门槛 |
| L0 语言规格 | 已通过既有验收 | 本项既定范围无待办 |
| L1 编译器与基础库 | 已通过既有验收 | 本项既定范围无待办 |
| L2 优化与源码调试 | 已通过既有验收 | 本项既定范围无待办 |
| L3 Dong 编译器自举 | 部分完成 | 已实际证实的完整语言差集：method、enum、error、try、orelse、defer、extern SysV/Win64；有限runner已验收集成，完整G5继续partial。 |
| L3A 完整后端与命令行 | 部分完成 | 完整语言、ABI与诊断覆盖仍属G5；现有runtime5/49模块profile的持久产物验收已见L3C，不因此关闭完整后端覆盖 |
| L3B 宿主有界自编译固定点（已进入主线） | 已通过既有验收 | 本项既定范围无待办 |
| L3C DongOS内自编译（runtime5/49模块profile） | 已通过既有验收 | 本项既定范围无待办 |

源码基线4e1fede的P2 EXEC/WC实际消费者、预算优化及有限G5已经集成；并行新增的SysV/方法/P9候选以其各自实时任务及独立验收为准。本轮修复旧任务记录不覆盖其它负责人源码或状态。

## 以下为原有历史快照

以下保留原有记录；其中日期、任务数量、机器路径和“当前/下一步”均属于各自历史检查点，最新状态以上述记录及协调器为准。

证据快照：2026-10-21T23:25:35+08:00。P2BUILD5已独立验收并本地集成rev6：正式16项零skip/source_stable；补齐正式构建NASM分组帮助探测，真实NASM2/3兼容测试通过。NASM3完整release runtime7构建、实际1/4核共享大页与四核桌面/P5两观察、独立raw replay均通过。正常kernel2006608B/余90544B；316inputs匹配主目录。与旧NASM2非逐字一致，19ASM源相同，编码/对齐差异已审查并保留双份证据。MCP快照132项=109 integrated+19 accepted+3 in_progress+1 todo。Claude EXEC in_progress rev10（R1返修），WC in_progress rev2；DeepSeek L3A在途rev2，L3待依赖验收。P2 EXEC/WC消费者、任意调度后多CR3及WC真实性能仍未关闭。不提交/推送/建PR。 见[MCP快照](reviews/2026-10-21-P2BUILD5-roadmap-snapshot.json)与[集成回执](reviews/2026-10-21-P2BUILD5-integration.json)。

**G6代码已合并并保全同步，限定profile验收完成。** [公开执行/合并报告](reviews/2026-10-21-g6-ci-execution.md)及[JSON](reviews/2026-10-21-g6-ci-execution.json)保留两轮失败、第三轮成功及原始证据。M7/M8等历史环节中的“当前main/HEAD244b18c”属于PR8原检查点；最新G6代码合并/同步检查点以顶部及M11为准。后续文档提交可推进HEAD，不改变已验收的f54c35c代码/tree证据。

## GitHub集成门禁（保留既有历史快照）

**#7 → #10 → #8 → #11 已合并并同步；#3独立暂缓。** G6与P5各自保留阶段门禁，本地P5上下文修改不计入GitHub准确head验证。

```mermaid
flowchart LR
 M7["✅ PR #7 已合"] --> M10["✅ PR #10 已合"] --> M8["✅ PR #8 已合并且本地已同步<br/>main 244b18c；任务身份已保全"]
 M3["⏸ PR #3 独立暂缓<br/>KVM权限/DAG观察未通过"]
 M8 --> M11["✅ PR #11 已合并/同步<br/>G6代码检查点 19e1a19"] --> G6["✅ L3C runtime5/49模块真实双启通过"]
```

| 环节 | 已完成 | 下一步 |
| --- | --- | --- |
| M0 已包含的历史分支：6项，无需重复合并 | PR#1/#2/#4/#5/#6/#9的分支均为GitHub main祖先，备份内容无遗漏；codex/p5-recovery-dma-journal；codex/p6-input-irq-fix；docs/p5-p6-engineering-handoff；docs/p5-p6-merged-checkpoint；dot/verified-components-console-20261020；dot/l3-host-checkpoint-20261020 | 所列集成范围已完成；阶段验收按各自门禁继续 |
| M7 PR#7：远端已合，本地主线已包含 | head3a5c773的专项、实际VirtIO reset guest、输入及完整CI通过；2026-10-20 21:29:25合并，merge 1dfebe1；只完成复位并持有DMA | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |
| M10 PR#10：已合入远端与本地主线 | head1c00a6f的专项及完整CI通过，已正常合入main，merge d7468a1；PR#8已正常合并并完成本地同步；整块DMA别名拒绝、reset/hold和租约记录全部保留 | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |
| M8 PR#8：已正常合并并同步本地主线 | 2026-10-20 23:02:01正常合并，merge244b18c；合并树与准确head50ab7cf完全相同，已包含PR#7/#10及P2/L3既有开发；准确head的完整CI39436523413、P5专项39436520689和输入专项39436523449均通过；27字节桥机器正反例和两seed模式完整原生ELF固定点已复核；本地主线于23:09:05快进至244b18c；120个bootstrap Dong模块、专用编译器栈、源/产物适配与WINVERIFY1执行器代码已可见；23:13合并同步冻结快照：56个原dirty文件已保全；533项本机state/任务书/交付文件SHA保持原样，另1个index仅由协调器正常更新generated_at；91项异机live路径仍隔离，foreign161条保留Git和ZIP，不导入本机调度；23:13冻结快照的官方DB为137任务/1129事件/120作业/1设置，逻辑SHA未变，活跃121项；此历史报告保持不改，本轮正式复验、验收/集成和新增P5CTX1另记录正常新rev，当前统计见本地协调轨道；stash2f286e8981a8283c65ce0a9dc9648ee9771e3bb8及.local/pr8-main-sync-20261020T150259Z保留可恢复副本；合并同步阶段未自动登记任务验收或集成，本轮后续登记保留原历史；合并后输入CI39444684432已通过，完整CI39444684378在本快照时仍运行；不把合并前准确head通过写成新push全量已通过，G6真实双启仍见L3C；23:13冻结时服务经HTTP与MCP核对为121项活跃任务，automation=false、issues=0；149项Python、11项UI JS、14项桥/NASM/启动宿主测试均0skip通过；其范围不替代本轮两项正式隔离复验 | 所列集成范围已完成；阶段验收按各自门禁继续 |
| M11 PR#11：G6代码已合并/同步，限定profile验收完成 | 准确候选f54c35c/tree394874cfe8ec7e4b0b4a9c857535781f88a957c6仅8个G6文件；FAT32分配I/O和生产日志解析修复有真实坏源及回归，不含P2或本地P5CTX1实现；G6 run39467503226 attempt1在准确headf54c35c通过真实同盘两启（304.834秒、307.193秒）；SEED/STAGE1/STAGE2各1892648字节且逐字等于宿主ELF，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2；432项源码与453项冻结输入按Git原始字节核验；两次共1810份物理转储经两位独审，64KiB栈/双guard、56MiB arena、只读源码借页、W^X和无能力隔离通过；每启128页退休表清零、core/借页撤销、controller恢复及真实FLUSH均通过；准确候选常规CI39467503240为20/20 success：712宿主测试0skip、931语言测试1项既有DONG_ASSEMBLER_FULL_INPUT条件skip、9组真实boot；P5 39467503250与输入39467503280通过。实际PR测试merge b905c1e、f54c35c与代码merge19e1a19同tree 394874cfe8ec7e4b0b4a9c857535781f88a957c6；G6代码合并/同步检查点19e1a19（PR#11于2026-10-21 02:20:34合并、2026-10-21 02:21:50本地快进同步），完整merge SHA 19e1a1982de0d7ebc57eea0b851d968e01b40e07；实际merge、本地检查点和已验收候选内容树相同；保全FF证明8项G6文件干净，其余307路径字节/删除态与cached diff原样；未使用reset/stash/restore，不导入foreign任务状态；合并后自动push检查在2026-10-20T18:20:41Z快照为39473893535 in_progress；39473893647 in_progress；与已通过的准确候选/同内容树检查分开，不冒称新push全绿，也不为重复CI阻塞此次集成。 | 仅本行声明profile/集成范围已完成；G5/P5等另验 |
| M3 PR#3：独立暂缓合并（工具已开发） | head288d65c的KVM/DAG验证工具和AP预筛已开发；三个共享输入文件已在main，剩余6个新增验证文件；不重复合并输入修复 | 不在M7→M10→M8合并队列；focused39425166102的KVM权限及首代DAG观察失败，应解决环境/观察门禁或另拆工具范围；保留真实失败，未取得KVM计时或首代结构成功证据前不标阶段验收通过 |

本次合并与本地同步依据见[合并/保全报告](reviews/2026-10-20-pr8-merged-local-sync.md)和[JSON记录](reviews/2026-10-20-pr8-merged-local-sync.json)。准确head的固定点及CI范围见[阻塞修复报告](reviews/2026-10-20-pr8-blockers-review.md)与[固定点实物核验](reviews/2026-10-20-pr8-fixedpoint-proof.json)。旧待合快照保留为历史证据。

## 系统主线

```mermaid
flowchart TD
 P0["✅ P0 工具链"] --> P1["✅ P1 UEFI"] --> P2["🟡 P2 核心/扩展源码均已主线<br/>共享根大页及封存持有已集成；EXEC/WC另验"]
 P2 --> P3["✅ P3 中断与线程"] --> P4["✅ P4 用户态与IPC"] --> P5["🟡 P5 存储/账本/DMA日志、reset-hold及别名拒绝已合入<br/>精确上下文与真实客体核验已本地集成，安全回收仍待闭环"]
 P5 --> P6["🟡 P6 SMP/tickless/init DAG已接线<br/>首次跨AP结构、GUI/USB回归、KVM计时待验"]
 P6 --> P7["🟡 P7 桌面既有功能通过，新版回归待闭"] --> P8["🟡 P8 受控USB通过，真机门槛待验"] --> P9["⬜ P9 安全加固"]
```

| 阶段 | 已完成的开发与证据 | 真实剩余项 |
| --- | --- | --- |
| P0 工具链与构建环境 | NASM、链接器、QEMU与UEFI固件可用；构建、调试、测试入口及本地自动启动验收通过；完整 CI 已拆为并行分片(ci.yml)，另有 p6-input 输入/USB 专用工作流；可复现基线夹具已修复；P2BUILD5本地integrated rev6：正式build.assemble已接NASM3分组警告帮助；保留严格其它警告及旧版兼容，正式16tests/0skip和完整release/真实1/4CPU回归通过。 | 所列受控范围已完成 |
| P1 UEFI 引导器 | 载荷读取、解压、SHA-256校验与BootInfo交接通过；正常启动、篡改/截短/缺失拒绝及退出固件重试通过 | 所列受控范围已完成 |
| P2 CPU 与内存 | 主线异常/分配器/活动页表、NX/WP/W^X及四核TLB shootdown已有验收；ELF装载撤销supervisor写别名、发布隔离与销毁退休已实际接线；PR#8已合入主线并同步本地：2MiB live映射/拆分/合并与页表退休回收，含512项转换、PAT位重映射和既有真实双CPU探针记录；PR#8已合入跨地址空间物理别名W^X规划，以及PAT/MTRR有效类型、别名冲突检查、WC编码与缓存迁移；P2LIVE1本地integrated rev6：保持Context/Stats ABI的active大页map/split/merge已接正常私有根，在AP启动前由BSP完成真实buddy order9租约、512页首末读写、替换/拒合并/恢复/合并/完整失效与精确回收，最终恢复4KiB树和账本；18项不同宿主测试通过，正式12项0skip/source_stable；最终1/4核正常客体、真实漏挂拆分表负控及完整release runtime7四核桌面/P5CTX2正常控制回归通过，原始归档独立复算；kernel.bin=2096720B，原2MiB窗口余432B；本地未提交实现，不计作既有GitHub CI覆盖；P2SIZE2 integrated rev6：保留默认编译输出与2MiB装载ABI，kernel函数节+链接GC释放106496B，完整release四核桌面通过。；P2SMP3 integrated rev6：AP在线/调度前固定共享内核根完成实际大页同步事务，全部临时表回收后永久持有512页WB/RW/NX视图并封存；正式5项零skip、source_stable，真实单/四核及唯一漏AP调用负控和独立完整raw replay通过。；P2SMP3验收时正常release runtime7的316输入与当时主目录SHA一致，kernel.bin=2006608B，余90544B；四核本轮524广播/1572 AP ACK，P5正常两观察回归通过；不计入既有GitHub CI。；P2OOM4 integrated rev9：真实碎片free879/最大order8下原生产alloc9返回02000007且完整状态不变；正式3tests/0skip/source_stable，真实1/4CPU及独立raw replay、原正常/漏AP负控归档再复算通过。；P2BUILD5 integrated rev6：NASM3正式构建完整runtime7，316inputs匹配主目录，2,006,608B/余90,544B；真实1/4CPU与四核P5/桌面及独立原始复算通过，汇编版本差异已核清。 | 通用动态EXEC与图形WC正常消费者仍待接线/实际客体验收；Claude EXEC详细R1返修in_progress rev10，WC in_progress rev2，候选不冒作完成。；P2SMP3只覆盖调度前固定共享内核根并永久封存；任意调度后多用户CR3动态修改及PCID/PGE启用范围继续另验。；受控真实碎片order9 OOM已由P2OOM4完成；任意固件碎片拓扑不作穷尽保证。TCG不证明WC真实性能；正常装载余量90544B，后续增长继续复核。 |
| P3 中断与抢占线程 | ACPI发现、LAPIC/IOAPIC与旧PIC屏蔽通过；受控定时回退与线程抢占、XSAVE/FXSAVE状态保存通过 | 所列受控范围已完成 |
| P4 用户态与 IPC | 独立地址空间、ELF加载、句柄权限与百万次真实IPC通过；BSP PCID生命周期及VMware标签保留通过；正常内核的通用能力通知、共享对象API通过 | 所列受控范围已完成 |
| P5 基础服务 | 主线受控设备授权、键盘、VirtIO/AHCI/NVMe、FAT32/shell与FLUSH同盘重启闭环已有验收；PR5已合入：恢复账本stop→quiesce→retire→reclaim→read→新代际发布，以及分配前PINNED/整块DMA归属记录；最新交接保存专项原生与完整CI通过记录；PR#7已合入GitHub主线：可信现代VirtIO停止后复位并持有DMA，专项/完整CI通过，含真实TCG control/fault；PR8历史同步检查点244b18c已包含；PR#10已正常合入GitHub主线（merge d7468a1）：普通USER分享拒绝完整DMA分配块别名；PR#8合并及本地同步后仍原样保留；P5CTX1由另一线程完成真实本地文件集成并登记integrated rev7：可信精确身份、完整DmaLease快照与退休观察已接入services/device_host；代码为本地未提交修改，不冒作本轮GitHub CI覆盖；P5CTX2本地integrated rev6：真实4核TCG正常/UD2故障两组各两次稳定观察，完整424B DmaContext与Device/DmaLease/Binding对照真实Catalog、账本、ECAM硬件；21项正式host零skip及独立raw/portable replay通过，P5CTX1生产源码保持不变；原租约held=1、drain=UNKNOWN | P5CTX1/P5CTX2已本地实际集成并分别登记rev7/rev6，尚未提交或推送；独立源码、宿主和真实客体核验不替代DMA安全回收闭环；可信outstanding DMA排空、持续旧owner排除、全别名撤映射后的全核TLB退休、unpin/free/reuse及恢复发布仍需真实闭环；现有ACK位于撤映射前，不算撤映射后退休证明；同boot设备重授权/驱动重启及旧句柄/旧DMA/旧IRQ负控与持久化回归；reset-hold和两次稳定持有观察不能充作drain或安全回收；分配错误、partial mapping、physical=0客体注入未执行，相关证据仍限P5CTX1原生测试；不重复开发已完成的账本/日志/精确身份/别名拒绝/reset-hold |
| P6 多核与快速启动 | 主线四核用户抢占/迁移/退休/IPI及tickless one-shot/idle停表已经开发并接线；正常runtime7启用P6_USER_SMP；init Kahn依赖图、ready_mask、普通AUTOSTART应用与首代归属已接线；不再列为待开发DAG；输入IRQ丢边沿修正已合入，专项与完整CI通过记录已在最新交接恢复；首次DAG观察器、严格KVM runner及负控已经在实验分支开发；失败记录也已保存 | PR#3 head288d65c的focused39425166102失败：首代AP/STARTING观察窗口未捕获，KVM权限探测因sudo需密码失败；合并独立暂缓，不重写已接线scheduler/init，也不记为KVM性能超时；新正常镜像GUI/键鼠/USB回归和实验验证工具差集集成；合法Linux/KVM环境下loader→interactive shell≤500ms；设备权限前置失败尚无成功性能结果 |
| P7 图形桌面 | 合成器、字体、DPI、主题、动画与真实输入功能已有验收；四个独立CPL3应用、窗口生命周期及文件/设置持久化已有验收 | 当前R6完整GUI及输入回归；输入修正已有原生、输入/USB专项及常规boot记录；新正常镜像的完整GUI/键鼠回归仍待关闭 |
| P8 USB 与真机 | 受控xHCI/HID/BOT、USB键鼠和USB主盘持久化通过；GPT/ESP启动镜像、QEMU实际USB引导及受控ACPI电源通过 | 至少一台台式机和一台笔记本实际启动验收；物理设备、Hub与热插拔等范围另验；当前新镜像USB集成回归待关闭 |
| P9 安全加固 | 原阶段门槛尚未完成 | 自有密钥签名、OVMF与真机安全启动；IOMMU限制驱动DMA；CET影子栈/间接跳转检查与内核基址随机化；系统调用/IPC模糊测试及原阶段24小时门槛 |

P5 的恢复顺序是 **stop → quiesce → retire → reclaim → read → 发布新代际**。reset-hold及两次持有快照不证明outstanding DMA已排空、解除PINNED或驱动恢复。P2LIVE1、P2SMP3共享根封存视图及P2OOM4受控碎片拒绝已集成；EXEC/WC消费者继续另验。

## 语言主线

```mermaid
flowchart TD
 L0["✅ L0 规格"] --> L1["✅ L1 编译器/基础库"] --> L2["✅ L2 既定优化/调试"] --> L3["🟡 L3 自举"]
 L3 --> A["🟡 L3A 已完成接线进入主线<br/>120模块；输入/输出/64KiB栈/56MiB流水线，G5另验"]
 A --> B["✅ L3B 宿主完整ELF固定点已完成且合入<br/>新桥CI四份1,892,648字节ELF逐字一致"]
 B --> C["✅ L3C runtime5/49模块profile<br/>真实双启、同盘ELF、隔离与退休已验收；G5另验"]
```

| 环节 | 已完成 | 剩余 |
| --- | --- | --- |
| L3 | 主线120个bootstrap Dong模块、66个nasm_组件；原生前端/诊断、通用IR/lowering/NASM、原生汇编器与宿主CLI已经接线；10个整函数组件已在主线文件集成并有5组真实组合测试；本轮逐项核对既有验收指纹、主线路径与有效负控；PR8保留161条异机原任务档案：109 integrated、27 accepted、23 paused、CX14 in_progress、CX15 submitted；其源码已合入，档案保留在Git、ZIP及恢复台账，不导入本机当前122项活跃调度；L3A输入/输出/64KiB栈/56MiB流水线和L3B完整ELF固定点已完成开发并进入主线，本地源码可见，原独审及正式复验记录保留；本机C52经新正式job c00f7299f5fb453a9d16d91ab5164d79完成6项零skip独立复验，accepted rev13→integrated rev14；主线组件早随PR8集成，本轮正常补记正式结果，不覆盖旧失败和时间线；现有runtime5/compiler_job隔离profile及49模块自编译闭包已完成真实G6验收并随PR#11合并/同步；G6 run39467503226 attempt1在准确headf54c35c通过真实同盘两启（304.834秒、307.193秒）；SEED/STAGE1/STAGE2各1892648字节且逐字等于宿主ELF，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2 | 主线代码已同步，本地任务身份和UI修改已保全；后续依据当前本地调度处理，不重复派发已完成的读取、栈、产物写入或入口桥开发；完整语言G5差分覆盖继续保留；当前自编译闭包不等于方法/错误/枚举/try/orelse/defer/完整ABI全部完成；异机CX14/CX15原状态保留为档案，不自动导入或改写；现有profile的真实双启已由本轮新证据闭合，更广完整语言G5仍待差分覆盖 |
| L3A | 主线原生frontend/diagnostics、program_ir→lower_program→nasm_program与宿主POSIX CLI已接线；主线已包含GUEST1～5、CR45/46及CX6/8的既有实现：有界路径/目录/源码读取、诊断、原生汇编输入、真实H_READ/H_WRITE/H_SYNC文件适配；原任务完成历史单独留档；主线已包含CX7的64KiB双guard编译器栈、CX10的既有64MiB帧池及CR47语义栈优化；旧16KiB开发阻塞已解决，原独审及正式复验记录保留；主线CX13 compiler_job在单56MiB arena内完成前端/压缩/后端/原生汇编与ELF输出，无宿主IR/汇编正文替代；27字节启动桥已修复并通过机器正反例；既有输入/输出/专用栈/纯编译流水线已在G6真实同盘两启验证，但仅限现有49模块profile | 完整语言、ABI与诊断覆盖仍属G5；现有runtime5/49模块profile的持久产物验收已见L3C，不因此关闭完整后端覆盖 |
| L3B | 早期49模块宿主stage1/stage2汇编、对象与C适配宿主可执行文件逐字节一致已有冻结记录；CX12紧凑x86编码与CX13完整原生自编译流水线已进入主线，原独审及正式复验历史保留；debug/release两种seed路径共四份ELF逐字一致；历史四份ELF均1892632字节，SHA256 cf19cd58e244835e142f5abc40c1ced98da3666b3ba4855080623bc638b606bc；64KiB guard栈/单56MiB arena及真实坏体记录保持原范围；原verification/source_stable/process_stopped、独审和指纹保留在异机Git/ZIP档案及恢复台账；源码已同步，不因ignored build未迁移撤销已完成开发事实；新27字节桥的准确head50ab7cf已在Linux CI通过完整固定点；debug/release四份ELF均1892648字节、逐字一致，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2；merge244b18c的树与该head相同，本机Windows映射失败不计成功；本轮G6两次客体生成的完整ELF与相同源码宿主固定点逐字一致；宿主NASM+C链和原生汇编器ELF链仍按各自证据记录 | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |
| L3C DongOS内自编译（runtime5/49模块profile） | 主线已包含CX14的P5隔离编译slot3、受限启动门、只读源码借页、core退出权限与controller真实文件持久化接线；原异机任务在途记录仅留档；真实VM已经运行，run-cc7b089dc2b4保留明确失败：SYSRET消耗RCX导致第4参数arena错误；不是从未运行；内核R10传参及27字节桥RCX←R10、host decoder已修复并进入主线，本地可见；宿主实际机器桥正反例通过；新真实双启结果按后续CI记录验收；PR#11已实际安装专用G6 workflow于独立分支，固定head/tree并重建完整fixture和runtime5/compiler_job内核；每次保留原始成功/失败证据；真实首轮写盘超时定位FAT32逐项重扫I/O，按扇区扫描与单次grow局部游标修复；第二轮533.094秒完成STAGE1持久写盘，完整1892648字节与宿主ELF逐字一致，但生产EBS解析门禁错误导致未进入第二启；G6 run39467503226 attempt1在准确headf54c35c通过真实同盘两启（304.834秒、307.193秒）；SEED/STAGE1/STAGE2各1892648字节且逐字等于宿主ELF，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2；432项源码与453项冻结输入按Git原始字节核验；两次共1810份物理转储经两位独审，64KiB栈/双guard、56MiB arena、只读源码借页、W^X和无能力隔离通过；每启128页退休表清零、core/借页撤销、controller恢复及真实FLUSH均通过；G6代码合并/同步检查点19e1a19（PR#11于2026-10-21 02:20:34合并、2026-10-21 02:21:50本地快进同步）；现有runtime5/compiler_job隔离profile及49模块自编译闭包完成。首轮超时与第二轮解析门禁失败完整保留，不改写成通过；G5和P5安全恢复仍独立保留 | 仅本行声明profile/集成范围已完成；G5/P5等另验 |

## 本轮正式协调进展

C52与CXNASM3的真实实现早已随PR8进入main244b18c；本轮通过新正式隔离复验、独立源码/契约及产物审查后，按原任务正常推进新rev。旧提交、失败、中断与None结算记录保留，不覆盖历史。

| 任务 | 已核实结果 | 当前状态与边界 |
| --- | --- | --- |
| claude:C52 | job c00f7299f5fb453a9d16d91ab5164d79；6 tests、0 skip、149.843秒；source_stable/process_stopped/execution_exited均true；源码及713项产物已独立审查 | accepted rev13→integrated rev14；仅限该模块，不代表L3/G6整体完成 |
| codex:CXNASM3 | job 4628b48597ad4fa4a0edb758628cc8a5；10 tests、0 skip、2.859秒；三项结算标志均true；实际NASM3.02双格式正反例及指纹已独审 | accepted rev5→integrated rev6；保留独立编号，不覆盖异机CX6 |
| cursor:P5CTX1 | 另一线程已正式复验、独审并本地集成；integrated rev7，job5ed94c53b4b84458a0a53b052c63b8c9为1test/0skip；[原集成报告](reviews/2026-10-21-P5CTX1-integration.md) | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |
| codex:P5CTX2 | 正式job b15f655e12ea439bbe3af0aef39cf8be，12+9=21 tests、0skip、source_stable；独立审查通过，accepted rev5→integrated rev6；完整runtime7正常/故障镜像各自构建通过，真实4CPU TCG control/fault分别40.015/43.109秒；各两次稳定raw观察、完整ELF/布局/源码/磁盘/清理证据及portable replay通过；实际主文件逐SHA匹配正式与客体来源；P5CTX1生产源码保留，未建PR、提交或推送 | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |
| codex:P2LIVE1 | 正式job a8778fe9dfae4df6842a1ce3cb5efe1e，1+2+9=12 tests、0skip、source_stable；另6项既有planner/paging回归通过，独立源码/契约/真实字节审查PASS，accepted rev5→integrated rev6；最终1/4核正常根实测、真实漏挂split链接坏源拒绝及完整release runtime7四核桌面/P5CTX2正常控制回归通过；512页/项精确检查，full_flush516/retired4，最终租约与表数恢复基线；14声明文件与正式指纹一致，1299源码匹配真实运行副本、8个P5文件及HEAD基线保留；2MiB装载ABI不变，余432B；无PR/commit/push | 本项既定范围已通过验收，无待办；范围说明与后续归属见下表 |

P5CTX1接续真实DMA申请成功/失败和退休路径的owner/incarnation、旧device token/generation、root/memory generation与完整DmaLease记录，禁止覆盖旧身份；reset只记confirmed、drain保持unknown，不回收DMA、不发新token或重启驱动。既有账本、整块记录、别名拒绝和reset-hold不重做，P5仍partial。

G6 run39467503226 attempt1在准确headf54c35c通过真实同盘两启（304.834秒、307.193秒）；SEED/STAGE1/STAGE2各1892648字节且逐字等于宿主ELF，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2。432项源码与453项冻结输入按Git原始字节核验；两次共1810份物理转储经两位独审，64KiB栈/双guard、56MiB arena、只读源码借页、W^X和无能力隔离通过；每启128页退休表清零、core/借页撤销、controller恢复及真实FLUSH均通过。准确候选常规CI39467503240为20/20 success：712宿主测试0skip、931语言测试1项既有DONG_ASSEMBLER_FULL_INPUT条件skip、9组真实boot；P5 39467503250与输入39467503280通过。实际PR测试merge b905c1e、f54c35c与代码merge19e1a19同tree 394874cfe8ec7e4b0b4a9c857535781f88a957c6。合并后自动push检查在2026-10-20T18:20:41Z快照为39473893535 in_progress；39473893647 in_progress；与已通过的准确候选/同内容树检查分开，不冒称新push全绿，也不为重复CI阻塞此次集成。 见[公开执行报告](reviews/2026-10-21-g6-ci-execution.md)。

### 已验收节点的范围说明

已对照原任务书、当前源码、正式验收指纹及实际客体原始归档重新核实。DMA排空/回收/恢复、P2后续消费者和G5完整语言覆盖确实未完成，继续作为所属阶段真实待办；以下仅区分它们与已完成任务的验收范围。详见[逐项实质核实](reviews/2026-10-21-roadmap-completion-check.md)。

| 已验收节点 | 验收范围与后续归属 |
| --- | --- |
| P5CTX2 | 本任务验收范围为initialized-queue正常/故障终态的精确上下文核验与租约稳定持有，已完成；held=1、drain UNKNOWN属于已核实的持有状态。；核实结论：DMA排空、撤映射后全核退休、回收/复用、新token及驱动重启确实未完成，保留P5阶段待办；P5CTX2原任务范围为持有上下文核验。 |
| P5CTX1 | 本任务精确持有上下文已验收并本地集成；按用户约定未提交或推送，不计入旧G6准确head的GitHub CI范围。；RESET_CONFIRMED与DMA drain UNKNOWN保持分开；后续真实客体核验已由P5CTX2完成，安全排空/退休/回收与驱动恢复确实未完成，保留在P5阶段待办。 |
| P2LIVE1 | 本任务验收范围为AP启动前BSP的临时WB/NX大页生命周期，已完成并恢复原4KiB树。；核实结论：持久大页、AP在线后多核大页及EXEC/WC消费者当前尚未接入，保留P2阶段待办；P2LIVE1原任务范围为BSP启动前临时生命周期。 |
| L3B | 验收范围为宿主有界自编译固定点；现有profile的客体固定点已由L3C验收，完整语言差分覆盖确实未完成，保留L3/G5阶段待办。；CX15原异机任务身份继续保留在历史档案，不作为L3B当前待办，也不据此把整体L3标为完成。 |
| M7 | 本节点为PR#7的代码合并与本地同步，已完成；PR8历史同步检查点244b18c已包含PR#7/#10/#8，无需重复合并。；异机任务记录继续保留为档案；DMA排空、unpin/free/reuse和驱动恢复确实未完成，保留P5阶段待办。 |
| M10 | 本节点为PR#10的代码合并与本地同步，已完成；DMA排空、回收和设备恢复确实未完成，保留P5阶段待办，代码合并不关闭阶段门槛。 |

### 已识别的下一步

1. 现有runtime5/49模块profile的G6已验收并合入；继续完整语言G5差分覆盖，不重复开发源读取、专用栈、入口桥或同一profile。
2. P5CTX1/P5CTX2已本地集成；继续可信DMA排空、撤映射后全核退休、精确回收/复用与设备恢复真实闭环，保留held=1/drain UNKNOWN门槛。
3. P2LIVE1已完成；继续持久/多核大页及EXEC/WC消费者，复用既有P4/PCID契约。P6/KVM与PR#3、P7/P8完整回归及真机门禁保持原范围；本轮release桌面smoke不替代这些完整门槛。
4. 新push CI按公开执行报告快照单列；既有同内容树验证足以完成此次G6集成，不冒称后续文档提交已通过相同检查。

## 异机任务档案与本地调度

[恢复台账](reviews/2026-10-20-cross-machine-task-ledger.md)及[JSON档案](reviews/2026-10-20-cross-machine-task-ledger.json)保留异机161条任务身份、原验证与指纹；91项异机live路径仍隔离，不执行higher-rev覆盖或导入。

23:13的[合并同步冻结报告](reviews/2026-10-20-pr8-merged-local-sync.md)保留当时137任务/1129事件/120作业/1设置逻辑SHA未变、活跃121项，以及533项本机记录SHA未变、index仅正常更新的证据。该报告保持原样；其后两项新正式复验、正常验收/集成和新增P5CTX1会产生新记录，不能把冻结结论当成当前DB未变。

当前MCP非归档124项：integrated=105、accepted=19，todo/in_progress/submitted/rework/paused均0。16归档/总138是02:26历史统计，本轮未复核归档总数；本次不改任务状态，异机档案和同号身份保全继续保持。

WINVERIFY1执行器代码早已同步；C52和CXNASM3本轮分别通过新正式隔离复验并登记integrated rev14/rev6。旧submitted、process_stopped=None及中断作业保留在历史时间线，没有用新结果覆盖旧回执。

## 依据

- [P2LIVE1交付](codex-works/deliveries/P2LIVE1.md)、[独立审查](reviews/2026-10-21-P2LIVE1-independent-review.md)与[本地集成回执](reviews/2026-10-21-P2LIVE1-integration.json)。
- [P5CTX2交付](codex-works/deliveries/P5CTX2.md)、[独立审查](reviews/2026-10-21-P5CTX2-independent-review.md)与[本地集成回执](reviews/2026-10-21-P5CTX2-integration.json)。
- [本次MCP任务快照](reviews/2026-10-21-roadmap-local-update.json)：124非归档、105 integrated、19 accepted，三个任务最新rev及正式复验来源。
- [G6真实执行、修复、独审与合并](reviews/2026-10-21-g6-ci-execution.md)及[JSON](reviews/2026-10-21-g6-ci-execution.json)：本轮准确head、同内容树CI及代码合并/同步检查点。
- [本轮P5/G6下一步](reviews/2026-10-20-p5-g6-next-actions.md)及[JSON](reviews/2026-10-20-p5-g6-next-actions.json)：保留当时正式复验与G6准备快照；当前实际执行、验收和合并以G6执行报告为准。
- [C52任务书](claude-works/tasks/C52-board.md)、[CXNASM3任务书](codex-works/tasks/CXNASM3-board.md)及[P5CTX1任务书](cursor-works/tasks/P5CTX1-board.md)：由协调器维护的原任务与本轮新任务入口。
- [PR8合并与本地保全](reviews/2026-10-20-pr8-merged-local-sync.md)及[JSON](reviews/2026-10-20-pr8-merged-local-sync.json)：merge、stash、逐项恢复、foreign隔离与DB逻辑指纹。
- [准确head固定点实物](reviews/2026-10-20-pr8-fixedpoint-proof.json)与[阻塞修复报告](reviews/2026-10-20-pr8-blockers-review.md)：新四份ELF、源码绑定、桥机器正反例及原CI范围。
- [主线接续记录](../../L3-RESUME.md)、[完整编译作业](../../code/docs/l3-compiler-job.md)与[语言门禁](../../code/docs/language-l2-l3.md)：已合入实现、历史范围和G5/G6后续。
- [P5/P6工程交接](../../code/docs/p5-p6-engineering-handoff.md)：reset-hold、DMA日志/别名、DAG失败及剩余真实门禁。
- [roadmap.json](roadmap.json)：控制台任务图的同源数据；旧GitHub快照及异机台账只作其对应时间的来源依据。

## 证据边界

- 图更新于2026-10-21 21:07:26 Asia/Shanghai；最新本地HEAD28fae186eade64aac9eec17fcc2fb30913b948f6。G6代码检查点19e1a19及其GitHub/CI内容保留原历史范围，本轮未重新查询远端。
- PR#7/#10/#8均已合入并完成本地同步；PR#3独立暂缓。P5完整恢复验收不是PR8代码合并的前置，原DMA guard、hold和reset契约全部保留。
- 23:13合并同步冻结报告保留56个dirty文件、533项任务相关文件SHA和DB四表逻辑未变的当时证据；该报告不改。后续C52/CXNASM3新正式复验及正常验收/集成、新增P5CTX1正常产生新记录，不再宣称当前DB未变；91项异机live路径仍隔离。
- 开发已完成、主线已集成、阶段验收是三个不同事实。本机没有任务书或ignored build回执，不能据此判未实现；源码、git状态快照、正式verification与独立报告构成异机恢复依据。
- PR8的161条异机任务（含23条paused）保留Git、ZIP与恢复台账，不导入本机live状态；旧快照相对原主线新增27项只作来源对照，不当新待办或当前任务数。
- 原pool:P2ALIAS1/P2HUGE1/P2PAT1已取消归档；P2扩展后来直接在PR8开发，不恢复这些旧派单凑数量。
- 发现异机codex:CX6/ cursor:CR43与本轮临时新任务同号异义。临时记录已经官方pause/archive并备份，NASM维护改独立编号CXNASM3；不让higher-rev同步规则混合不同契约。
- WINVERIFY1执行器早已随PR8同步；C52本轮新正式复验6 tests/0 skip、149.843秒通过，source_stable/process_stopped/execution_exited均true，正常accepted rev13→integrated rev14。旧submitted/None及中断记录保留在原时间线，不覆盖回填。
- 当前MCP只读快照：非归档124项，integrated=105、accepted=19，todo/in_progress/submitted/rework/paused均0；归档总数本轮未复核。异机161条仍未导入，任务数不代表系统阶段完成百分比。
- P5CTX1保持integrated rev7；P5CTX2与P2LIVE1均integrated rev6。本地实现及验证不计作旧G6 GitHub CI覆盖，P5与P2仍partial。
- P6首代DAG真实结构观察失败与KVM前置权限失败保留；它们不否定已接线的scheduler/init实现。P7/P8新版GUI/USB回归及外部真机门槛继续保留。
- 绿色L3B为有界宿主固定点；L3C的现有runtime5/compiler_job隔离profile及49模块自编译闭包已完成真实两启及持久产物验收。整体L3/L3A仍因G5完整语言覆盖保持partial。
- GitHub集成状态与阶段验收分开：本轮G6以真实两启、原始磁盘/物理转储及双独审通过，不仅依据CI绿色；P5/P2/G5不由该结论关闭。
- 本机Windows完整固定点两次均在seed执行前因固定ELF地址占位而失败，未计通过；临时链接尝试撤回，完整固定点由准确head的Linux CI及源码绑定回执证明。
- PR8合并前准确head三组CI均通过；main244b18c的完整CI39444684378 attempt2已20/20 success，原apt源403失败保留。PR11各候选head和各次实际G6结果单列，不跨head沿用绿色。
- 23:13同步验证的149项Python回归81.274秒、11项UI JS及14项桥/NASM/启动宿主检查17.529秒保持原范围。本轮C52与CXNASM3另有正式隔离复验和正常新rev集成；该02:26历史快照当时为122项，当前统计见最新MCP记录，不替代G6客体双启。
- CXNASM3新正式复验10 tests/0 skip、2.859秒通过，source_stable/process_stopped/execution_exited均true，经独审accepted rev5→integrated rev6；独立身份与异机CX6及旧临时记录分开。
- G6 run39467503226 attempt1在准确headf54c35c通过真实同盘两启（304.834秒、307.193秒）；SEED/STAGE1/STAGE2各1892648字节且逐字等于宿主ELF，SHA256 e7f2424dc2010cf5b66e32c14faafec87f1f0f76051c04bd4e9eee050d34c9f2；432项源码与453项冻结输入按Git原始字节核验；两次共1810份物理转储经两位独审，64KiB栈/双guard、56MiB arena、只读源码借页、W^X和无能力隔离通过；每启128页退休表清零、core/借页撤销、controller恢复及真实FLUSH均通过。首两轮失败仍在公开执行报告中，不覆盖历史。
- 旧P5/G6下一步报告与静态提案保留为历史；当前G6实施、真实失败、修复及各head CI以2026-10-21-g6-ci-execution.md为准，不能继续把提案未运行写为当前状态。
- M7/M8等历史环节中的“当前main/HEAD244b18c”属于PR8原检查点；最新G6代码合并/同步检查点以顶部及M11为准。后续文档提交可推进HEAD，不改变已验收的f54c35c代码/tree证据。
- 准确候选常规CI39467503240为20/20 success：712宿主测试0skip、931语言测试1项既有DONG_ASSEMBLER_FULL_INPUT条件skip、9组真实boot；P5 39467503250与输入39467503280通过。实际PR测试merge b905c1e、f54c35c与代码merge19e1a19同tree 394874cfe8ec7e4b0b4a9c857535781f88a957c6
- 合并后自动push检查在2026-10-20T18:20:41Z快照为39473893535 in_progress；39473893647 in_progress；与已通过的准确候选/同内容树检查分开，不冒称新push全绿，也不为重复CI阻塞此次集成。
- 历史02:26快照：P5CTX1 integrated rev7、122活跃=103 integrated+19 accepted，16归档/总138；该统计不再代表当前，原G6提交/CI范围保持不变。
- P2LIVE1完整release runtime7构建及真实桌面回归通过，先前超7760B/3664B失败与无manifest首轮拒绝保留；原装载2MiB ABI不变，余432B。P2大页正常根BSP生命周期不再列为未接线。
- P5CTX2正式21项零skip、真实control/fault两观察和独立完整离线复验已通过；reset confirmed/drain UNKNOWN继续分开，不证明DMA排空、unpin/free/reuse或驱动恢复。
- 本轮任务图仅更新本地已核事实、证据入口及当前统计；不修改协调器状态/数据库/派生index，不创建PR、提交或推送。来源见coordination/dongos_works/reviews/2026-10-21-roadmap-local-update.json。

## 历史接续快照（由顶部最新记录取代）（2026-10-21T22:35:22+08:00）

P2SIZE2与P2SMP3均已独立验收并本地集成integrated rev6：构建节省106496B，共享内核根在AP在线/调度前完成大页转换、全读者应答、临时表回收及最终封存持有视图；正式5项零skip，正常1/4核与唯一漏AP调用负控及完整物理归档复算通过，release runtime7为2006608B/余90544B。MCP快照130项=107 integrated+19 accepted+3 todo+1 in_progress。DeepSeek已领取L3A rev2，L3待其验收；Claude P2EXEC1/P2WC1已发布待领取，worker MCP已配置并独立握手验证。不建PR/提交/推送。P2通用EXEC/WC及调度后多CR3修改、P5 DMA安全回收、L3完整G5继续保留真实待办；历史GitHub证据未重查。

| 任务 | 状态与范围 |
| --- | --- |
| P2SIZE2 | 构建函数节与内核GC预算（本地集成）；codex:P2SIZE2 integrated rev6；正式3项零skip/source_stable，默认输出/ABI回归与真实四核桌面通过；释放106496B。；本项为构建预算前置；整体P2消费者按P2阶段继续验收。 |
| P2SMP3 | 共享根大页同步与永久持有视图（本地集成）；codex:P2SMP3 integrated rev6；正式5tests/0skip/source_stable；正常1/4CPU、唯一漏AP调用实际负控、独立raw replay通过；四核桌面/P5两观察回归通过。；范围为AP在线、调度前固定共享根；之后owner永久封存。整体EXEC/WC和任意多用户CR3操作仍归P2待办。 |
| DS-L3A | DeepSeek L3A：可变全局量原生闭环；已发布并由DeepSeek本人领取in_progress rev2。；完成候选生产与真实两模式原生闭环测试，再由Codex独立复验/验收/本地集成；不等于完整L3A完成。 |
| DS-L3 | DeepSeek L3：G5整程序差分回归；已发布todo rev1，依赖deepseek:L3A。；L3A验收后领取并完成真实差分框架、有限支持矩阵及已证实缺口回归。 |
| CL-P2EXEC1 | Claude P2EXEC1：动态执行别名事务；首交正式复验0tests/exit5，实际Dong编译E0201；隐藏别名扫描/本地flush/C oracle存在占位，未验收。；详细R1写入协调器；原负责人当前in_progress rev10，尚未通过验收。；按原任务完成真实完整别名闭包、权限事务和同步回调，修正ABI/epoch，真实Dong原生正反例及零skip正式复验后由Codex接线正常客体。 |
| CL-P2WC1 | Claude P2WC1：帧缓冲WC缓存迁移事务；本人客户端已领取in_progress rev2，尚未提交或验收。；完成原任务缓存迁移执行器、失败持有及原生正反例，再由Codex独立复验和真实消费者接线；不宣称WC真实性能。 |

## 历史P2碎片拒绝闭环（结果保留，最新接续见顶部）（2026-10-21T23:08:18+08:00）

P2OOM4已独立验收并本地集成rev9：正式3项零skip/source_stable，真实1/4核碎片free879但无order9，精确OOM且完整账本/页表/读者域不变；正常1/4核与漏AP同步负控归档再次独立复算通过。正常kernel仍2006608B/余90544B，316构建输入保持。MCP快照131项=108 integrated+19 accepted+3 in_progress+1 todo。Claude P2EXEC1首交编译失败、正式0tests，详细R1返修后重新领取in_progress rev8；P2WC1 in_progress rev2。DeepSeek L3A in_progress rev2，L3 todo rev1待其验收。EXEC/WC正常消费者、任意调度后多CR3、P5安全回收、L3完整G5仍待办。不提交/推送/建PR。

| 任务 | 结果 |
| --- | --- |
| P2OOM4 | integrated rev9；正式3项/0skip；真实1/4CPU free879且order9 OOM、零发布、完整状态保持，物理归档独立复算通过。 |

## 当前正式构建接续（2026-10-21T23:25:35+08:00）

P2BUILD5已独立验收并本地集成rev6：正式16项零skip/source_stable；补齐正式构建NASM分组帮助探测，真实NASM2/3兼容测试通过。NASM3完整release runtime7构建、实际1/4核共享大页与四核桌面/P5两观察、独立raw replay均通过。正常kernel2006608B/余90544B；316inputs匹配主目录。与旧NASM2非逐字一致，19ASM源相同，编码/对齐差异已审查并保留双份证据。MCP快照132项=109 integrated+19 accepted+3 in_progress+1 todo。Claude EXEC in_progress rev10（R1返修），WC in_progress rev2；DeepSeek L3A在途rev2，L3待依赖验收。P2 EXEC/WC消费者、任意调度后多CR3及WC真实性能仍未关闭。不提交/推送/建PR。

| 任务 | 结果 |
| --- | --- |
| P2BUILD5 | integrated rev6；正式16项/0skip；NASM3完整release与真实1/4CPU回归通过，已完成节点无本项待办。 |

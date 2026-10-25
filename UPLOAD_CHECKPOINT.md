# 2026-10-23 上传检查点

## 当前完成状态（2026-10-24T16:26:44+08:00）

2026-10-24 L3完成：L3ELFMATRIX1 已独立验收并集成本地主线 main 工作树（integrated rev6）。正式作业 ed37c79515f94c87a488e538ea6ba20d：51项/27组全部通过、零skip，963.657秒，source_stable及进程停止/退出均确认。148份目标ELF、166次实际观察运行和六类错误源码通过独立产物审计；157主目录源码与复验一致，G6的456源仍逐字绑定已验收的2,062,984字节编译器。因此L3/L3A剩余纯ELF矩阵门关闭，整体状态更新为complete。

完成回执：code/docs/l3-pure-elf-matrix.md；永久机器可读证据：coordination/dongos_works/reviews/2026-10-24-l3-closure.json。后续按既定顺序回到P2/P5；本次没有执行Git提交、推送或关机。下方“待验证/partial”等为历史检查点。

## 当前L3优先检查点

G6DOC1 integrated rev8；G6WAIT2/G6POOL1/G6RUN2 integrated rev6。当前fresh镜像实际同盘两启通过，961+961原始文件独审与固定点/回收检查通过，G6RUN2正式15项零skip。完整证据见 coordination/dongos_works/codex-works/reviews/2026-10-23-G6-current-run.md/json。L3A更广纯ELF仍待完成，再接续P2/P5。当前进展仅本地集成，尚未推送，不关机。

## 当前结果：负控证据补齐并本地集成

P2OBS36 已 integrated rev37，P2LARGE16 已 integrated rev68。正式独立复验110/65项、零skip；同R15冻结版本正常/漏刷/flush返回错误各双启动、严格回放及独立原始审计通过，主目录12/18文件与正式指纹一致后分别验收并登记本地集成。正常成功归档为normal-r15-wire2；wire1采集干扰失败和其他历史失败保留。证据见 `coordination/dongos_works/reviews/2026-10-23-P2OBS36-P2LARGE16-R15-review.md` 与同名evidence.json。本地新进展尚未推送，P2其余项/P5/物理WC待验仍未关闭，不执行关机。以下为此前各次检查点。

用户要求上传完整代码，随后明确取消关机。本次保存当前完整源码、测试、任务书、交付和进度记录；停止继续实施 P2/P5，上传成功并核对远端提交后保持电脑运行。

## 上传后继续推进（2026-10-23）

用户随后要求继续推进；上段“停止继续实施”仅描述此前上传检查点，不代表当前指令。
GitHub 已核实 main 为 `2d1804938daf6062e42f77b72ade5314c3a7ce9b`；以下新进展尚未再次推送。关机仍取消。

- P2OBS36 R8 submitted rev31：WHPX 首次启动按真实 P1_START、DESKTOP_READY 分阶段等待，各默认90秒；guest期限不变。独立作业 `3689afe78be34b4e8a68f87c0382a5c8` 通过110项、零跳过、源码稳定。含B兼容的本机预检150项通过。
- P2LARGE16 R11 新源独立作业 `5b4b8c1e64da4a0ead8e4569f81f8b10` 完整56项通过，零跳过、源码稳定，正常/漏刷镜像各1109源码、286产物完整校验通过。
- 新源正常场景 `normal-r11-obs-r8-wire1` 实际双启动通过，五个工作进程、B事务及后续PCID均完成；独立原始runner严格回放rc0。结果SHA256 `07d56741d3c61428117bcc5b4e9f996c7dabd073606096a29208141e7a6ad89b`。两个owned QEMU均退出0，无PFLASH错误。
- 新源漏刷场景 `omit-r11-obs-r8-wire1` 未通过：B实际正常完成、AP1读到新值，未形成精确旧TLB值负控；随后一次1078ms采集暂停出现无关的原1秒期限失败。结果SHA256 `858d3677177f6416351e3e5cdf2246c57a923212c719ddab0a5d105866b4a885`；独立原始审计1376文件闭合。没有把超时或未出现旧值标为负控通过。
- B的R12已完成并submitted rev55：负控未形成而一次性owner已正常完成时立即保存失败退出，避免继续采集混入后续无关错误。首次预检151项有1个夹具错误，修正后独立预检151项、7.371秒、零跳过通过。完整正式复验作业 `e4ee7de582284b38b40e504e5d7f1e6e` 于2026-10-23 16:09:39（北京时间）通过57项、零跳过，源码稳定，执行进程均退出；仍未验收/集成。
- 关机后用户重新要求按顺序继续；协调服务现已恢复，MCP已重新读取上述权威状态。本轮继续补齐动态漏刷分支命中记录和独立flush错误负控；不把新负控冒称为原stale负控通过，不安排再次关机。
- OBS/B均未登记accepted/integrated。framebuffer ledger、C/D、warm PCID完整实际验收和P5仍未完成；物理WC真机待验。
- 最新B任务已进入R13返修，in_progress rev57。正在实现动态命中记录、独立flush-return-error用例与完整代码范围校验；12个ELF/COFF对象和安全发布器C探针早期独立检查通过。尚未冻结并完成R13正式复验或新实际双启动，不沿用R12通过结果宣称R13通过。
- 后续R13六路径已冻结并submitted rev58，修后兼容预检157项/7.306秒/零skip、四源码稳定。正式作业 `cd564952ad754918b1e70d44693da265` 正在执行64项及三类新镜像构建，实际双启动尚未进行。首次157项中两个夹具失败原件保留：B字符串int已改bool；OBS同tick反控已改为严格早于sealed边界。
- OBS R9 submitted rev35，正式作业 `0553d178506e4026bec83d2adc021e7c` 已通过110项、零skip、源码稳定、执行进程均退出。该轮只修反控夹具与文档，生产规则不变；仍未提前登记accepted/integrated。
- B R13正式64项已全部通过，三镜像完成。随后error实际确认AP1 real0→1，但旧校验未容纳AP2/3 first-Failure记录早于后续requested发布；omit实际确认动态漏刷命中、AP1 stale-A/PTE-B、reader未ACK和旧2MiB逐字节保持，旧metrics.failed==0门拒绝预期failed1。两次归档result仍false，进程均退出0、输入稳定、无PFLASH错误。现R15 in_progress rev64，实施严格首Failure归因后的窄修，待新正式/实际复验；不重标旧失败。独立978原始文件scoped审计SHA `c75dc19e4fb093c0f8d57ae89e3d7d102772b664a6f7da926410b60a900b5d09`，只是分项证据，不是完整验收。

原始复验/审计材料保存在 `code/build/test/p2-historical36-review/`，VM归档在上述独立作业的workspace中，沿用构建产物忽略规则。

### 最新R15复验接续

同源漏刷 `omit-r15-wire1` 也已通过实际双启动、严格回放及独立raw审计（979/1087文件），精确stale-A/PTE-B、reader未ACK和旧2MiB保持均成立。结果SHA256 `b021868d2ebbf6e21771c926c05940554c1935a875f98baeda531101506780a4`，两进程退出0，无PFLASH错误。两类负控证据已补齐，当前进行同源正常双启动，尚未登记最终验收/集成。

P2LARGE16 submitted rev66：正式作业 `4363ad07fc1145dbba775a2d817710b6` 通过65项、零skip、源码稳定、执行进程退出；本机兼容预检158项通过。`flush-error-r15-wire3` 原runner实际双启动、独立严格回放均通过，独立raw审计闭合981/980文件，两个QEMU正常退出且无PFLASH错误。结果SHA256 `ba676ba92cfc2f01de1a47ea6367dfba366f17147d56a35adbb14d7f27e707ed`。此前启动超时及诊断结果保留，未改变生产等待期限或重标失败。当前继续同冻结版本漏刷和正常双启动；OBS/B尚未accepted/integrated，新进展尚未推送。

Intel SDM Vol3A §5.10.2.2说明处理器可随时失效TLB项，软件不能依赖保留；因此未出现旧值不证明刷新正确，也不足以断言WHPX进行了额外刷新：[官方手册](https://cdrdv2-public.intel.com/835754/253668-sdm-vol-3a.pdf)。

## 以下为此前上传时的历史状态

- G5FULL1、G5CLOSURE1 及 G5INT1 已按协调器记录完成独立验收和集成。
- P2 软件仍未全部完成。P2RAW38、P2SYNC40 已 integrated rev6。
- P2OBS36 R7 为 submitted rev27：独立复验作业 `aacbfb1bf6e0464fab534f784317e93b` 通过 105 项，零跳过，源码稳定且进程已退出；尚未登记最终验收/集成。
- P2LARGE16 R11 为 paused rev48，恢复状态 submitted。作业 `9dc3c0d73dfc4fdcbf6df654411bd0ce` 按本次上传关机指令停止，不能作为完整复验通过。此前 R10 原生/构建复验通过不替代 R11 的完整复验和实际运行验收。
- B 的历史运行中已有一次单启动完整事务观察，但后续 PCID 检查未通过，整体结果仍失败。新 R11 正常/负控双启动、严格回放及独立原始证据核验尚未完成。
- P2 的独立 framebuffer ledger、C/D 实际接线、warm PCID/错误 tag 实际验收仍待继续。真机不可用，物理 WC 性能待验。
- P5 本轮仅完成只读实施计划，尚未实施；原 P5CTX1/2 的既有集成状态保留。

协调器状态是权威记录；已有进度文档中的较早检查点属于历史记录，不应理解为本次完成声明。本次 Git 提交保存未完成工作，不等同于任务验收。

发布范围包含仓库源码和永久文档，排除现有忽略规则下的工具安装、构建产物、VM 镜像及本机数据库。公开 Git 状态 JSON 副本移除 `claim_token` 字段，其余字段保持不变；本机协调器原文件和数据库不改写。此处理不改写既有 Git 历史。

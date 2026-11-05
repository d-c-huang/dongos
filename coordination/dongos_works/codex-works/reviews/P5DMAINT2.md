# P5 DMA 主线集成与回归修复独立审查

2026-11-05 非作者 /root/review_recovery 只读独立审查 PASS。承接P5DMAINT1的生产迁移一致性/调度边界审查，原超时和取消保留。生产memory/host仍逐字匹配已验收候选。新增native_reachable不改变受测body；无场景/坏体/数值断言删减，不提高超时或禁用警告。

审查者未调用helper自证，用独立逐行全局标签解析及含裸标识符的符号扫描，复算全部58变体：exports/kept/trapped一致、保留函数体与header逐字不变、.rodata起全部静态data/后续区段逐字不变，未达入口严格ud2。

| 本地新证据（code/build/test/下） | 变体 | 正常exit0 | 负控数值断言exit1 |
| --- | ---: | ---: | ---: |
| p7-font-native/run-1098a90f264d | 10 | 32 | 8 |
| framebuffer-ledger/run-1fa5362aee90 | 12 | 20 | 10 |
| user-reuse-cursor/run-38237e600644 | 20 | 12 | 18 |
| compositor-pool128-native/run-b0f15a11a5ce | 16 | 10 | 14 |
| 合计 | 58 | 74 | 50 |

50次负控逐条检查均实际C数值/顺序断言，不是panic/trap/超时。FB最后负控为fb_other(i)==0x04060004；summary passed=true/30记录。C夹具NATIVECWARN1只为if-return加括号换行，语义不变，-Wall/-Wextra/-Werror保留。旧run-448b1b198215编译失败不计通过。

主代理7模块本地13 tests/203.184s，12通过且唯一旧C warning失败；其修复后FB定向1 test/92.924s/OK/0skip。此前生产DMA专项2项已通过run-a789f444fb6b、源码不变。正式八组15项仍须在冻结源码下重新复验，不以拼接本地结果代替协调验收。

SHA256：native_reachable 13bc55cb8d9592631cea700a623781a5721d1249823dba103ce299fcb71aca02；FB C dadc0e0cf7b338e039f3c3daa2bbe4f5da1b756c235e235e9039889418a7fa7d；GUI d083bd74eabf266c90ac2bffd97c7e31b540ad4cf53d006f23058e71983633ed；FB test 27bc79d88be0ee12484c8496d971ea3816487b50614f2369215617a491ba2cea；reuse 56be065f3af243eded44b37a80879392f62cf80f535d84daf728c9cc4c510590；compositor 1594aa53d667942a99016cc1a13643709f527b0b27d70daf0d1bd77e50673a02；memory e680f44af218f927c1ca3290601eb4af7943c2119bfe36915825fa9e67b6f3de；host dfc506308148e9c9b181a1a132b52d29a2bd0e450b704d540474a37bd415fe08。

没有services自动接线、DMA drain、物理回收、OS/VM或整阶段通过结论。已发布P5DMACALL1与P9RAWTRANSPORT1为后续有界研发任务，Cursor手动执行，前者依赖本集成验收。

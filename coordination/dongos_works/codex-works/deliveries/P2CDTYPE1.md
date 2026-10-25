# P2CDTYPE1 交付

按P2CD1接手中的真实TCG失败定位：GOP MTRR为UC、PAT4为WC，原D组件WB-only准入与既有cache_type_plan.effective_type表不一致。改为逐页解析MTRR后分别验证PAT WC->有效WC及PAT UC->有效UC；保留所有MTRR编码、重叠冲突、每CPU原始状态相等、运行中变化、PAT选择器、cache维护、deadline及held检查，不写MSR。

Intel SDM 325462-089表13-7：https://cdrdv2-public.intel.com/868137/325462-089-sdm-vol-1-2abcd-3abcd-4.pdf 。既有规划器已实现该表，未修改规划器。

实际隔离本机测试：python -B -X utf8 -m unittest tests.test_runtime_cache -v。R2为1test/194.246秒/零skip通过；debug/release、ELF/COFF、26场景、原五类真实生产坏体加恢复WB-only/忽略MTRR冲突两类坏体，共16构建组正常返回并由精确oracle拒绝。证据build/test/runtime-cache/run-796d5dbfa9bd，完整源/工具前后hash稳定。原R1五处失败为mtrr-changed被测试前缀误归为正例及冲突坏体断言文本不符；修正夹具后通过，失败日志保留于build/test/p2cdtype。

本交付仅组件，硬件边界为显式模型；P2CD1真实客体新构建和正负证明另行完成，不把本机通过代替客体门。无OS/VM、提交、推送；请求协调器独立复验后审查验收/集成。


## AI交付 2026-10-24T11:55:44+00:00 · codex-mcp-5f95564a50c4415d

真实TCG定位GOP MTRR UC/PAT4 WC的0x06150004。按既有effective_type与Intel SDM表13-7逐页证明WC/UC目标，不写MSR，不跳过原始状态/冲突/每CPU相等/维护/期限/持有。新增UC/WC/WT/WP/WB正例、非法/重叠冲突及两种真实坏体，保留原五坏体。隔离R2 1test/194.246秒/0skip，16构建组、两模式两格式；R1测试夹具失败历史保留。五声明文件真实移交前主目录SHA与snapshot base相符；本次模型组件测试未运行VM，P2CD1客体另验。请求正式独立复验。

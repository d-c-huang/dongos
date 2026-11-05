# P5RECBOUND1 作者自查记录（不替代独立审查）

2026-11-05。用户要求接手 Cursor 任务后，本卡负责人转为 Codex；被审修复同样由本会话 Codex 编写。因此以下是源码/契约/测试复核，不满足原任务的“独立”身份要求，不作为 accept/integrate 的独立意见。独立审查仍待非作者执行；没有修改被审源码，也没有自行验收。

已通过 MCP 重读 `codex:P5RECBOUND1` 最新 submitted rev4、原任务书及 verification。正式作业 `856e2bb666b84899b024da8f27be865c`：6 个 recovery 测试 + 3 个 DMA hold 测试，0 skip，returncode 0，source_stable/process_stopped/execution_exited 均为 true。2026-11-05 本次重新读取文件计算的 SHA256 与该指纹一致：

| 文件（源码根或 works 根相对路径） | SHA256 |
| --- | --- |
| kernel/user/device_recovery.dg | 304e83e073374c4212c6e1b5a69aa9ec626f440fd8ae87e2e459bdc207e28fbb |
| tests/test_device_recovery.py | 801a0e3612b48d3e8b10c69bef384f9a22e7873273d26cc383fab8d93ef4c986 |
| docs/device-recovery.md | cf3af64c52563ee76f15e2e07d12d70425ac91e55a170f3595db57ee20408b48 |
| codex-works/deliveries/P5RECBOUND1.md | 19a64db7c03dd744441f04b1b57dc658220adbdc549a7b6543f7dd18a5ad291d |

## 源码核对

`device_recovery.dg:163` 附近 `plan_ok` 在 `steps.len*16` 前拒绝 `len>MAX/16`；之后 `span` 先保护端点再进行 overlap，所以后续 `p+n` 不会在有效输入下溢出或回绕。覆盖完整声明片段，不仅是实际写入前缀。非空空指针及未对齐指针拒绝；长度零的 null steps 可用于无 DMA 的 quiesce，written 仍必须独立、对齐且有有效跨度。

`word_and_plan_ok` 先执行 word/plan 检查，然后补上 out_token 与 written 的 8 字节重叠检查，并保留 out_token 与全部 steps 的重叠检查。8 字节对齐的两个字若重叠必是相同地址，双方向相邻字不重叠。reclaim/reauthorize 的这些检查均位于任何表或输出写入之前。故障返回遵循既有原子性契约；没有改变状态机、设备代际、租约序列、零页和 quiesce 门禁。

## 测试核对

完整读取了原生编译/链接路径、C ABI shim、独立 Python Model、Driver 整表/输出哨兵比较及 6 个测试。`plan_driver` 先到达实际转换状态，边界拒绝不会被 STATE 错误偶然遮蔽。四个变长接口检查 MAX/16、其上两值、MAX、空片、未对齐、地址端点及尾部 written 别名；reclaim/reauthorize 检查输出同址、步骤尾部和表尾别名以及双方向邻接合法情况。reauthorize 的既有 ABI probe 固定八步，任意长度经同一 plan_ok 源码检查，测试不宣称该 probe 提供可变长度 reauthorize ABI。

新两类坏体分别显式模拟跨度截断和移除 out_token/written guard；均实际编译 debug/release。子进程须 returncode=1 且有 BOUNDARY_ASSERT，而正确体须 returncode=0 且有 BOUNDARY_PASS；panic 的退出 87、崩溃及超时均不满足断言，不能被计为成功负控。旧四测试保留：全状态门禁、代际与指针边界、每模式 1600 次独立模型比较、八类真实坏体。旧坏体通过 Python AssertionError 检出；进程崩溃不会伪装成该异常。

正式复验的 0 skip 是本次证据前提。测试类在缺少 NASM/GCC 时仍可能 SkipTest，因此未来不能仅看 unittest OK，仍须协调器零 skip 门禁。文档末段保留“4 项测试”的旧历史记录，2026-11-05 新段及正式记录已说明当前为 6 项；这是历史表述，不据此降低本次实测数。

## 保留门禁与结论

读取生产 memory.dg 的 destroy/unshare_range：PINNED 仍位于第一拒绝门；没有重新引入 release_dma/PINNED_BASE/PINNED_PAGES。test_dma_release 的三个项目是源码契约检查，不能当作硬件 DMA 排空或页表退休证据。边界修复无硬件 drain、撤映射后全核确认、物理回收或同盘重启证据，P5 仍未关闭。

作者自查未发现这两个边界修复的新阻断问题，旧复验指纹保持一致，未重复运行相同检查。独立审查身份要求尚未满足，被审任务继续 submitted；不建议用本报告绕过独立验收。

# P2OBS36 / P2LARGE16 R15 独立复验记录

本记录由 Codex 协调者依据冻结源码、正式独立作业和真实客体证据编写。正常和两类负控均已完成独立复验；协调器已分别登记 OBS accepted rev36 → integrated rev37、B accepted rev67 → integrated rev68。

## 最终正常复验与本地集成

`normal-r15-wire2` 在未改源码、镜像和期限的条件下双启通过原runner及严格回放，独立raw审计1930/1894文件；正常完整生命周期、实际读者和后续PCID检查通过。结果SHA256 `f684f9e8ea96dd87834c738bb9125570fefa4fa5b6e68921ffc3369e658d6a4b`。两owned进程退出0，无PFLASH错误。先前wire1失败保持false；此次成功不承诺任意宿主负载下的观察稳定性。

主目录OBS12/B18文件均已真实存在并逐项匹配正式复验指纹，随后才登记验收与本地主线集成。机器可核对汇总见 `2026-10-23-P2OBS36-P2LARGE16-R15-evidence.json`，SHA256 `3acfd3f25843101746c466b2ccfce50c4caf55ddbff96c43858656afe17add83`。该汇总中的submitted rev是验收前冻结来源，当前集成状态见协调器及独立登记回执。

## 源码与契约审查

- OBS R9 仅修正同 tick 下无实际篡改的反控夹具：queued_ns 必须严格早于 sealed_ns。生产采集、暂停边界和客体期限没有因此改变。R8 的启动分阶段等待及 R7 的 PFLASH writethrough 规则沿用此前独立审查；并不承诺 WHPX 无启动或采集延迟。
- B R13 的 16Q 动态回执绑定实际 AP1、Domain、窗口和替换序号，记录实际 flush 结果及注入结果，最后发布。正常回执全零；漏刷与返回错误有不同 magic 和源构建契约。完整函数机器码范围以符号端点和精确长度绑定，不能用截断前缀通过。
- R14 只容纳返回错误时 AP2/3 首个失败记录与后续 requested 发布之间的源码允许顺序：历史 requested 为 pre/post 且不超当前值；CPU0/AP1、ACK、事务和失败归因仍严格绑定。
- R15 漏刷指标例外仅在完整首 Failure 逐 CPU 归属于同一已完成替换 post 后生效；AP1 必须是实际读者 Hardware，其他 CPU 仅接受支持的 Held 传播。正常及旧契约仍要求 failed=0。实际 stale-A、新映射 B、读者未 ACK、旧 2MiB 完整保持和零 retire/reclaim 仍分别校验。
- 错误发布短窗口保留首次采集，只允许同一事务的有限后续采集；不以超时、其他故障或 owner 正常完成代替负控。

## 已完成复验

OBS 正式作业 `0553d178506e4026bec83d2adc021e7c`：110项，零skip。B R15 正式作业 `4363ad07fc1145dbba775a2d817710b6`：65项，零skip，三类源码绑定镜像构建完成。两作业均 source_stable、process_stopped、execution_exited。另有本机兼容预检158项通过。

`flush-error-r15-wire3` 两启通过原runner及严格回放，独立raw审计981/980文件；结果SHA256 `ba676ba92cfc2f01de1a47ea6367dfba366f17147d56a35adbb14d7f27e707ed`。

`omit-r15-wire1` 两启通过原runner及严格回放，独立raw审计979/1087文件；精确stale-A/PTE-B、reader未ACK与旧2MiB保持均成立。结果SHA256 `b021868d2ebbf6e21771c926c05940554c1935a875f98baeda531101506780a4`。两类负控共四个owned QEMU均退出0，无PFLASH错误，源码和工具输入不变。

原始材料在 `code/build/test/p2-historical36-review/`，VM归档在上述B作业的隔离workspace内。raw审计报告本身是分项证据，不单独等于整个任务验收。

## 保留的失败与范围

R13旧oracle拒绝的两个归档仍为false；候选oracle对旧raw诊断不替代新源实际运行。R15返回错误前两次P1_START启动超时和单独启动诊断也保留，不混入成功两启结果。

正常 `normal-r15-wire1` 总结果false：第一启已采集完整B及后续PCID，第二启在GUI控制前UART响应超时。独立444文件审计显示首次暂停2922ms，恢复后AP1/AP3首Failure为Timeout，B尚未触发。结果SHA256 `464d9fd147e02ed35a96ab0662ffa71f90099eee6f290923dc8d06667a555517`，审计SHA256 `14ffe2d551ead58c6780f1131f8796885990d5680f40b6fb366fc52e761b486c`；两owned进程退出0，无PFLASH错误。该观察与采集干扰一致，不证明所有宿主延迟的具体成因。保持原期限，进行一次同源正常双启复跑。

本记录不关闭整个P2、P5、物理WC真机性能或任意其他消费者任务。不提交、推送或关机。

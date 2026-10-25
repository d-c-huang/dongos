# G6 宿主准备独立复核与新优先级

用户要求 P2/L3 中先完成剩余较少的一组。当前按实际阶段门禁归组：L3 有新 G6 客体回归和 L3A 更广纯 ELF 覆盖两组；P2 有 framebuffer ledger、C/D 实际接线、独立 warm-PCID 三组软件工作，另有物理 WC 真机待验。此为范围比较，不是预计工时，也不是已建任务卡的精确数量。先恢复 L3，不重复已集成 G5 和历史 L3C。

## 原始证据复核

G6PREP1 integrated rev6，正式作业 `7b55181e05024fdba45198cdcf4858cd` 的五组检查为1+15+2+3+1=22项、零skip，全部退出0且源码稳定；耗时分别352.078、1.047、31.906、20.344、161.438秒。宿主准备receipt自身耗时351.438秒，不能与五组总耗时混同。

本轮独立stdlib审计重新读取318个产物SHA；冻结输入445源、7harness、4fixture、12profile全部匹配。49模块编译器源码仍绑定原冻结版本；stage1/stage2逐字节一致，2,046,376字节，SHA256 `2bda587a6842913879eb6bf0445202066adb68baef06d06593ff0f3ee787defa`。独立解析四种ELF：编译器500页、controller(shell)1172页、fs113页、block48页。

源码blob491,683字节，相对512KiB余32,605字节；ELF相对2MiB余50,776字节。arena仍56MiB，栈64KiB。上述ELF映射页数及静态预算不证明动态managed frame峰值；原准备明确 `dynamic_managed_frames_verified=false`。此前静态总16265/16384页的记录仅保留为原审查结论，本轮不以它替代客体峰值观察。

独立解析64MiB FAT磁盘，两份FAT一致，SOURCES/SEED链逐字读回等于原blob/ELF，STAGE1/STAGE2条目均为空。两次改字节负控分别拒绝fixture ELF和SERVICES产物篡改，原始前后SHA恢复一致；构建命令均退出0且日志存在。`guest_executed=false`、`actual_qemu_executed=false`、boot_calls=0。详细可复算输入和SHA见[JSON回执](2026-10-23-G6-host-ready.json)。

## 当前源码差异与接续

当前主目录已有12个不同的内核/构建输入相对该准备快照发生变化，清单在JSON中；编译器固定点证据没有被这些变化自动转换成新内核证据。因此后续应先从当前源码生成新的冻结G6构建，再执行实际客体自编译、FLUSH、同盘双启、隔离和退休复验。不能直接用旧镜像关闭当前G6。

deepseek:L3 integrated rev13、deepseek:L3A integrated rev11 为原任务既定范围已完成；整体L3/L3A仍有上述阶段余项。G5完整NASM语言矩阵已通过，不代表内建assembler已覆盖XMM/atomic/全部受限asm。历史G6只绑定旧head/runtime5/49模块profile，不外推新2,046,376字节编译器。

本任务只进行文档及宿主原始证据审查，没有运行OS/VM、修改生产代码、提交或推送。最终独立入口检查和验收状态以协调器为准。

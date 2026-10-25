# 当前源码 G6 接续

## 最终实际结果

run-b54a8a8d615b 原 runner 两启全部通过，两个 owned QEMU 均正常退出0。独立离线审计（禁止创建进程/网络）逐项重放原 live、P5 physical、retirement 检查；每启961原始文件长度/SHA通过，FAT双副本一致，SOURCES/SEED正确，STAGE1==STAGE2==2,046,376字节宿主固定点。128页编译器页表全零、REQUEST清空、RUNNING/FAILED归零、LAST成功逐字段检查通过。独立审计SHA256：086c1523670c306625e05fce05c7a569a5219176f09ffc9dac93b238ecd1641e。

实际运行采用 dc797113b18f48799f55d0b1ed135f28 冻结检查器及 e8510c2b91054ebe941e0c6d0eec57af 的fresh修复后镜像/夹具；仅检查器适配，没有重新编译生产代码。运行前后冻结输入无变化，当前主目录生产源逐文件与实跑冻结输入一致。证据、旧失败审计、fresh宿主准备审计均嵌入同名JSON。G6RUN2等待正式定向复验与协调验收登记；本结果只关闭当前G6，不替代更广L3A纯ELF或P2真机WC。

以下为保留的过程记录，阶段性“待定/运行中”以本节最终结果为准。

最新：run-662c6cec8a01 完成编译和服务退出，managed_frames=16266；整体因旧 P5 检查器固定三个静态池而失败，未第二启。独立审计700原始文件通过，失败结果保持，审计SHA256 2c8cb59af5b190a2d25268bfd894cff3568a09fd74b04f12a11af1385d40da5b。G6POOL1 根据真实构建 profile 证明动态池的身份/容量/已分配arena范围/互斥/逐页supervisor RW NX WB，正式20项零skip通过并集成rev6，未弱化原逐级跨池检查。新实跑 run-b54a8a8d615b 使用 dc797113b18f48799f55d0b1ed135f28 冻结检查器、原修复后fresh镜像与fixture；生产源码未变化，无需重复编译。日志 g6-pool-fixed-guest.log，结果待定。

G6RUN2 in_progress rev2。G6DOC1已独立验收并本地集成rev8（15项零skip）。当前源码冻结于正式作业5279fdea41ba4447b776fdf4416206ec的workspace；开始在该隔离副本执行既有test_compiler_job_preparation，生成全新固定点fixture与runtime5/compiler_job镜像。此次准备及后续实际客体尚未完成，不能沿用历史G6或旧PREP1判定通过。

原始构建日志：code/build/test/p2-historical36-review/g6-current-preparation.log。全新准备已通过1项零skip，406.055秒。独立stdlib复算328个产物、456源/7harness/4fixture/12profile，所有当前主目录源码输入匹配。新夹具仍为2,046,376字节固定点，源码/ELF预算保持，FAT双副本、逐字内容及负控恢复通过；详情见同名JSON。

已启动原run_compiler_job_qemu的TCG单BSP实际同盘两启流程。此时真实客体尚在运行，仍未验收；guest日志为code/build/test/p2-historical36-review/g6-current-guest.log。不放宽预算、期限或同盘双启要求。

首轮run-c36c9a232b26失败，第二启未执行。客体输出L3_RESULT 0/3/0/0，证明编译作业返回成功；随后block_failed_op=4、status=0x05030007，FAT传播0x05040004，服务退出0x050b0002。失败在FLUSH等待，不归因为编译失败。live原始观察managed_frames=16265/16384、14336页arena、16页栈、4guard、只读源码/W^X/无能力均通过；这些分项不等于持久化或完整G6通过。开始一次同源同规则复跑，保留本轮原归档，不扩大100000次轮询或3600秒总期限，不跳过真实FLUSH。

复跑run-21643a475546再次在FLUSH返回0x05030007；两次各700文件hash审计、禁止进程/网络的原live校验离线重放、独立FAT解析均通过，原整体结果仍false。审计SHA分别099aa1299443f937b3e52a833fb9807b60809f1be037973e24ae6847b9511641、89a6cea8af8bf0ad12ab752f884df761044b80c2b57310629940d3f28ce3fa08。

已独立完成G6WAIT2组件修复并本地集成rev6：显式timed接口按AHCI/NVMe已有5000ms命令契约使用真实单调时间，旧接口与共享布局不变；这是明确的新驱动等待契约，不重标旧100000poll失败。4项正式复验/24场景/5坏体/两模式两格式通过，原G6总3600秒不变。G6FLUSH1最初共享Ops扩张设计未实施，已释放并暂停rev4，由G6WAIT2替代。

当前在e8510c2b91054ebe941e0c6d0eec57af冻结workspace全新重建包含修复的G6镜像；仍未声明客体通过。

修复后fresh准备run-ed1eb11f565f通过1项/422.051秒/零skip；独立复算328产物、456/7/4/12输入且当前主目录无差异，编译器固定点/预算保持。block映射49页（此前48页），须在新客体确认managed实际值。audit SHA256 905a7455cf42389a7eeae8554cef49f447c60a3a813a516e130dfc3702e9ebc4。原runner已启动新镜像双启，日志g6-fixed-guest.log，等待实际结果。

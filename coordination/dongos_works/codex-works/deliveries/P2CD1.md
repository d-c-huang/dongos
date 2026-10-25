# P2CD1 Codex接手记录（进行中）

已登记codex:P2CD1并领取rev2。Claude原交付/补丁保留，主目录未应用补丁，所有实现与测试在独立workspace中进行。完成B/C/D接线审查、runtime7零静态池oracle/runner适配和四类SMP夹具补依赖；runtime5/6统一既有动态池后完整release构建各1,986,960B，runtime7为1,991,056B，2MiB上限不变。

原PCID/历史采集/bulk95项，组件/账本/绘制门/原服务9项，快速poll/唤醒2项，readonly/fault3项和新接线控制3项均通过，零skip。最初四夹具R1中fast/wakes通过，另两项因current_files缺失失败；修后R2通过，历史保留。

受控TCG诊断前两轮C已实际完成13屏障、2份回执、页表数恢复和持有；D绑定前硬件准入0x06150004，原始失败保留。第三轮密集采集下C出现0x06140002，保留不计通过。旧A原始硬件BOX揭示GOP MTRR UC/PAT4 WC。另登记P2CDTYPE1，使用已有cache_type_plan有效类型表与Intel SDM表13-7逐页验证WC/UC目标，不写PAT/MTRR；需单独独立验收。

最终普通及两个真实遗漏poll坏体镜像、实际客体正负证据与正式协调器复验仍在进行。未验收、未集成，未提交推送；不把warm-PCID复用、物理WC真机门标完成。


## 接续检查点（独立复验进行中）

P2CDTYPE1 已独立验收并主目录集成rev6：正式82cf626668fe437c803de857b41405c0，1test/213.437秒/零skip，源码稳定且进程退出；本机R2 1test/194.246秒通过，16构建组。父任务隔离副本使用同一已验收字节。

父任务B/C/D宿主三镜像回归58项/1065.190秒零skip通过；PCID/历史/bulk原95项通过；四类focused夹具修后均通过；原组件/账本/绘制门/服务9项通过。新raw verdict及slot0动态池/实际坏体/暂停边界编排控制4项/2.281秒通过。B的large_try/large_identity/large_check与主目录逐块相同，未改Domain/Bridge deadline。

TCG及WHPX失败过程均保留。查明新runner先前shell返回已暂停却sleep12秒，造成观察预算超限；已显式resume后再等待，并加能拒绝旧行为的编排测试。原始B/AP超时及C Authority仍保留，不重标通过。WHPX默认max模型UEFI的feature-control #GP亦保留。当前采用此前P2 R15真实成功的明确WHPX配置：q35,kernel-irqchip=off；CPU host,-vmx,-mpx,-sgx,-sgxlc。读取原R15成功归档确认参数，非猜测替换源码。

最终冻结构建目录为build/test/p2cd/sealed-normal、sealed-omit-exec、sealed-omit-cache；镜像及客体正负证明正在完成。主目录尚未应用父任务生产补丁，父任务仍in_progress rev2，不得冒记验收/集成。父工作副本：coordination/dongos_works/.local/manual/P2CD1-codex-20261024/workspace。

## 最终冻结交付与源码审查

源码1121输入冻结，主目录无无关源码差异。runtime5/6/7内核分别1,986,960 / 1,991,056 / 1,995,152B，保持2MiB。B三处事务逐块相同，Domain/Bridge/ACK/观察预算未放宽。四类focused夹具修复；原95项oracle、组件/账本/服务9项、focused2+3项、runtime-large58项、新控制5项、builder10项均实际零skip通过。P2CDTYPE1组件有效类型修复已正式独立验收集成rev6；P2CDBUILD1补齐初始漏列builder预期0，单独复验登记。

最终guest源码和工具绑定构建为sealed-final-normal、causal2-omit-exec、sealed-final-cache。新runner连续通过原UART关闭GUI及启动5个工作负载，复用bootstrap历史镜像，无客体RAM/寄存器写入；完整校验source/artifact/profile、UART字节边界/次序、初终Catalog和raw capture。正例C13屏障/两回执/8PF/4CPU调用，D5屏障/两轮/完整8100页收回重映射；负例首次STORE/READ真实遗漏poll、精确请求掩码及ACK0、held/poison/Domain失败和BSP错误链。若AP先到等锁期限，另须原始WAIT到期证据，不能将任意失败算通过。

normal: D:\projects\2026\dongos\coordination\dongos_works\.local\manual\P2CD1-codex-20261024\workspace\build\test\p2cd\final-normal-r1\result.json；result SHA256 3b2ab4e80494ccac57f7d02777052207058cd4342b16c97f680c27c9d47ac171；raw files 488；seal passed；QEMU清理完成且process_alive=false。

omit-exec: D:\projects\2026\dongos\coordination\dongos_works\.local\manual\P2CD1-codex-20261024\workspace\build\test\p2cd\final-omit-exec-r1\result.json；result SHA256 0d061c22051c28e9ac130b740015ebb1e66b89eb320d358b84a400bc81c1c095；raw files 478；seal passed；QEMU清理完成且process_alive=false。

omit-cache: D:\projects\2026\dongos\coordination\dongos_works\.local\manual\P2CD1-codex-20261024\workspace\build\test\p2cd\final-omit-cache-r1\result.json；result SHA256 cd1444c4c37156b0b7c38050f05ce1b003d07f8a72164961de935ffacf0edb71；raw files 491；seal passed；QEMU清理完成且process_alive=false。

旧失败报告和不稳定构建全部保留，不重标成功。原正常w1/wmax1两轮属于判据修改前历史诊断，当前门以上述最终冻结三类为准。正式独立复验、验收及集成状态以协调器记录为准；本报告不预先宣称验收。warm-PCID、物理WC性能及真机门未接受。无commit/push。


## AI交付 2026-10-24T13:45:30+00:00 · codex-mcp-5f95564a50c4415d

已完成Claude原补丁审查与剩余修复，原交付保留。B三事务逐块相同，C真实buddy/PF entry/trace，D真实账本/GOP有效类型/根快照接线；runtime5/6/7零静态池，2MiB不扩大，内核1,986,960/1,991,056/1,995,152B；同步oracle与四类focused夹具。修复观察runner暂停等待错误，连续UART关闭GUI/启动5worker并复用bootstrap历史镜像，严格字节/hash/次序/Catalog来源。负例按源码真实请求mask和本地/AP先到期限的精确错误链校验，新增真实raw反控；旧失败及source不稳定构建全部保留不重标。本机原oracle95、组件账本服务9、focused2+3、runtime-large58、新控制5、builder10项均0skip通过。最终冻结1121源码的全新正常/C遗漏poll/D遗漏poll实际WHPX guest首轮均通过，offline seal分别488/478/491 raw文件；C13屏障/2回执/8PF/页表75恢复，D5屏障/两轮/8100页完整回收重映射，4CPU ACK与真实操作校验；QEMU全部清理退出。最终guest目录：.local/manual/P2CD1-codex-20261024/workspace/build/test/p2cd/final-normal-r1、final-omit-exec-r1、final-omit-cache-r1。P2CDTYPE1已独立集成rev6；漏列helper补登记P2CDBUILD1另行复验。28份声明/补充文件逐份基线预检、备份、真实移交hash校验，主目录完整1121输入与冻结客体源码图一致；transplant-manifest.json在手工副本父目录。源码/契约审查写入codex-works/reviews/2026-10-24-P2CD1.json。请求协调器独立定向复验，尚不宣称验收；warm-PCID和物理WC性能/真机门未标完成。无commit/push。

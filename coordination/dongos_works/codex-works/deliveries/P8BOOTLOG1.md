# P8BOOTLOG1 交付

真机 USER RUNTIME R1 仍残留 S19/error0。该画面不是当前位置证明。本轮没有声称已定位该 Intel 的唯一根因。

实际修复：`services_write_bytes` 先接收全部已校验日志到 4096 字节环，再尝试可选 UART。保留发送、未发送、状态及超时计数；0xff 缺席、65536 次忙轮询或校准 TSC 100ms 等待预算到达后停用串口，日志 syscall 返回已接收。原 syscall 参数/内存范围检查、全部服务、CPU 拓扑、BKL/EOI/时限和设备权限不变。配置 5 的 init 在真实退役清理后若不再 managed，向现有桥错误传播非零退出状态或明确零退出/异常编码；正常应用的退出不升级为内核故障。R2 私有构建仍连续执行，无成功停车；现有可信失败页接口和 ABI 未变。

实际验证（提交时完成）：

- `python -X utf8 -m unittest tests.test_services_console tests.test_init_lifecycle tests.test_user_runtime -v`：7 tests / 124.563s / 0 skip，日志 `build/bootlog-native-r1.log`。
- 串口原生测试执行真实 ASM，只替代 IN/OUT/RDTSC。固定并核对 HEAD 原例程 SHA `1dbf09cb124ed6eea8a69efb466eae04addf4a5cb233a0b5c15b82357ee00ac1`：忙 UART 时原实现真实轮询 1048576 次、返回 0x050b0004，真实 init 在启动子服务前退出；新实现同一真实 init 完成三次启动和一次 kill。debug/release、C O0/O2、ELF/COFF、4096 环回绕、缺席/忙/延迟就绪/部分输出/时钟回绕/停滞/零预算/零长度；丢环记录、返回串口错误、轮询超限三个真实坏体被断言拒绝。
- init 致命退出原生测试执行真实 smp_service / retire_one / Catalog / Domain / queue。零退出、非零退出、CPU 异常均在退役/远程 ACK/资源撤销后上报，两个坏体被拒绝；硬件/perform 边界为明确模拟。
- `tests.test_user_smp_services.Tests.test_actual_service_callbacks_and_retirement_before_withdrawal`：1 test / 298.297s / 0 skip；普通应用 exit/fault/GUI 和 24 坏体继续通过，日志 `build/bootlog-services-regression-r1.log`。

完整 fresh normal 与 R2 candidate 从当前来源重建。Root 连续 8 CPU 两启动验证位于 `build/hardware/user-runtime-20261027-r2/vm-r2/`，TX 恒忙的独立 never-publish fixture 与 RAM 日志观察位于同目录 `uart-busy-fixture-r2/`、`uart-vm-r1/`。提交时完整 VM 仍在执行，最终通过/失败必须读取实际 result.json；不能把本交付文本视为 VM 已通过。验收须在独立复验与 root 完整测试完成后填写实际审查 note。

保留的失败：首故障注入脚本遗漏重定向 NASM 列表文件，使正常树仅 `services_run.lst` 改变，严格校验拒绝 `vm-r1`。已执行原完整汇编命令恢复，整个正常树 SHA 与既有候选清单完全一致；故障版本新目录 `uart-busy-fixture-r2` 的列表输出已隔离。源代码与实际 normal 运行对象未被改写为故障版本，不抹除失败记录。

用户已确认原 SanDisk H: 插回。写盘须在通过上述门禁后另核对实际身份、旧四文件哈希、备份、同步回读和 FAT32 rb 检查。实际真机完整桌面仍待本轮启动反馈；不宣称 VM 代表真机通过。


## AI交付 2026-10-27T16:10:32+00:00 · codex-mcp-5c7de4d7c45b49d1

已完成可选UART内存日志接收/双重有界发送和init退出清理后错误传播，R2连续profile无成功停车。真实旧ASM+init复现忙UART导致0子服务退出，新实现真实init完整3spawns/1kill；新console/initfatal正反例、既有init/runtime共7tests124.563s0skip，独立普通服务回归1test298.297s含24坏体0skip。代码/文档和交付已落盘；freshnormal/candidate已重建。Root正常两启动与恒忙UART fixture完整VM仍在执行，验收前须实际读取通过结果；首VM因测试脚本覆盖唯一listing被严格拒绝，已原命令逐字节恢复并隔离新fixture输出，保留失败。尚未写H、不宣称Intel根因/真机桌面通过。


## AI交付 2026-10-27T16:28:07+00:00 · codex-mcp-5c7de4d7c45b49d1

返修完成：init_detail仅在通过真实Frame校验的exit(0xff)操作中采集非零rdi；无效syscall帧/event258明确使用0x04050001，CPU异常继续050b0100|vector，零exit050b0003。真实smp_service/退役/ACK/revoke测试增加invalid/irq-invalid和把参数误作退出码坏体，debug/release均拒绝；普通应用分支不变。当前来源7tests141.875s0skip全通过，build/bootlog-native-r2.log，services-console/run-1ada82e36df7与init-fatal/run-e1f8744386b0。此前完整普通服务回归1test298.297s0skip、24坏体通过。此前20261027-r2正常8CPU两启动已通过；其UART故障VM已到桌面键鼠/文件写入阶段，为本轮来源修正主动结束并保留失败，不计为通过。新的冻结来源在build/hardware/user-runtime-20261028-r2重建，最终正常两启动与TX恒忙完整VM尚待完成，独立复验与VM实际结果通过前不得验收或写H。不宣称Intel根因/真机桌面通过。

# P8BOOTCONSOLE1 delivery

Implemented explicit continuous BOOT LIVE R1 private profile and the actual
456-byte producer. Original normal profile and service ELFs are preserved.
Exact return/capture/log hooks, 8x40 bounded rows, private punctuation font,
original framebuffer Gate, permanent disable before compositor IRET and the
previous fatal screen are included. This is diagnostic visibility work; the
Intel machine's persistent S19 cause and physical desktop pass remain unknown.

Native `tests.test_startup_console` passed locally (2 tests, zero skips),
executing debug/release, C O0/O2, ELF64/Win64 assembly, and five wrong bodies.
The first build overlapped a diagnostic text-range correction and correctly
rejected its changed inputs; it will not be published. A fresh frozen-source
build, root eight-CPU desktop and fault-log VM evidence, independent verification
and USB publication are required before acceptance/integration. Their immutable
results and precise paths will be recorded in the coordinator's review note.

No physical desktop success is claimed by this delivery.

Rework: the first native/independent five-test run and actual missing-media
screen (76,440 pixels) passed. Full desktop runs then exposed two FLUSH timeouts
and one runtime/BKL failure; the ordinary control passed file writes but later
failed HID consumption. These are retained, not accepted as full passes. Actual
snapshots confirmed the console stopped at compositor entry. Added an ASM
permanent-disable fast path to avoid entering the Dong producer afterwards,
plus two executable wrong-ASM-body tests. No USB deadline/oracle was relaxed.
All changed source requires fresh build and independent verification again.


## AI交付 2026-10-28T08:23:16+00:00 · codex-mcp-08a83870ee38446d

显式 BOOT LIVE R1 实现已落盘七个授权文件；实际 producer/ASM 本地2 tests/0skip PASS，debug/release、O0/O2、ELF64/Win64、五个坏体均实际执行。完整构建与 root VM 正在进行，尚未声称通过或写盘；先对冻结源码排队独立模块复验，验收另需 root 全流程与故障显示证据。


## AI交付 2026-10-28T08:59:18+00:00 · codex-mcp-08a83870ee38446d

返修增加真实汇编关闭标志；compositor首次返回永久关闭后，tick在GS/CR3/IF读取和Dong producer调用之前返回。新增asm-no-fast/asm-no-close实际坏体，现原生2 tests/0skip PASS（7坏体/debug release/O0 O2/ELF64 Win64）。保留前轮VM失败与普通对照；不宣称USB超时根因已修复。正在冻结源重建并重做完整VM，尚未写H。


R2 rework (2026-10-28): Intel reached actual init logging, cfg2 exited with
05060001 and cfg4 with 07310001. These are block setup and input USB readiness
failures, not evidence of a S19 lock hang. Preserve earliest USB issue and
terminal controller failure separately, including contiguous port/phase/held
context. Complete nonzero hex records only; fragmented input and wrapped-ring
prefix are bounded; subsequent init/revoke logs do not overwrite the evidence.
No driver changes or claimed hardware fix. Existing desktop-regression failures
remain recorded. Native five tests passed (2 startup + 3 runtime); nine faulty
producer/ASM bodies rejected. Independent checks and exact-image VM pending.


## AI交付 2026-10-28T09:59:25+00:00 · codex-mcp-b0b0a56f66684e46

R2修正真实Intel照片暴露的日志被init级联覆盖问题：独立保留最早USB异常及最终xhci/hid/proxy错误和连续detail；精确完整非零记录、分片/批量/环形截断/超过4096字节后仍保留。Report792B保持原456B偏移，原ASM早退/首次compositor关闭不变。原生startup2 tests通过（9坏体，debug/release、ELF64/Win64、O0/O2）；runtime3 tests通过。根因仍未知，未改驱动/重试/DMA；先前完整桌面回归失败仍未解决。本轮fresh build和实际故障屏验证进行中，未写U盘，不申请验收集成。


## AI交付 2026-10-28T10:38:03+00:00 · codex-mcp-b0b0a56f66684e46

仅将显式EFI版本标识及其断言/文档更新为BOOT LIVE R3，配合新P8XHCIPRECHECK1服务诊断。producer/renderer/ASM和792B布局未更改，4条预检日志+原error/phase/held7行适用已有sticky窗口。完整HID文件回归前轮失败仍未解决，本轮重新排队5项独立检查。新镜像root实际故障显示/正常启动与写盘尚未完成，不申请验收。

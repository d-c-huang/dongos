# P8XHCIPRECHECK1

Actual photograph: 08110002 with phase=0 and held=0. Unsupported is shared by
multiple precheck predicates. No specific firmware/extended-header value was
present in the photo, so no permission or supported-feature gate is relaxed.

Added separate 40-byte PrecheckReport and exact precheck decision samples;
service logs CHECK/REG/VALUE/AUX before original error/phase/held. No additional
MMIO reads or hardware writes, unchanged Setup/Caps/State ABI and return codes.
New calls reset stale records. Native tests run actual precheck plus extracted
actual service formatter, 42 cases, both modes and O0/O2, ELF64/Win64, four bad
bodies, callback read error, Intel base caps plus labeled synthetic extended
records, post-decision register changes and zero DMA/input writes. Native new
1 test and old controller2 tests passed. Scratch/independent and real VM pending.

Root physical boot success is not claimed. Version R3 is handled under the
existing BOOTCONSOLE task. User explicitly confirmed original SanDisk H inserted.


## AI交付 2026-10-28T10:37:41+00:00 · codex-mcp-b0b0a56f66684e46

已实现独立40B预检诊断，原Unsupported谓词/返回码和公开Setup/Caps/State布局未改变，记录真实决策样本并在原service失败路径输出CHECK/REG/VALUE/AUX；无额外MMIO读取或硬件写。新实际precheck及实际formatter测试1项通过：42cases/exec/debug release/O0 O2/ELF64 Win64，四坏体拒绝，精确read counts、输入/DMA不变、改变MMIO后日志仍为原始样本；旧controller2 tests通过。Fresh构建和rootVM进行中，未写盘，Intel具体拒绝条件仍未知，不宣称硬件修复。

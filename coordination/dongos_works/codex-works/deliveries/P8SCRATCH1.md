# P8SCRATCH1 — Intel xHCI Scratchpad support

User requested the fix after CAPS R1 returned HCSPARAMS2=14200054 (34 Scratchpad pages and advertised restore capability), mask C and an extended-capability pointer at BAR+8000. Implemented the real shared DMA layout and initialization, not a guard bypass. Detailed design and physical-test limitations are in code/docs/hardware-xhci-scratchpad.md.

## Actual files and contract

The shared usb.xhci_dma layout preserves the old zero-scratch 128KiB and all existing context/ring offsets. Counts 1..64 receive a separate table page and buffers after the original region, with the complete lease rounded to a power-of-two page count. The Intel34 case uses 128 pages/512KiB. Counts above64 fail before side effects. Controller, launcher and trusted authority use the same layout; the kernel independently re-reads hardware to determine the requested allocation and checks every alias/physical page. The new trusted contiguous_xhci entry retains the original pin-before-allocation/partial-failure state machine with a128-page limit; the old32-page API is unchanged.

The driver zeroes the entire lease and installs DCBAA[0] and each buffer address before the existing fence/enable/start sequence. The kernel independently checks the exact reachable pointer graph and zero table/buffers/rounded suffix before BME, and snapshots the entire lease using private kernel storage. Restore capability does not issue CSS/CRS or weaken the command gate. Firmware ownership/SMI/protocol/unknown-extension guards remain active; normal extension reads are bounded by the sized BAR, including an extension chain at8000. No hardware success is inferred from the earlier incomplete read-only screen.

## Executed validation at submission

- New actual-controller/authority/allocator native module:3 tests PASS in77.845s, zero skips; debug/release, normal O0/O2, ELF+COFF assembly, eight real bad-body variants fail through independent C assertions. Source hashes and native outputs retained under code/build/test/xhci-scratchpad/run-*/result.json. The34-page path and64-page boundary, table pointers, dirty buffers/tail, undersized/over-limit leases and 128-page partial allocation events are exercised.
- Actual trusted-kernel native grant/gate/quarantine tests and their bad-body controls have passed in the current root run, including new34/64-page positive cases and corrupt table/dirty tail/last-page-alias refusal before BME. The separate unmodified full-graph debug/release compilation is still running at this submission; formal verification is required to complete it.
- Existing controller and authority positive/negative native suites and transport positive/negative tests have passed in the ongoing broader root regression. Async/BOT/old allocator regression and a fresh full normal USB-only desktop build are in progress; no final result or OS success is claimed at this point.
- Early failures are preserved: an explicit u32/u64 comparison needed a cast, and the new C oracle initially collided with the included fixture's main renaming. Corrected the actual source type and the isolated test fixture; tests were rerun against the corrected frozen source. A superseded baseline run was interrupted before source repair; it is not counted as passing evidence.

## Completion gates

### First independent run and targeted harness repair

Formal job835cee8808874d40910ab7b2da47f3ba passed scratch3/controller2/authority2 and both kernel-native methods, with all18 inputs stable and zero skips. Its final unmodified graph assembly of user.device_host-debug.o hit the existing90-second subprocess timeout during concurrent8-CPU VM load. The job correctly returned failure/rework; this result is retained and is not counted as passed. Root's earlier complete kernel module had passed3 tests/352.587s, and the broader regression passed12 tests/378.278s. The task was reclaimed before changing only the unmodified-graph NASM budget to300 seconds. Native execution still has its90-second limit and every oracle/assertion is unchanged. No production source, ordinary build input, runtime observer or candidate artifact was changed by this repair.

The root eight-CPU normal single-USB live gate has now passed using the fresh candidate: actual HID/console, GUI surfaces, same-disk file create/write/append/remove/readback/sync, final immutable code/permission/CPU checks and three entire writable internal sentinels. Result is code/build/hardware/usb-s19-20261026-r1/scratch-20261027-vm1/result.json. Subsequent formal verification must use the repaired host-only timeout helper; the runtime VM evidence retains its original input fingerprints and is not represented as rerun evidence.

Submit for the four predeclared independent modules. Root must review actual sources, contracts and test effectiveness, confirm stable fingerprints and zero skips, finish the full normal build and actual VM observation, then accept/integrate. The final review note records those later results. User has confirmed the original SanDisk is reinserted as H:, but publication is gated on those results and actual identity/previous payload checks, backup, flush/readback and a native rb FAT32 volume check. Physical desktop/HID success remains pending the user's next boot.


## AI交付 2026-10-27T11:08:29+00:00 · codex-mcp-5c7de4d7c45b49d1

实际共享Scratchpad布局/512KiB独占DMA/驱动DCBAA与页表初始化/内核全部alias与快照/authority指针图及零尾部校验已落盘，零scratch旧布局ABI保持；old32页API不变，可信xHCI新入口128页。新增实际模块3tests77.845s通过0skip，debug/release×O0/O2及ELF/COFF，8类真实坏体被C独立断言拒绝。内核actual gate与坏体native通过，单独unmodified graph编译仍在root运行；旧controller/authority/transport正负native已通过，async/BOT/DMA回归和fresh完整USB-only build仍运行。未声明完整build/VM/硬件通过。交付报告逐项说明已执行/待完成，申请四个预声明模块独立复验；源码冻结，待formal与root完整构建VM后实际审查验收，用户已确认H但尚未写盘。


## AI交付 2026-10-27T11:17:57+00:00 · codex-mcp-5c7de4d7c45b49d1

保留首次正式失败835cee...：scratch3/controller2/authority2及kernel native2方法均通过，独立最后unmodified graph的NASM命中90s host timeout，并非功能断言失败，source_stable且零skip。已领取返修并只改tests.test_xhci_kernel的command可选timeout，默认/native执行仍90s，仅完整unmodified图NASM调用300s。无production/sourcebuild/runtime observer/candidate字节变化。Root完整kernel3tests352.587s及广回归12tests378.278s已通过；fresh完整normalUSB-only构建及实际8CPU单USB live gate全通过，3整内盘哨兵未变，GUI/HID/console及同盘create/write/append/rm/cat/sync完成。交付追加真实失败及时间预算修复记录。申请原四模块全部重跑独立复验，未提前验收或写H。

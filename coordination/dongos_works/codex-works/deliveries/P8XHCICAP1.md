# P8XHCICAP1 — first-page read-only xHCI diagnostic

The physical USB census found Intel 8086:A12F at ECAM E00A0000, with a 64-bit BAR starting at DF510000 and no UEFI descriptor covering its first page. Inventory flags 1103 do not prove a Reserved descriptor or a Runtime BAR failure. This delivery collects the missing controller capability and firmware-ownership evidence without changing normal boot or driver admission.

## Implementation and limits

The opt-in builder preserves the ordinary source tree, compile/link input provenance, all 17 service artifacts and normal defaults. Its private overlay adds a guarded, supervisor-only, uncached, read-only, NX 4 KiB mapping and a bounded reader; there are no PCI writes, BAR-sizing writes, ownership requests, controller resets or new DMA authority. The decoder exports a 256-byte report and stops at phase 24 before userspace. The 15-row screen ends at pixel 470, including FLAGS. MMIO access is denied before mapping if the actual existing mmio_range guard rejects Runtime, RAM, framebuffer or invalid ranges.

Only the first BAR page is read. Extended capabilities outside that page or beyond the bounded chain are explicitly incomplete. REJECT MASK records observed predicates in the current implementation; it is not an actual driver failure or proof that all normal admission checks pass. USBCMD/USBSTS are observations of firmware-configured state. The normal S14/S19 physical fault remains unproven pending this next hardware photograph.

## Executed validation

- Native tests: `python -m unittest tests.test_xhci_capability_probe -v`, 2 tests, 29.611 s, PASS, zero skips, 141 tracked source inputs stable. Evidence: `code/build/test/xhci-capability/run-c7d1f9716c6b/validation-summary.json`.
- The actual capability module runs in debug/release at O0/O2, with ABI offsets and adjacent BSS canaries. Eight bad decoder bodies per mode fail through the independent C assertions. The actual private reader and original mmio_range run against real native map/load boundaries; six bad bodies per mode fail. Total: 64 ELF/COFF assemblies and 36 native executions. Normal cases cover 56 decoder cases/2887 checks and 63 map cases/1617 checks per executable.
- Real diagnostic build and strict verification completed eight actual compile/link commands from the retained ordinary build. Candidate: `code/build/hardware/xhci-caps-20261026-r1/builder-preflight-r1/esp`. Manifest SHA256: `55f9567399c9b16beacf5ac30ba8dc4a1d5429a9cd4ff49e37f081c539b95c35`.
- Root ran the unchanged candidate with WHPX, eight CPUs, one USB medium and three writable internal-disk sentinels. `vm-r3/result.json` PASS, SHA256 `fae66cdc2f13c398c804bb11919e2ada1265630f49c86419e24b02ca41852610`. Actual phase 24, CPU count 8, READ ERROR 0, FLAGS DF, observed rejection mask 0, 17 successful MMIO reads. The actual 256-byte report, raw capability registers, bounded chain, full 15-row framebuffer (78792 pixels), actual page tables and CR0.WP were checked. The leaf is UC/RO/NX, effective user access is denied, and no HHDM alias exists. The guest was stopped and closed; the entire USB image and all three complete internal images were unchanged.
- Earlier root observer runs are retained: r1 incorrectly matched the legitimate CAPS_DONE marker as a userspace marker; r2 incorrectly disallowed USER on upper page-table entries even when the leaf denies it. Both observer checks were corrected; no guest source or candidate bytes changed. The final check evaluates effective four-level permissions.

## Delivery status

All six declared files are present in the real workspace. Independent coordinator verification and acceptance are required before publication. H: publication will back up the previous verified four files, preserve the SanDisk identity and partition, flush and read back each replacement, and run the native FAT32 volume probe in rb mode. Hardware success and desktop/keyboard/mouse operation are not claimed by this intentional diagnostic stop.


## AI交付 2026-10-26T15:19:18+00:00 · codex-mcp-918a30d10dd649bf

已落盘六个声明文件，交付见 codex-works/deliveries/P8XHCICAP1.md。真实 native 2 tests/29.611s/零skip/141源稳定；debug/release×O0/O2，8类decoder和6类实际guard/map坏体有效失败；实际八命令构建和严格manifest核验通过。Root WHPX 8 CPU单USB/三可写内盘哨兵 vm-r3通过，报告256B/实寄存器/15行78792像素/UC RO NX有效权限/CR0.WP/无HHDM alias/无userspace及新增硬件authority；所有磁盘整盘hash不变。VM结果SHA fae66cdc2f13c398c804bb11919e2ada1265630f49c86419e24b02ca41852610。前两轮仅observer误判修正，客体和候选未变。真实硬件故障仍待能力/固件占用字段，只读首4K及显式不完整，不宣称修复/桌面通过。请求独立复验。

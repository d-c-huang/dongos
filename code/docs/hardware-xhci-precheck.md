# xHCI precheck evidence

The Intel BOOT LIVE R2 photograph reports `08110002`, phase 0, held 0. In the
actual controller these values identify an Unsupported return before admitting
the controller state. They do not distinguish the many capability predicates.
The earlier Intel base-register photograph is compatible with the implemented
34-scratchpad layout. Its `XECP FIRST=8000` was an offset, not a captured header:
that old first-page probe explicitly did not read the extended chain there.

This change retains the original predicates, error codes, MMIO read order,
no-write-before-precheck contract, and Setup/Caps/State ABI. A separate 40-byte
PrecheckReport records the actual rejection sample. The service emits four
short records before its existing error/phase/held records. All seven fit the
existing BOOT LIVE sticky window. Logging uses the saved sample and never
re-reads MMIO. Success and each new precheck clear the previous diagnostic.
The new EFI banner is BOOT LIVE R3, managed by P8BOOTCONSOLE1.

| CHECK (hex) | Test | REG / VALUE / AUX |
| --- | --- | --- |
| 03 | CAPLENGTH/version | 0 / CAP0 / 0 |
| 04 | slots, interrupters, ports, scratch count | 4 / HCSPARAMS1 / HCSPARAMS2 |
| 05 | scratch allocation size | 8 / HCSPARAMS2 / actual lease bytes |
| 06 | 32-bit DMA restriction | 10 / DMA physical base / lease bytes |
| 08 | 4 KiB page support | operational+8 / PAGESIZE / 0 |
| 09 | extended-chain limit | next offset / 64 / 0 |
| 0A | BIOS/OS ownership bits | capability offset / header / 0 |
| 0B | legacy control nonzero | capability+4 / control / header |
| 0C | Supported Protocol name | capability+4 / name / header |
| 0D | Supported Protocol range/major/PSI/slot | capability+8 / range / slot in high 32 bits, header in low 32 bits |
| 10 | unsupported capability ID | capability offset / header / 0 |
| 80 | callback read failure | attempted offset / callback status / 0 |

CHECK 0 means no annotated rejection. Invalid setup/range/overlap failures keep
their original errors and do not invent a raw value. The read-error record is
explicitly a callback status, not a successfully read register value. This is
diagnostic evidence, not implementation of BIOS handoff or additional protocol
support. Unknown capabilities and uncleared firmware ownership remain rejected.

Tests execute actual precheck and the actual service formatter in debug/release,
with independent C layouts, exact read counts, unchanged DMA/input/output checks,
42 cases per execution, post-decision MMIO changes, and wrong-body controls.
Synthetic extended records at offset 8000 are labeled models, not hardware
captures. Old controller and scratchpad tests retain functional validation.

The relevant capability and legacy ownership definitions are in Intel's
[xHCI specification, chapter 7](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/extensible-host-controler-interface-usb-xhci.pdf).
No ownership transition is inferred from the screenshot alone.

## PSI compatibility follow-up (P8PSI1 / P8PSIGATE1)

Hardware R3 captured CHECK=0D, REG=8008, VALUE=30111001,
AUX=02000802: USB2 ports 1..16 with three explicit speed entries.
The entry values themselves have not yet been captured on that machine.

The driver now reads bounded PSI entries and admits only complete standard
USB2 IDs 1/2/3 at 12/1.5/480 Mbit/s, or USB3 ID 4 at 5 Gbit/s.
Symmetric link type and matching half/full duplex are required. Equivalent
exponent/mantissa representations are accepted. Incomplete sets, duplicate IDs,
other IDs/rates/link protocols, malformed fields, overlapping next capabilities,
and out-of-BAR spans remain rejected. This is deliberately not arbitrary speed
ID remapping. PSIC=0 retains the original default mapping behavior.

The kernel independently rereads and validates every entry before BME. The
48-byte trusted Extension snapshot retains raw range/PSIC; for protocol entries
only, legacy_control carries the validated speed mask (14 or 16). For legacy
entries it retains its original meaning. The authority validator checks count,
mask, and the full 16+4*PSIC byte span; no ABI or snapshot allocation grows.
No user-provided mask is trusted. CHECK=11 (hex) reports an unsupported PSI word
with REG=its offset, VALUE=the actual word, AUX=protocol header.

This repairs the confirmed blanket rejection; compatibility with the actual
unread PSI words and complete hardware startup still require a physical test.

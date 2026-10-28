# BOOT LIVE R3

P8BOOTCONSOLE1 adds an explicit `user-startup-console` diagnostic profile. The
Intel machine still retained the old S19/error0 screen after USER RUNTIME R2;
that screen alone does not establish a domain-lock failure. This profile makes
subsequent execution visible and does not claim to fix the unknown hardware cause.

Build a fresh ordinary level7 USB-only source with `tools.build.build`, then run
`python -m tools.build_startup_console --normal-source <source> --normal-build-log <log> --output <candidate>`.
The EFI banner is `DongOS BOOT LIVE R3`; `startup-console.json` binds the original
source, exact commands, private patches, full compiler ABI, service bundle and
all output hashes. It cannot be substituted for an ordinary build manifest.

The private kernel displays the first two BSP returns/captures and each accepted
log update. POINT is 1 before user return, 2 after log acceptance, 3 after user
capture, or 4 at compositor handoff. SLOT identifies the selected/captured
process; SYSCALLS, EVENT, OPERATION and USER RIP are observed values, not errors.
POINT alone is not a diagnosis. The lower eight rows show the recent 4096-byte
RAM log, uppercased, wrapped at 40 characters. Empty lines/CR are omitted; a
clipped ring prefix is discarded through its first LF. Unsupported characters
become `?`. Separators `_`, `=`, `:` and `?` have private diagnostic glyphs.

Rendering uses the existing geometry checks and framebuffer Gate, on trusted
BSP/kernel CR3 with IF clear and kernel xstate restored. Capture rendering runs
before the original deadline calculation. The console adds execution time and
can affect timing-sensitive faults. It permanently stops before cfg3's first
compositor IRET, retaining ordinary view retirement, AP idle, service policy,
deadlines, and the earlier fatal-only runtime screen. An assembly flag then
returns before GS/root checks or the Dong producer, avoiding its stack and
argument work on subsequent hot paths. No successful checkpoint
halts, device grants, DMA or internal-disk policy changes are introduced.

Native tests execute the actual Dong producer in debug/release and actual ASM
wrappers with explicit models for privileged observations. They check layout,
input/output canaries, bounded wrapping, capture selection, one-way handoff,
return-value preservation, and deliberately wrong bodies. Root-only QEMU
validation must additionally retain the existing eight-CPU desktop, USB HID,
file persistence and internal-disk sentinel checks, and exercise visible logs
when an actual virtual USB device is removed after firmware loading. Native
tests do not establish real hardware success. Publication requires independent
zero-skip verification, exact candidate identity and USB file readback.

On hardware, leave wired keyboard/mouse directly attached. If startup does not
reach the desktop, photograph the complete BOOT LIVE screen, including all log
rows. If a fatal screen appears, photograph it instead. A desktop pass still
requires actual mouse, keyboard and file checks by the hardware operator.


R2 follows the real Intel photograph with cfg2/block 05060001 and cfg4/input
07310001. These are generic downstream failures; the photo does not establish
the controller's underlying error. R1's last-eight-rows screen lost that evidence.
R2 keeps two independent eight-row windows: FIRST USB ISSUE captures the first
complete nonzero USB error (or device-limit marker) and its contiguous detail
records; LATEST OR TERMINAL USB LOG continues normally until the first terminal
xhci/hid/proxy error, then retains its contiguous phase/held records. Later init
failures and circular-buffer rollover cannot overwrite either snapshot. The
first issue may be a recoverable rejected device and is not declared the root
cause. Both windows contain original log text, not inferred diagnoses. The
normal screen remains when no recognized issue has occurred. At 18-pixel pitch
both windows fit the existing 640x480 minimum geometry. The report ABI is 792
bytes; its original first 456 bytes retain their offsets. No driver, retry,
readiness or DMA behavior is changed. Handoff still permanently disables all
startup drawing before the first compositor entry.

Tests exercise fragmented/batched records, exact nonzero error recognition,
clipped prefixes, first issue versus later terminal failure, more than 4096
bytes of subsequent init logs, read-only canaries, and closure before compositor.
Two additional wrong-body cases verify that losing either sticky window fails.
The previous complete-desktop VM failures remain unresolved; this is an
experimental evidence collector, not an accepted desktop repair.

R3 changes the explicit EFI banner for the xHCI precheck diagnostic service.
The sticky producer and renderer are unchanged from R2. See hardware-xhci-precheck.md
for CHECK/REG/VALUE/AUX; these four records plus the existing error/phase/held
fit one eight-row window. This is not a claim of physical startup repair.

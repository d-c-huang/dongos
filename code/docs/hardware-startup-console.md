# BOOT LIVE R1

P8BOOTCONSOLE1 adds an explicit `user-startup-console` diagnostic profile. The
Intel machine still retained the old S19/error0 screen after USER RUNTIME R2;
that screen alone does not establish a domain-lock failure. This profile makes
subsequent execution visible and does not claim to fix the unknown hardware cause.

Build a fresh ordinary level7 USB-only source with `tools.build.build`, then run
`python -m tools.build_startup_console --normal-source <source> --normal-build-log <log> --output <candidate>`.
The EFI banner is `DongOS BOOT LIVE R1`; `startup-console.json` binds the original
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

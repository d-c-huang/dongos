; Only privileged observation operands are modeled by the native harness.
; Tick and log wrapper bodies are extracted from the actual builder output.
bits 64
default rel
section .text
global startup_console_tick,services_write_bytes
extern dong_startup_console_run,boot_progress_draw,startup_console_write_bytes
extern dong_startup_console_pointer
extern test_cpu,test_root,test_kernel_root,test_flags
extern services_console_head,services_console_accepted,services_console_ring
extern runtime_failure_view,boot_progress_view,boot_progress_phase

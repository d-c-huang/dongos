; BSP-only runtime7 diagnostics. Every macro preserves all registers/flags.
; Defining HW_BOOT_PROGRESS_OWNER makes entry.asm the sole symbol owner.
%ifndef DONGOS_BOOT_PROGRESS_INC
%define DONGOS_BOOT_PROGRESS_INC
%ifndef RUNTIME_LEVEL
%define RUNTIME_LEVEL 0
%endif
%if RUNTIME_LEVEL >= 7
; ABI cross-checked against boot.device_policy.Conflict's compiler manifest.
struc BootProgressMmio
    .version: resq 1
    .valid: resq 1
    .error: resq 1
    .slot: resq 1
    .address: resq 1
    .page: resq 1
    .descriptor_index: resq 1
    .kind: resq 1
    .base: resq 1
    .pages: resq 1
    .attributes: resq 1
endstruc
%ifdef HW_BOOT_PROGRESS_OWNER
global boot_progress_draw, boot_progress_record_error
global boot_progress_phase, boot_progress_failed, boot_progress_error
global boot_progress_view, boot_progress_cpus
global boot_progress_mmio
%else
extern boot_progress_draw, boot_progress_record_error
extern boot_progress_phase, boot_progress_failed, boot_progress_error
extern boot_progress_view, boot_progress_cpus
extern boot_progress_mmio
%endif
%endif

%macro HW_BOOT_STAGE 1
%if RUNTIME_LEVEL >= 7
    mov byte [rel boot_progress_phase],%1
    call boot_progress_draw
%endif
%endmacro

%macro HW_BOOT_ERROR 0
%if RUNTIME_LEVEL >= 7
    call boot_progress_record_error
%endif
%endmacro

%macro HW_BOOT_DISABLE 0
%if RUNTIME_LEVEL >= 7
    mov qword [rel boot_progress_view],0
%endif
%endmacro
%endif

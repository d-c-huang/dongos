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
; ABI cross-checked against user.devices.ConfigurationConflict (16 qwords).
; A fixed compiler-owned BSS object, never an address supplied in a field.
struc BootPciConflict
    .version: resq 1
    .valid: resq 1
    .reason: resq 1
    .error: resq 1
    .physical: resq 1
    .bytes: resq 1
    .ecam: resq 1
    .descriptor_index: resq 1
    .kind: resq 1
    .base: resq 1
    .pages: resq 1
    .attributes: resq 1
    .mcfg_first: resq 1
    .mcfg_end: resq 1
    .framebuffer_base: resq 1
    .framebuffer_bytes: resq 1
endstruc
%define BOOT_PCI_CONFLICT_GETTER dong_configuration_conflict
%ifdef HW_BOOT_PROGRESS_OWNER
extern BOOT_PCI_CONFLICT_GETTER
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

; Timed AP handoff may advance the observation without drawing a framebuffer.
; MOV preserves every GPR, flags and XMM, including a live return value.
%macro HW_BOOT_MARK 1
%if RUNTIME_LEVEL >= 7
    mov byte [rel boot_progress_phase],%1
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

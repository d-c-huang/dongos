; Bounded, best-effort boot diagnostics. Microsoft x64 ABI, no allocations.
; Seal before the final GetMemoryMap/ExitBootServices sequence, including all
; retries: a failed EBS may already have partially shut firmware services down.
bits 64
default rel
%include "uefi.inc"

section .text
global loader_console_initialize, loader_console_write, loader_console_seal

; RCX = trusted EFI_SYSTEM_TABLE*, or null. Initialization is entry-only.
loader_console_initialize:
        mov     [rel loader_console_table], rcx
        ret

; No firmware access, even if a subsequent message pointer is invalid.
loader_console_seal:
        mov     qword [rel loader_console_table], 0
        ret

; RCX = NUL ASCII message. At most 127 bytes become UTF-16 plus a terminator.
; Missing console/method, empty input and OutputString errors are nonfatal.
; Preserve every MS x64 nonvolatile GPR/XMM register. At the firmware CALL,
; RSP is 16-byte aligned and [RSP, RSP+32) is exclusively shadow space.
loader_console_write:
        push    rbx
        sub     rsp, 288                ; 32 shadow + 128 UTF-16 code units
        mov     rbx, rcx
        mov     rax, [rel loader_console_table]
        test    rax, rax
        jz      .done
        mov     rcx, [rax + EFI_SYSTEM_TABLE.ConOut]
        test    rcx, rcx
        jz      .done
        mov     rax, [rcx + EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL.OutputString]
        test    rax, rax
        jz      .done
        test    rbx, rbx
        jz      .done
        lea     rdx, [rsp + 32]
        xor     r8d, r8d
.convert:
        cmp     r8d, 127
        jae     .terminate
        movzx   r9d, byte [rbx + r8]
        test    r9b, r9b
        jz      .terminate
        mov     [rdx + r8 * 2], r9w
        inc     r8d
        jmp     .convert
.terminate:
        mov     word [rdx + r8 * 2], 0
        test    r8d, r8d
        jz      .done
        call    rax
.done:
        add     rsp, 288
        pop     rbx
        ret

section .data
align 8
loader_console_table: dq 0

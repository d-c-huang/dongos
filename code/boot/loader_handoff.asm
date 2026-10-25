; A self-contained low transition supports EFI images loaded above 4 GiB.
; Public helpers use Microsoft x64 ABI; the transition never calls firmware.
bits 64
default rel
%include "bootinfo.inc"

section .text
global loader_image_range, loader_handoff_prepare
global loader_handoff_template, loader_handoff_end, loader_handoff_target

; RCX ImageBase, RDX ImageSize, R8 actual entry. EAX=1 valid / 0 invalid.
; Validate containment and overflow, without assuming a low firmware load.
loader_image_range:
        xor     eax, eax
        test    rcx, rcx
        jz      .done
        test    rdx, rdx
        jz      .done
        mov     r9, rcx
        add     r9, rdx
        jc      .done
        cmp     r8, rcx
        jb      .done
        cmp     r8, r9
        jae     .done
        mov     eax, 1
.done:
        ret

; RCX low page, RDX capacity, R8 kernel entry. EAX=0 success / 1 invalid.
; Reject all invalid input before writing. Only blob bytes and target change.
loader_handoff_prepare:
        mov     eax, 1
        test    rcx, rcx
        jz      .done
        test    rcx, 4095
        jnz     .done
        cmp     rdx, 4096
        jb      .done
        mov     r9, rcx
        add     r9, 4095
        jc      .done
        shr     r9, 32
        jnz     .done
        mov     r9, 0xffffffff80000000
        cmp     r8, r9
        jb      .done
        add     r9, 0x200000
        cmp     r8, r9
        jae     .done
        push    rsi
        push    rdi
        mov     r10, rcx
        mov     rdi, rcx
        lea     rsi, [rel loader_handoff_template]
        mov     ecx, loader_handoff_end - loader_handoff_template
        cld
        rep     movsb
        mov     [r10 + loader_handoff_target - loader_handoff_template], r8
        pop     rdi
        pop     rsi
        xor     eax, eax
.done:
        ret

; Enter by JMP while firmware mappings still exist. Preserve R13=BootInfo,
; RSI=service handoff, RDX=trace page, RCX=trace magic (absent values are zero).
; Every RIP-relative reference stays inside this copied blob.
align 16
loader_handoff_template:
        endbr64
        cli
        cld
        mov     rsp, [r13 + BootInfo.stack_physical]
        add     rsp, [r13 + BootInfo.stack_size]
        lea     rax, [rel .gdt]
        mov     [rel .gdtr + 2], rax
        lgdt    [rel .gdtr]
        lidt    [rel .idtr]
        mov     ax, 0x10
        mov     ds, ax
        mov     es, ax
        mov     ss, ax
        xor     eax, eax
        mov     fs, ax
        mov     gs, ax
        mov     rax, cr4
        and     rax, ~0x80               ; Flush inherited global translations.
        mov     cr4, rax
        mov     rax, [r13 + BootInfo.pml4_physical]
        mov     cr3, rax
        push    qword 0x08
        lea     rax, [rel .own_cs]
        push    rax
        retfq
.own_cs:
        xor     ebp, ebp
        mov     rdi, r13
        lea     rax, [rel .returned]
        push    rax                      ; SysV kernel entry RSP%16=8.
        mov     rax, [rel loader_handoff_target]
        jmp     rax
.returned:
        ; Reachable only during initial mappings; later roots remove identity.
        cli
        lea     rsi, [rel .return_error]
.return_next:
        mov     r9b, [rsi]
        test    r9b, r9b
        jz      .return_drain
        mov     ecx, 0x100000
        mov     dx, 0x3fd
.return_wait:
        in      al, dx
        test    al, 0x20
        jnz     .return_send
        pause
        dec     ecx
        jnz     .return_wait
        jmp     .halt
.return_send:
        mov     dx, 0x3f8
        mov     al, r9b
        out     dx, al
        inc     rsi
        jmp     .return_next
.return_drain:
        mov     ecx, 0x100000
        mov     dx, 0x3fd
.return_empty:
        in      al, dx
        test    al, 0x40
        jnz     .halt
        pause
        dec     ecx
        jnz     .return_empty
.halt:
        hlt
        jmp     .halt
.return_error: db "DONGOS_P1_FAIL:E14_KERNEL_RETURNED",13,10,0
align 8
.gdt:   dq 0, 0x00af9b000000ffff, 0x00cf93000000ffff
.gdtr:  dw 3 * 8 - 1
        dq 0                            ; Computed from the actual low copy.
.idtr:  dw 0
        dq 0
loader_handoff_target: dq 0
loader_handoff_end:
%if loader_handoff_end - loader_handoff_template > 4096
%error Low handoff must fit one complete owned page
%endif

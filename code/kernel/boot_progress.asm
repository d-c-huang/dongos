; Included by entry.asm only for runtime7. No additional framebuffer writer:
; the existing screen_draw owns geometry checks and the outer cache Gate.
; A nonzero view is published only after the first successful screen_draw.
; All call-site arguments, return values, flags (including DF) and XMM survive.
; One named function in the owning entry TU avoids cross-object %% labels.
boot_progress_record_error:
    pushfq
    cmp byte [rel boot_progress_failed],0
    jne .recorded
    mov [rel boot_progress_error],rax
    mov byte [rel boot_progress_failed],1
.recorded:
    popfq
    jmp boot_progress_draw

boot_progress_draw:
    pushfq
    push rax
    push rcx
    push rdx
    push rbx
    push rbp
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    push r14
    push r15
    mov rbp,rsp
    and rsp,-16
    cld
    mov r12,[rel boot_progress_view]
    test r12,r12
    jz .restore
    call screen_draw
.restore:
    mov rsp,rbp
    pop r15
    pop r14
    pop r13
    pop r12
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rbp
    pop rbx
    pop rdx
    pop rcx
    pop rax
    popfq
    ret

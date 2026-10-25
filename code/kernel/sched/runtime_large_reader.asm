bits 64
default rel
%include "user_smp.inc"
global runtime_large_environment,runtime_large_load,runtime_large_window,runtime_large_digest
global runtime_large_test_omit,runtime_large_window_active
global runtime_large_test_omit_end,runtime_large_test_record,runtime_large_test_record_end
global runtime_large_test_publish,runtime_large_test_publish_end,runtime_large_test_receipt
section .data
align 8
runtime_large_window_active: dq 0
align 64
runtime_large_test_receipt: times 16 dq 0
section .text
; These readers neither switch CR3 nor invalidate any translation. A warm AP
; stays on its already captured kernel root while CPU0 holds the global BKL.
runtime_large_environment:
    mov rax,[gs:UserSmpCpu.logical_id]
    mov [rdi],rax
    pushfq
    pop rax
    shr rax,9
    and eax,1
    xor eax,1
    mov [rdi+8],rax
    mov rax,cr3
    mov [rdi+16],rax
    mov rax,cr4
    mov [rdi+24],rax
    ret
runtime_large_load:
    mov rax,[gs:UserSmpCpu.logical_id]
    mov [rsi],rax
    mov rax,cr3
    mov [rsi+8],rax
    mov rax,cr4
    mov [rsi+16],rax
    lfence
    mov rax,[rdi]                   ; actual volatile alias load
    lfence
    mov [rsi+24],rax
    ret
runtime_large_window:
    mov [rel runtime_large_window_active],rdi
    ret
runtime_large_digest:
    ; Full old-window byte coverage only before/after the lifecycle, in this
    ; compact real reader loop. No writes, allocation, flush or CR3 switch.
    mov rax,0x4c41524745313601
    xor ecx,ecx
.word:
    xor rax,[rdi+rcx]
    rol rax,7
    add rcx,8
    cmp rcx,rsi
    jb .word
    ret
runtime_large_test_omit:
    ; Private guest bad build replaces only this literal. The unchanged
    ; production user_arch never calls this function.
    xor eax,eax
    ret
runtime_large_test_omit_end:
runtime_large_test_record:
    ; Private overlays alone replace this dormant recorder.
    xor eax,eax
    ret
runtime_large_test_record_end:
runtime_large_test_publish:
    ; rdi points to 16 actual samples. Native tests exercise this exact safe
    ; publisher, never the privileged sampling or a guest TLB instruction.
    lea rdx,[rel runtime_large_test_receipt]
    cmp qword [rdx+8],0
    jne .repeat
    mov qword [rdx+8],1
    mov rax,[rdi]
    mov [rdx],rax
    lea rsi,[rdi+16]
    lea rdi,[rdx+16]
    mov ecx,14
    cld
    rep movsq
    mfence
    mov qword [rdx+8],2
    xor eax,eax
    ret
.repeat:
    ; Preserve the first payload; repeated/partial publication is never one hit.
    mov qword [rdx+8],3
    xor eax,eax
    ret
runtime_large_test_publish_end:
%ifidn __OUTPUT_FORMAT__,elf64
section .note.GNU-stack noalloc noexec nowrite progbits
%endif

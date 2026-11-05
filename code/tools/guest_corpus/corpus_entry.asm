bits 64
default rel
global corpus_call,corpus_emit,__dong_panic
extern corpus_main
section .text
; Same SysV(number,A,B,C,D,E,F) -> SYSCALL register path as svc_call.
corpus_call:
    mov rax,rdi
    mov rdi,rsi
    mov rsi,rdx
    mov rdx,rcx
    mov r10,r8
    mov r8,r9
    mov r9,[rsp+8]
%ifdef CORPUS_HOST
    ; Test substitutes ONLY the privilege boundary. Save all seven raw inputs
    ; before adapting to the C oracle, preserving syscall RCX/R11 clobbers.
    sub rsp,72
    mov [rsp],rax
    mov [rsp+8],rdi
    mov [rsp+16],rsi
    mov [rsp+24],rdx
    mov [rsp+32],r10
    mov [rsp+40],r8
    mov [rsp+48],r9
    mov rdi,rsp
    extern corpus_host_boundary
    call corpus_host_boundary
    add rsp,72
%else
    syscall
%endif
    ret
corpus_emit:
%ifdef CORPUS_HOST
    extern corpus_host_emit
    jmp corpus_host_emit
%else
    mov eax,0x70
    syscall
    ret
%endif
__dong_panic:
    ud2
%ifndef CORPUS_HOST
global _start
_start:
    and rsp,-16
    call corpus_main
    mov rdi,rax
    mov eax,0xff
    syscall
    ud2
%endif

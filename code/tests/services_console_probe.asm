bits 64
default rel
extern console_in,console_out,console_clock
global console_test_in,console_test_out,console_test_clock
section .text
%macro SAVE 0
    pushfq
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
%endmacro
%macro RESTORE 0
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
    popfq
    ret
%endmacro
console_test_in:
    SAVE
    movzx edi,dx
    mov r11,rsp
    and rsp,-16
    sub rsp,16
    mov [rsp],r11
    call console_in
    mov rsp,[rsp]
    mov [rsp+64],al
    RESTORE
console_test_out:
    SAVE
    movzx edi,dx
    movzx esi,al
    mov r11,rsp
    and rsp,-16
    sub rsp,16
    mov [rsp],r11
    call console_out
    mov rsp,[rsp]
    RESTORE
console_test_clock:
    SAVE
    mov r11,rsp
    and rsp,-16
    sub rsp,16
    mov [rsp],r11
    call console_clock
    mov rsp,[rsp]
    mov edx,eax
    mov [rsp+64],rdx
    shr rax,32
    mov [rsp+48],rax
    RESTORE

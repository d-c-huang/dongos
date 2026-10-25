; Win64 EFI desktop mode selection. Rank the existing desktop contract by area,
; release every QueryMode pool, then verify the actual mode after each SetMode.
; The 256 scores belong to this call; no firmware-owned pointer is retained.
bits 64
default rel
%include "uefi.inc"
global desktop_graphics_mode
section .text
desktop_graphics_mode:
    push rbp
    mov rbp,rsp
    push rbx
    push r12
    push r13
    push r14
    push r15
    push rsi
    push rdi
    ; 32-byte shadow, two QueryMode outputs, 256 qword scores, alignment.
    sub rsp,2104
    mov rbx,rcx
    mov r12,rdx
    test rbx,rbx
    jz .bad
    test r12,r12
    jz .bad
    cmp qword [rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.QueryMode],0
    je .bad
    cmp qword [rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.SetMode],0
    je .bad
    cmp qword [r12+EFI_BOOT_SERVICES.FreePool],0
    je .bad
    mov rax,[rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.Mode]
    test rax,rax
    jz .bad
    mov r13d,[rax+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.MaxMode]
    test r13d,r13d
    jz .bad
    cmp r13d,256
    ja .bad
    cmp [rax+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.Mode],r13d
    jae .bad
    lea rdi,[rsp+48]
    xor eax,eax
    mov ecx,256
    rep stosq
    lea rdi,[rsp+48]
    xor r14d,r14d
.query:
    mov qword [rsp+32],0
    mov qword [rsp+40],0
    mov rcx,rbx
    mov edx,r14d
    lea r8,[rsp+32]
    lea r9,[rsp+40]
    call [rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.QueryMode]
    test rax,rax
    jnz .free
    cmp qword [rsp+32],EFI_GRAPHICS_OUTPUT_MODE_INFORMATION_size
    jb .free
    mov rax,[rsp+40]
    call .geometry
    mov [rdi+r14*8],rax
.free:
    ; Even a failed QueryMode may return a pool that remains ours to free.
    mov rcx,[rsp+40]
    test rcx,rcx
    jz .advance
    call [r12+EFI_BOOT_SERVICES.FreePool]
    test rax,rax
    jnz .bad
.advance:
    inc r14d
    cmp r14d,r13d
    jb .query
.rank:
    xor esi,esi
    xor r14d,r14d
    xor r15d,r15d
.score:
    cmp [rdi+r14*8],rsi
    jbe .next_score
    mov rsi,[rdi+r14*8]
    mov r15d,r14d
.next_score:
    inc r14d
    cmp r14d,r13d
    jb .score
    test rsi,rsi
    jz .current_fallback
    ; Consume the candidate before calling firmware, so failures stay bounded.
    mov qword [rdi+r15*8],0
    mov rcx,rbx
    mov edx,r15d
    call [rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.SetMode]
    test rax,rax
    jnz .rank
    mov rax,[rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.Mode]
    test rax,rax
    jz .rank
    cmp [rax+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.Mode],r15d
    jne .rank
    call .valid_current
    test eax,eax
    jz .rank
    jmp .success
.current_fallback:
    ; A firmware current mode can remain usable when queries/sets all fail.
    call .valid_current
    test eax,eax
    jz .bad
.success:
    xor eax,eax
    jmp .return
.bad:
    mov eax,1
.return:
    add rsp,2104
    pop rdi
    pop rsi
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

; Input RAX info pointer. Output EAX pixel area, R10 required bytes; zero bad.
; Width/height bounds make both products nonoverflowing. No NV register touched.
.geometry:
    test rax,rax
    jz .invalid
    cmp dword [rax+EFI_GRAPHICS_OUTPUT_MODE_INFORMATION.Version],0
    jne .invalid
    mov ecx,[rax+EFI_GRAPHICS_OUTPUT_MODE_INFORMATION.HorizontalResolution]
    cmp ecx,800
    jb .invalid
    cmp ecx,1920
    ja .invalid
    mov edx,[rax+EFI_GRAPHICS_OUTPUT_MODE_INFORMATION.VerticalResolution]
    cmp edx,600
    jb .invalid
    cmp edx,1080
    ja .invalid
    cmp dword [rax+EFI_GRAPHICS_OUTPUT_MODE_INFORMATION.PixelFormat],1
    ja .invalid
    mov r8d,[rax+EFI_GRAPHICS_OUTPUT_MODE_INFORMATION.PixelsPerScanLine]
    cmp r8d,ecx
    jb .invalid
    cmp r8d,2048
    ja .invalid
    mov r10,r8
    imul r10,rdx
    shl r10,2
    mov eax,ecx
    imul eax,edx
    ret

; Validate actual GOP ownership/geometry plus the existing boot/cache contract.
; Full firmware size is checked, never truncated to visible rows or low bits.
.valid_current:
    mov r11,[rbx+EFI_GRAPHICS_OUTPUT_PROTOCOL.Mode]
    test r11,r11
    jz .invalid
    mov ecx,[r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.MaxMode]
    test ecx,ecx
    jz .invalid
    cmp ecx,256
    ja .invalid
    cmp [r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.Mode],ecx
    jae .invalid
    cmp qword [r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.SizeOfInfo],EFI_GRAPHICS_OUTPUT_MODE_INFORMATION_size
    jb .invalid
    mov rax,[r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.Info]
    call .geometry
    test eax,eax
    jz .invalid
    mov r8,[r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.FrameBufferBase]
    cmp r8,0x100000
    jb .invalid
    mov r9,[r11+EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE.FrameBufferSize]
    cmp r9,r10
    jb .invalid
    cmp r9,0x1000000
    ja .invalid
    mov rax,r8
    add rax,r9
    jc .invalid
    dec rax
    shr rax,32
    jnz .invalid
    ; Runtime cache ownership covers at most 4096 pages including edge pages.
    mov rax,r8
    and eax,4095
    add rax,r9
    add rax,4095
    shr rax,12
    cmp rax,4096
    ja .invalid
    mov eax,1
    ret
.invalid:
    xor eax,eax
    ret

"""Build explicit continuous startup console; no successful checkpoint stop.

Only private build copies are changed. BSP return/capture and accepted logs
update a bounded screen through the existing framebuffer Gate until the first
compositor return permanently disables it. This diagnostic adds rendering time;
normal AP idle, view retirement and desktop execution remain enabled. The prior
failure-only screen remains. No normal artifact, CPU topology, service bundle
or device authority is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'tools/build.py').is_file())
sys.path.insert(0, str(ROOT))
from tools.build import ROOT
from tools import build_bsp_diagnostic as prior
from tools.elf_image import materialize
from tools.mkimage import manifest_text, pack_image, unpack_image

VERSION = 1
PROFILE = 'user-startup-console'
STAGE = 24
REPORT_SIZE = 256
FIELDS = ('version', 'done', 'error_code', 'cpu', 'cpus', 'failure_cpu', 'failure_code', 'failure_detail', 'entry', 'event', 'stage', 'domain_failed', 'bridge_failed', 'lock', 'owner', 'online', 'mode', 'slot', 'token', 'captured', 'syscalls', 'user_entries', 'header_error', 'operation', 'rip', 'rsp', 'frame_root', 'raw_root', 'pcid', 'calls', 'failure_mask', 'frame_kind')
ROWS = (('CHECK ERROR', 'error_code'), ('ERROR CPU', 'failure_cpu'), ('ERROR CODE', 'failure_code'), ('DETAIL', 'failure_detail'), ('ENTRY', 'entry'), ('LAST EVENT', 'event'), ('BRIDGE STAGE', 'stage'), ('CPU MODE', 'mode'), ('SLOT', 'slot'), ('OPERATION', 'operation'), ('USER RIP', 'rip'), ('SYSCALLS', 'syscalls'), ('USER ENTRIES', 'user_entries'), ('DOMAIN FAIL', 'domain_failed'), ('BRIDGE CALLS', 'calls'))
TITLE = 'DONGOS RUNTIME FAILED'
BANNER = b'DongOS BOOT LIVE R1'
COMPLETION_MARKER = 'DONGOS_USER_RUNTIME_FAILURE'
MODULE = 'boot.user_runtime_status'
MODULE_PATH = 'boot/user_runtime_status.dg'
RUN_EXPORT = 'dong_user_runtime_status_run'
POINTER_EXPORT = 'dong_user_runtime_status_pointer'
REPLACED_OBJECTS = ('entry.o', 'dong_probe.o', 'user_entry.o', 'user_boot.o', 'services_run.o')
COMMAND_ORDER = ('compile', 'dong_probe', 'entry', 'user_entry', 'user_boot', 'services_run', 'kernel',
                 'image', 'efi_main', 'loader')
check, sha = prior.check, prior.sha


def _replace(text, before, after):
    newline = '\r\n' if '\r\n' in text else '\n'
    before, after = before.replace('\n', newline), after.replace('\n', newline)
    check(text.count(before) == 1, 'unique private patch location required: '+before[:70])
    return text.replace(before, after)


def patch_user_boot_asm(text):
    text = _replace(text, 'extern user_smp_activate,user_smp_idle,user_smp_fail\n',
        'extern user_smp_activate,user_smp_idle,user_smp_fail\nextern runtime_failure_view\n')
    # Save only the immutable view pointer. Original retirement still executes
    # at the original point, preserving every register, flag and stack depth.
    return _replace(text, 'user_boot_retire:\n    HW_BOOT_DISABLE\n    ret',
        'user_boot_retire:\n%if RUNTIME_LEVEL >= 7\n'
        '    push rax\n'
        '    mov rax,[rel boot_progress_view]\n'
        '    mov [rel runtime_failure_view],rax\n'
        '    pop rax\n%endif\n'
        '    HW_BOOT_DISABLE\n    ret')


def runtime_patch_user_entry_asm(text):
    text = _replace(text, 'extern sched_xstate_save,sched_xstate_restore\n',
        'extern sched_xstate_save,sched_xstate_restore\nextern user_runtime_failure_stop\n')
    # Only the original trusted-GS failure boundary may recover a screen. AP
    # failures and untrusted GS continue into the original halt unchanged.
    return _replace(text,
        '    mov qword [rax+1024+UserEntryMetrics.failed],1\nuser_smp_fail_untrusted:',
        '    mov qword [rax+1024+UserEntryMetrics.failed],1\n'
        '    cmp qword [gs:UserSmpCpu.logical_id],0\n'
        '    jne user_smp_fail_untrusted\n'
        '    mov r8,cr3\n'
        '    call user_smp_to_kernel\n'
        '    mov rsp,[gs:UserCpu.kernel_stack]\n'
        '    sub rsp,8\n'
        '    xor edi,edi\n'
        '    mov rsi,r8\n'
        '    jmp user_runtime_failure_stop\n'
        'user_smp_fail_untrusted:')


def runtime_patch_entry(text):
    """Only the existing guarded screen_draw may display the fixed Report."""
    text = _replace(text, '%include "boot_progress.inc"\n',
        '%include "boot_progress.inc"\n%if RUNTIME_LEVEL >= 7\n%include "user_entry.inc"\nextern '+POINTER_EXPORT+'\nextern sched_xstate_restore\n%endif\n')
    text = _replace(text, '    cmp byte [rel boot_progress_failed],0\n    jne .progress_failed_title\n',
        '    cmp byte [rel boot_progress_phase],24\n'
        '    jne .runtime_failure_regular_title\n'
        '    mov rax,[rel runtime_failure_report]\n'
        '    test rax,rax\n'
        '    jz .runtime_failure_regular_title\n'
        '    cmp qword [rax],1\n'
        '    jne .runtime_failure_regular_title\n'
        '    cmp qword [rax+8],1\n'
        '    jne .runtime_failure_regular_title\n'
        '    lea rsi,[rel runtime_failure_title]\n'
        '    jmp .draw_title\n'
        '.runtime_failure_regular_title:\n'
        '    cmp byte [rel boot_progress_failed],0\n'
        '    jne .progress_failed_title\n')
    rows = []
    for index, (_, field) in enumerate(ROWS):
        value = '[rel boot_progress_cpus]' if field == 'boot_progress_cpus' else '[rbx + '+str(FIELDS.index(field)*8)+']'
        rows.append('    BOOT_USER_RUNTIME_FAILURE_LINE user_runtime_status_label_'+str(index)+','+str(120+index*24)+','+value)
    body = '''.progress_regular:
    ; USER_RUNTIME_FAILURE_RENDER_BEGIN: scalar data only, fixed compiler-owned BSS.
    cmp byte [rel boot_progress_phase],24
    jne .user_runtime_status_regular
    call dong_user_runtime_status_pointer
    mov rbx,rax
    test rbx,rbx
    jz .user_runtime_status_regular
    cmp qword [rbx],1
    jne .user_runtime_status_regular
    cmp qword [rbx + 8],1
    jne .user_runtime_status_regular
%macro BOOT_USER_RUNTIME_FAILURE_LINE 3
    lea rsi,[rel %1]
    mov edi,56
    mov edx,%2
    call text_draw
    mov rax,%3
    mov edi,238
    mov edx,%2
    call screen_hex_draw
%endmacro
'''+ '\n'.join(rows)+'''
%unmacro BOOT_USER_RUNTIME_FAILURE_LINE 3
    jmp .painted
.user_runtime_status_regular:
    ; USER_RUNTIME_FAILURE_RENDER_END
'''
    text = _replace(text, '.progress_regular:\n', body)
    text = _replace(text, '    cmp ecx,23\n', '    cmp ecx,24\n')
    text = _replace(text, '    dd boot_progress_user_dispatch-boot_progress_titles\n',
        '    dd boot_progress_user_dispatch-boot_progress_titles\n    dd runtime_failure_title-boot_progress_titles\n')
    labels = 'runtime_failure_title: db "'+TITLE+'",0\n'
    labels += ''.join('user_runtime_status_label_'+str(i)+': db "'+label+'",0\n' for i,(label,_) in enumerate(ROWS))
    text = _replace(text, 'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n',
                    labels+'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n')
    return text+"""
section .bss
align 8, resb 1
global runtime_failure_view
runtime_failure_view: resq 1
runtime_failure_report: resq 1
section .text
global user_runtime_failure_stop
extern dong_user_runtime_status_run
user_runtime_failure_stop:
    ; The trusted caller supplies SysV RSP%16=8 after restoring kernel CR3.
    ; There is no raw exception Frame read and no success-path callback here.
    sub rsp,8
    mov r12,rdi
    mov r13,rsi
    cli
    cld
    mov rdi,[gs:UserEntryCpu.kernel_xstate]
    call sched_xstate_restore
    mov rdi,r12
    mov rsi,r13
    call dong_user_runtime_status_run
    mov [rel runtime_failure_report],rax
    ; Only the BSP can be the compositor writer. With IF0 it is stopped;
    ; the original screen_draw still acquires and obeys the existing Gate.
    mov r14,[rel boot_progress_view]
    mov rax,[rel runtime_failure_view]
    test rax,rax
    jz .view_ready
    mov [rel boot_progress_view],rax
.view_ready:
    HW_BOOT_STAGE 24
    mov [rel boot_progress_view],r14
    lea rsi,[rel runtime_failure_marker]
    call serial_write
    cli
.stop:
    hlt
    jmp .stop
section .rodata
runtime_failure_marker: db "DONGOS_USER_RUNTIME_FAILURE",13,10,0
"""


def patch_probe(raw):
    check(b'import boot.user_runtime_status;' not in raw, 'normal graph already imports the diagnostic')
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    return raw+(b'' if raw.endswith(b'\n') else newline)+b'import boot.user_runtime_status;'+newline+b'import boot.startup_console;'+newline


def _canonical_command_plan(normal, log, output):
    normal, log, output = Path(normal).resolve(), prior._ordinary(log), Path(output).absolute()
    base = prior.command_plan(normal, log, output)
    commands = [prior.argv_from_log(line[2:]) for line in log.read_text(encoding='utf-8').splitlines() if line.startswith('+ ')]
    def one(predicate):
        found = [c for c in commands if predicate(c)]
        check(len(found) == 1, 'unique original kernel compile/assembly command required')
        return found[0]
    def emits(c, path):
        return '-o' in c and c[c.index('-o')+1] == str(path)
    original_compile = [sys.executable, '-m', 'lang.dongc', '--mode', 'release', '--function-sections', '-O1',
        '--emit-ir', str(normal/'kernel-optimization.json'), '--root', str(ROOT/'lang/examples'),
        '--root', str(normal/'kernel-profile-src'), '--root', str(ROOT/'lang/std'),
        '--root', str(normal/'usb-only-services'), '--emit-asm', str(normal/'dong_probe.asm'),
        '--emit-layout', str(normal/'dong_layout.json'), str(normal/'kernel-profile-src/smp_probe.dg')]
    actual_compile = one(lambda c: '--emit-asm' in c and c[c.index('--emit-asm')+1] == str(normal/'dong_probe.asm'))
    check(actual_compile == original_compile, 'normal release Dong compile template differs')
    nasm = base['normal_commands']['services_run'][0]
    warnings = tuple(v for v in base['normal_commands']['services_run'] if v in ('-w-reloc-rel-dword', '-w-reloc-abs-qword'))
    old_dong = prior._nasm(nasm, 'elf64', (ROOT/'include', normal), normal/'dong_probe.o', normal/'dong_probe.asm', (), warnings)
    old_entry = prior._nasm(nasm, 'elf64', (ROOT/'include', normal), normal/'entry.o', ROOT/'kernel/entry.asm',
                            ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=1'), warnings)
    check(one(lambda c: emits(c, normal/'dong_probe.o')) == old_dong, 'normal Dong object recipe differs')
    check(one(lambda c: emits(c, normal/'entry.o')) == old_entry, 'normal entry object recipe differs')
    compile_command = list(original_compile)
    for flag, name in (('--emit-ir', 'kernel-optimization.json'), ('--emit-asm', 'dong_probe.asm'), ('--emit-layout', 'dong_layout.json')):
        compile_command[compile_command.index(flag)+1] = str(output/name)
    compile_command[compile_command.index(str(normal/'kernel-profile-src'))] = str(output/'kernel-profile-src')
    compile_command[-1] = str(output/'kernel-profile-src/smp_probe.dg')
    new = dict(base['commands'])
    new['services_run'] = prior._nasm(nasm,'elf64',(ROOT/'include',output,normal),output/'services_run.o',output/'private/services_run.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    new['compile'] = compile_command
    new['dong_probe'] = prior._nasm(nasm, 'elf64', (ROOT/'include', output, normal), output/'dong_probe.o', output/'dong_probe.asm', (), warnings)
    new['entry'] = prior._nasm(nasm, 'elf64', (ROOT/'include', output, normal), output/'entry.o', output/'private/entry.asm',
                              ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=1'), warnings)
    old_user_entry = prior._nasm(nasm,'elf64',(ROOT/'include',normal),normal/'user_entry.o',ROOT/'kernel/sched/user_entry.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    check(one(lambda c: emits(c,normal/'user_entry.o'))==old_user_entry,'normal user-entry recipe differs')
    new['user_entry'] = prior._nasm(nasm,'elf64',(ROOT/'include',output,normal),output/'user_entry.o',output/'private/user_entry.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    old_user_boot = prior._nasm(nasm,'elf64',(ROOT/'include',normal),normal/'user_boot.o',ROOT/'kernel/sched/user_boot.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    check(one(lambda c: emits(c,normal/'user_boot.o'))==old_user_boot,'normal user-boot recipe differs')
    new['user_boot'] = prior._nasm(nasm,'elf64',(ROOT/'include',output,normal),output/'user_boot.o',output/'private/user_boot.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    kernel = base['normal_commands']['kernel']
    new['kernel'] = [*kernel[:kernel.index('-o')+1], str(output/'kernel.elf'),
        *(str(output/name) if name in REPLACED_OBJECTS else str(normal/name) for name in prior.KERNEL_OBJECTS)]
    original = dict(base['normal_commands'], compile=original_compile, dong_probe=old_dong, entry=old_entry, user_entry=old_user_entry, user_boot=old_user_boot)
    tools = dict(base['tool_sha256'])
    tools[str(Path(sys.executable).resolve())] = sha(sys.executable)
    return dict(normal_commands=original, commands=new, tool_sha256=tools)


def command_plan(normal, log, output):
    # Older genuine build logs may use relative output operands. Resolve only
    # existing paths against the recorded build cwd; keep the original raw log
    # and hash. Executable/flags/order and every resolved input remain strict.
    parser = prior.argv_from_log
    resolutions = []
    def resolved(line):
        values = parser(line); result = []
        for value in values:
            prefix = next((p for p in ('/out:','/map:') if value.startswith(p)), '')
            if prefix:
                tail = Path(value[len(prefix):])
                if not tail.is_absolute() and (ROOT/tail).exists():
                    value = prefix+str((ROOT/tail).resolve())
            candidate = Path(value)
            if not value.startswith('-') and not candidate.is_absolute() and (ROOT/candidate).exists():
                absolute = str((ROOT/candidate).resolve())
                if value.endswith(('\\','/')): absolute += os.sep
                resolutions.append(dict(original=value,resolved=absolute)); value=absolute
            result.append(value)
        return result
    prior.argv_from_log = resolved
    try:
        plan = _canonical_command_plan(normal,log,output)
    finally:
        prior.argv_from_log = parser
    plan['original_log_path_resolutions'] = resolutions
    return plan


CONSOLE_FIELDS = ('version','done','error_code','kind','returns','captures','logs','slot','operation','event','syscalls','entries','bridge_stage','rip','stopped','accepted')
CONSOLE_ROWS = (('POINT','kind'),('SLOT','slot'),('SYSCALLS','syscalls'),('EVENT','event'),('OPERATION','operation'),('USER RIP','rip'))
CONSOLE_TITLE = 'DONGOS BOOT LIVE'

def console_layout(layout):
    matches=[t for t in layout['types'] if t['full_name']=='boot.startup_console.Report']
    check(len(matches)==1,'one console layout required');r=matches[0]
    check(r['size']==456 and r['alignment']==8 and [(f['name'],f['offset'],f['size']) for f in r['fields']]==[(n,i*8,8) for i,n in enumerate(CONSOLE_FIELDS)]+[('text',128,328)],'console layout differs')
    return r

def patch_user_entry_asm(text):
    text=runtime_patch_user_entry_asm(text)
    return _replace(text,'user_smp_return:\n','user_smp_return:\n    ; BOOT_CONSOLE_RETURN: trusted kernel root/xstate, before commit/IRET.\n    mov edi,1\n    call startup_console_tick\n').replace('extern user_runtime_failure_stop\n','extern user_runtime_failure_stop\nextern startup_console_tick\n')

def patch_user_bridge(text):
    text=_replace(text,'unsafe extern "sysv64" fn user_bridge_restore(pointer:u64)void;',
        'unsafe extern "sysv64" fn user_bridge_restore(pointer:u64)void;\nunsafe extern "sysv64" fn startup_console_tick(kind:u64)void;')
    return _replace(text,'user_bridge_restore((*header).kernel_xstate);\n stage(cpu,DEADLINE);',
        'user_bridge_restore((*header).kernel_xstate);\n if cpu==0{startup_console_tick(3);}\n stage(cpu,DEADLINE);')

def patch_services_run(text):
    check('startup_console_write_bytes:' not in text, 'services console hook already present')
    return _replace(text,'services_write_bytes:\n', '''extern startup_console_tick
services_write_bytes:
    push rbx
    call startup_console_write_bytes
    mov rbx,rax
    mov edi,2
    call startup_console_tick
    mov rax,rbx
    pop rbx
    ret
startup_console_write_bytes:
''')

def patch_entry(text):
    text=runtime_patch_entry(text)
    # Preserve separators in real log keys; the ordinary boot font has blanks
    # for punctuation and stops at Z. Only this private diagnostic extends it.
    text=_replace(text,'    cmp eax, 90\n','    cmp eax, 95\n')
    text=_replace(text,'    times (65-58)*7 db 0\n',
        '    db 0,4,4,0,4,4,0 ; :\n    times 2*7 db 0\n'
        '    db 0,0,31,0,31,0,0 ; =\n    times 7 db 0\n'
        '    db 14,17,1,2,4,0,4 ; ?\n    times 7 db 0\n')
    text=_replace(text,'    db 31,1,2,4,8,16,31 ; Z\n',
        '    db 31,1,2,4,8,16,31 ; Z\n    times 4*7 db 0\n'
        '    db 0,0,0,0,0,0,31 ; _\n')
    body='''    ; BOOT_CONSOLE_RENDER_BEGIN: owned BSS, six scalars and eight bounded rows.
    cmp byte [rel boot_progress_phase],25
    jne .startup_console_regular
    call dong_startup_console_pointer
    mov rbx,rax
    cmp qword [rbx],1
    jne .startup_console_regular
    cmp qword [rbx+8],1
    jne .startup_console_regular
'''
    for i,(_,field) in enumerate(CONSOLE_ROWS):
        body+='    lea rsi,[rel startup_console_label_'+str(i)+']\n    mov edi,56\n    mov edx,'+str(110+i*24)+'\n    call text_draw\n    mov rax,[rbx+'+str(CONSOLE_FIELDS.index(field)*8)+']\n    mov edi,238\n    mov edx,'+str(110+i*24)+'\n    call screen_hex_draw\n'
    for i in range(8):
        body+='    lea rsi,[rbx+'+str(128+i*41)+']\n    mov edi,56\n    mov edx,'+str(256+i*24)+'\n    call text_draw\n'
    body+='    jmp .painted\n.startup_console_regular:\n    ; BOOT_CONSOLE_RENDER_END\n'
    text=_replace(text,'.progress_regular:\n','.progress_regular:\n'+body)
    text=_replace(text,'    cmp ecx,24\n','    cmp ecx,25\n')
    text=_replace(text,'    dd runtime_failure_title-boot_progress_titles\n','    dd runtime_failure_title-boot_progress_titles\n    dd startup_console_title-boot_progress_titles\n')
    labels='startup_console_title: db "'+CONSOLE_TITLE+'",0\n'
    labels+=''.join('startup_console_label_'+str(i)+': db "'+label+'",0\n' for i,(label,_) in enumerate(CONSOLE_ROWS))
    text=_replace(text,'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n',labels+'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n')
    return text+'''
section .text
global startup_console_tick
extern dong_startup_console_run,dong_startup_console_pointer
extern services_console_head,services_console_accepted,services_console_ring
; All callers are trusted, IF0 and on kernel CR3 after restoring kernel xstate.
; The producer permanently disables this before the first compositor IRET.
startup_console_tick:
    cmp byte [rel startup_console_disabled],0
    jne .return
    cmp qword [gs:UserSmpCpu.logical_id],0
    jne .return
    mov rax,cr3
    cmp rax,[gs:UserCpu.original_cr3]
    jne .return
    pushfq
    pop rax
    test eax,0x200
    jnz .return
    push rbx
    push r12
    push r13
    mov rsi,[rel services_console_head]
    mov rdx,[rel services_console_accepted]
    lea rcx,[rel services_console_ring]
    call dong_startup_console_run
    test rax,rax
    jz .done
    call dong_startup_console_pointer
    cmp qword [rax+112],0
    je .display
    mov byte [rel startup_console_disabled],1
.display:
    mov rbx,[rel boot_progress_view]
    movzx r12d,byte [rel boot_progress_phase]
    mov rax,[rel runtime_failure_view]
    mov [rel boot_progress_view],rax
    HW_BOOT_STAGE 25
    mov [rel boot_progress_view],rbx
    mov byte [rel boot_progress_phase],r12b
.done:
    pop r13
    pop r12
    pop rbx
.return:
    ret
section .bss
global startup_console_disabled
startup_console_disabled: resb 1
'''


def _private_sources(output):
    for source, target, patch in (('kernel/entry.asm', 'entry.asm', patch_entry),
                                    ('kernel/sched/user_boot.asm','user_boot.asm',patch_user_boot_asm),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm),('kernel/services_run.asm','services_run.asm',patch_services_run)):
        text = (ROOT/source).read_bytes().decode('utf-8')
        (output/'private'/target).write_bytes(patch(text).encode('utf-8'))
    firmware = (ROOT/'boot/efi_main.asm').read_bytes()
    check(firmware.count(prior.BANNER_BEFORE) == 1 and BANNER not in firmware, 'one normal EFI banner required')
    (output/'private/efi_main.asm').write_bytes(firmware.replace(prior.BANNER_BEFORE, BANNER))


def _verify_overlay(normal, output):
    before = prior._snapshot(normal/'kernel-profile-src')
    after = prior._snapshot(output/'kernel-profile-src')
    # Fresh ordinary builds snapshot even dormant DG modules. They may carry
    # this exact source, but the normal root must never import it already.
    check(MODULE_PATH not in before or before[MODULE_PATH] == sha(ROOT/'kernel'/MODULE_PATH),
          'normal snapshot contains a different dormant runtime status module')
    expected = dict(before)
    expected[MODULE_PATH] = sha(ROOT/'kernel'/MODULE_PATH)
    expected['boot/startup_console.dg'] = sha(ROOT/'kernel/boot/startup_console.dg')
    expected['sched/user_bridge.dg'] = hashlib.sha256(patch_user_bridge((normal/'kernel-profile-src/sched/user_bridge.dg').read_bytes().decode('utf-8')).encode('utf-8')).hexdigest()
    expected['smp_probe.dg'] = hashlib.sha256(patch_probe((normal/'kernel-profile-src/smp_probe.dg').read_bytes())).hexdigest()
    check(after == expected, 'private kernel overlay differs beyond explicit runtime module/import')
    return after


def _verify_report_layout(output):
    layout = json.loads((output/'dong_layout.json').read_text(encoding='utf-8'))
    reports = [t for t in layout['types'] if t['full_name'] == MODULE+'.Report']
    check(len(reports) == 1, 'one actual runtime failure screen Report layout required')
    report = reports[0]
    check(report['size'] == REPORT_SIZE and report['alignment'] == 8
          and [(f['name'], f['offset'], f['size']) for f in report['fields']]
          == [(name, index*8, 8) for index, name in enumerate(FIELDS)], 'actual diagnostic Report layout differs')
    return dict(failure=report,console=console_layout(layout))


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def build_preflight(normal_source, normal_build_log, output):
    normal, metadata, bundle = prior._normal_checked(normal_source)
    log = prior._ordinary(normal_build_log)
    module = prior._ordinary(ROOT/'kernel'/MODULE_PATH)
    output = prior._new_output(output, normal)
    plan = command_plan(normal, log, output)
    before = prior._snapshot(normal)
    sources = {name: sha(ROOT/name) for name in metadata['source_sha256']}
    sources['kernel/'+MODULE_PATH] = sha(module)
    sources['kernel/boot/startup_console.dg'] = sha(ROOT/'kernel/boot/startup_console.dg')
    sources['tools/build_bsp_diagnostic.py'] = sha(ROOT/'tools/build_bsp_diagnostic.py')
    output.mkdir(parents=True)
    (output/'private').mkdir()
    (output/'esp/EFI/BOOT').mkdir(parents=True)
    shutil.copytree(normal/'kernel-profile-src', output/'kernel-profile-src')
    shutil.copyfile(module, output/'kernel-profile-src'/MODULE_PATH)
    probe = output/'kernel-profile-src/smp_probe.dg'
    probe.write_bytes(patch_probe(probe.read_bytes()))
    shutil.copyfile(ROOT/'kernel/boot/startup_console.dg',output/'kernel-profile-src/boot/startup_console.dg')
    bridge=output/'kernel-profile-src/sched/user_bridge.dg'
    bridge.write_bytes(patch_user_bridge(bridge.read_bytes().decode('utf-8')).encode('utf-8'))
    overlay = _verify_overlay(normal, output)
    _private_sources(output)
    shutil.copyfile(normal/'esp/SERVICES.BIN', output/'esp/SERVICES.BIN')
    for name in prior.SERVICE_NAMES:
        folder = output/'services'/name
        folder.mkdir(parents=True)
        shutil.copyfile(normal/'services'/name/'program.elf', folder/'program.elf')
    executed = []
    def execute(label):
        command = plan['commands'][label]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=240, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        record = dict(label=label, command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        executed.append(record)
        _write_json(output/(label+'-command.json'), record)
        check(result.returncode == 0, 'runtime failure screen '+label+' failed: '+result.stderr[-1800:])
    for label in COMMAND_ORDER[:COMMAND_ORDER.index('image')]:
        execute(label)
    report = _verify_report_layout(output)
    raw = materialize((output/'kernel.elf').read_bytes())
    check(raw != (normal/'kernel.bin').read_bytes(), 'diagnostic kernel must differ from normal')
    (output/'kernel.bin').write_bytes(raw)
    image = pack_image(raw)
    (output/'esp/DONGOS.IMG').write_bytes(image)
    (output/'image_manifest.inc').write_text(manifest_text(image), encoding='utf-8')
    for label in COMMAND_ORDER[COMMAND_ORDER.index('image'):]:
        execute(label)
    check(prior._snapshot(normal) == before and all(sha(ROOT/name) == digest for name,digest in sources.items()),
          'normal or diagnostic source changed during build')
    artifacts = prior._snapshot(output)
    receipt = dict(version=VERSION, profile=PROFILE, intentional_failure_stop=True, continuous_user_runtime=True, fatal_failure_screen=True, normal_ap_idle=True,
        success_path_unchanged=False, view_retirement_deferred=False, no_success_hook=False,
        continuous_startup_console=True, compositor_handoff_disables_console=True, no_success_stop=True,
        ordinary_normal_build=False, no_device_ownership_or_dma=True,
        platform_cpu_topology_unchanged=True, stage=STAGE, fields=list(FIELDS), rows=[list(r) for r in ROWS],
        title=TITLE, banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        normal_source=str(normal), normal_build_log=str(log), normal_build_log_sha256=sha(log),
        normal_manifest_sha256=sha(normal/'build-inputs.json'), normal_inputs_sha256=before,
        source_sha256=sources, builder_sha256=sha(__file__), recipe=plan, executed=executed,
        replaced_kernel_objects=list(REPLACED_OBJECTS), kernel_overlay_sha256=overlay,
        report_layout=report, original_services_bundle=bundle, artifacts=artifacts)
    _write_json(output/'startup-console.json', receipt)
    verify_preflight(output/'esp')
    return output/'esp'


def verify_preflight(esp):
    esp = prior._ordinary(esp, directory=True)
    output = esp.parent
    check(esp.name == 'esp' and output.is_relative_to(ROOT/'build'), 'runtime failure screen ESP path differs')
    check(not (output/'build-inputs.json').exists(), 'runtime diagnostic must not masquerade as a normal build')
    receipt = json.loads(prior._ordinary(output/'startup-console.json').read_text(encoding='utf-8'))
    expected = dict(version=VERSION, profile=PROFILE, intentional_failure_stop=True, continuous_user_runtime=True, fatal_failure_screen=True, normal_ap_idle=True,
        success_path_unchanged=False, view_retirement_deferred=False, no_success_hook=False,
        continuous_startup_console=True, compositor_handoff_disables_console=True, no_success_stop=True,
        ordinary_normal_build=False, no_device_ownership_or_dma=True,
        platform_cpu_topology_unchanged=True, stage=STAGE, fields=list(FIELDS), rows=[list(r) for r in ROWS],
        title=TITLE, banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        replaced_kernel_objects=list(REPLACED_OBJECTS))
    check(all(receipt.get(k) == value and type(receipt.get(k)) is type(value) for k,value in expected.items()),
          'runtime failure screen diagnostic profile differs')
    check(receipt['builder_sha256'] == sha(__file__), 'runtime failure screen builder changed')
    normal, metadata, bundle = prior._normal_checked(receipt['normal_source'])
    log = prior._ordinary(receipt['normal_build_log'])
    check(sha(log) == receipt['normal_build_log_sha256'] and sha(normal/'build-inputs.json') == receipt['normal_manifest_sha256'],
          'original normal manifest/log identity changed')
    check(prior._snapshot(normal) == receipt['normal_inputs_sha256'], 'original normal tree changed')
    sources = {name: sha(ROOT/name) for name in metadata['source_sha256']}
    sources['kernel/'+MODULE_PATH] = sha(ROOT/'kernel'/MODULE_PATH)
    sources['kernel/boot/startup_console.dg'] = sha(ROOT/'kernel/boot/startup_console.dg')
    sources['tools/build_bsp_diagnostic.py'] = sha(ROOT/'tools/build_bsp_diagnostic.py')
    check(sources == receipt['source_sha256'], 'production/diagnostic source identities changed')
    check(command_plan(normal, log, output) == receipt['recipe'], 'runtime failure screen recipe changed')
    check([r['label'] for r in receipt['executed']] == list(COMMAND_ORDER)
          and all(r['returncode'] == 0 and r['command'] == receipt['recipe']['commands'][r['label']]
                  for r in receipt['executed']), 'runtime failure screen execution sequence/command differs')
    check(_verify_overlay(normal, output) == receipt['kernel_overlay_sha256'], 'runtime failure screen overlay identities changed')
    for original,target,patch in (('kernel/entry.asm','entry.asm',patch_entry),('kernel/sched/user_boot.asm','user_boot.asm',patch_user_boot_asm),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm),('kernel/services_run.asm','services_run.asm',patch_services_run)):
        check((output/'private'/target).read_bytes() == patch((ROOT/original).read_bytes().decode('utf-8')).encode('utf-8'),
              'private source patch differs: '+target)
    original = (ROOT/'boot/efi_main.asm').read_bytes()
    check(original.count(prior.BANNER_BEFORE) == 1 and (output/'private/efi_main.asm').read_bytes()
          == original.replace(prior.BANNER_BEFORE, BANNER), 'private firmware changed beyond banner')
    check(_verify_report_layout(output) == receipt['report_layout'], 'runtime status Report compiler layout changed')
    check(bundle == receipt['original_services_bundle'] and (esp/'SERVICES.BIN').read_bytes() == (normal/'esp/SERVICES.BIN').read_bytes(),
          'original service bundle changed')
    for name in prior.SERVICE_NAMES:
        check((output/'services'/name/'program.elf').read_bytes() == (normal/'services'/name/'program.elf').read_bytes(),
              'original service ELF changed: '+name)
    actual = prior._snapshot(output)
    actual.pop('startup-console.json', None)
    check(actual == receipt['artifacts'], 'runtime failure screen artifact inventory/hash differs')
    raw = materialize((output/'kernel.elf').read_bytes())
    image = (esp/'DONGOS.IMG').read_bytes()
    check(raw == (output/'kernel.bin').read_bytes() and raw != (normal/'kernel.bin').read_bytes()
          and unpack_image(image, hashlib.sha256(image).digest()) == raw
          and (output/'image_manifest.inc').read_text(encoding='utf-8') == manifest_text(image),
          'diagnostic kernel/image/manifest binding differs')
    digest = hashlib.sha256(image).digest()
    check(digest in (output/'image.obj').read_bytes() and digest in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(),
          'EFI verifier lost the runtime diagnostic image digest')
    definitions = [line for line in manifest_text(image).splitlines() if line.startswith('%define ')]
    for name in ('image.lst', 'efi_main.lst'):
        listing = (output/name).read_text(encoding='utf-8')
        check(all(len(re.findall(r'(?m)^\s*\d+\s+<1> '+re.escape(line)+r'\s*$',listing)) == 1 for line in definitions),
              'both actual EFI manifest consumers must use this image: '+name)
    check(BANNER+b'\r\n\0' in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(), 'runtime diagnostic banner missing')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal-source',type=Path,required=True)
    parser.add_argument('--normal-build-log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    esp = build_preflight(args.normal_source,args.normal_build_log,args.output)
    print('STARTUP_CONSOLE_BUILD_PASS',esp,flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise SystemExit('runtime failure screen: '+str(error))

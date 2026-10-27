"""Build continuous USB-only userspace with a trusted BSP failure screen.

Only private build copies are changed. Normal AP idle, user capture, service
callbacks, view retirement and desktop execution remain enabled. The extra
screen is entered only by the original trusted BSP user-entry fail-stop,
using its saved immutable view through the existing framebuffer Gate. No
normal artifact, CPU topology, service bundle or device authority is changed.
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
PROFILE = 'user-runtime-failure-screen'
STAGE = 24
REPORT_SIZE = 256
FIELDS = ('version', 'done', 'error_code', 'cpu', 'cpus', 'failure_cpu', 'failure_code', 'failure_detail', 'entry', 'event', 'stage', 'domain_failed', 'bridge_failed', 'lock', 'owner', 'online', 'mode', 'slot', 'token', 'captured', 'syscalls', 'user_entries', 'header_error', 'operation', 'rip', 'rsp', 'frame_root', 'raw_root', 'pcid', 'calls', 'failure_mask', 'frame_kind')
ROWS = (('CHECK ERROR', 'error_code'), ('ERROR CPU', 'failure_cpu'), ('ERROR CODE', 'failure_code'), ('DETAIL', 'failure_detail'), ('ENTRY', 'entry'), ('LAST EVENT', 'event'), ('BRIDGE STAGE', 'stage'), ('CPU MODE', 'mode'), ('SLOT', 'slot'), ('OPERATION', 'operation'), ('USER RIP', 'rip'), ('SYSCALLS', 'syscalls'), ('USER ENTRIES', 'user_entries'), ('DOMAIN FAIL', 'domain_failed'), ('BRIDGE CALLS', 'calls'))
TITLE = 'DONGOS RUNTIME FAILED'
BANNER = b'DongOS USER RUNTIME R1'
COMPLETION_MARKER = 'DONGOS_USER_RUNTIME_FAILURE'
MODULE = 'boot.user_runtime_status'
MODULE_PATH = 'boot/user_runtime_status.dg'
RUN_EXPORT = 'dong_user_runtime_status_run'
POINTER_EXPORT = 'dong_user_runtime_status_pointer'
REPLACED_OBJECTS = ('entry.o', 'dong_probe.o', 'user_entry.o', 'user_boot.o')
COMMAND_ORDER = ('compile', 'dong_probe', 'entry', 'user_entry', 'user_boot', 'kernel',
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


def patch_user_entry_asm(text):
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


def patch_entry(text):
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
    return raw+(b'' if raw.endswith(b'\n') else newline)+b'import boot.user_runtime_status;'+newline


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
    del new['services_run']
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


def _private_sources(output):
    for source, target, patch in (('kernel/entry.asm', 'entry.asm', patch_entry),
                                    ('kernel/sched/user_boot.asm','user_boot.asm',patch_user_boot_asm),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm)):
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
    return report


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
    sources['tools/build_bsp_diagnostic.py'] = sha(ROOT/'tools/build_bsp_diagnostic.py')
    output.mkdir(parents=True)
    (output/'private').mkdir()
    (output/'esp/EFI/BOOT').mkdir(parents=True)
    shutil.copytree(normal/'kernel-profile-src', output/'kernel-profile-src')
    shutil.copyfile(module, output/'kernel-profile-src'/MODULE_PATH)
    probe = output/'kernel-profile-src/smp_probe.dg'
    probe.write_bytes(patch_probe(probe.read_bytes()))
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
    for label in COMMAND_ORDER[:6]:
        execute(label)
    report = _verify_report_layout(output)
    raw = materialize((output/'kernel.elf').read_bytes())
    check(raw != (normal/'kernel.bin').read_bytes(), 'diagnostic kernel must differ from normal')
    (output/'kernel.bin').write_bytes(raw)
    image = pack_image(raw)
    (output/'esp/DONGOS.IMG').write_bytes(image)
    (output/'image_manifest.inc').write_text(manifest_text(image), encoding='utf-8')
    for label in COMMAND_ORDER[6:]:
        execute(label)
    check(prior._snapshot(normal) == before and all(sha(ROOT/name) == digest for name,digest in sources.items()),
          'normal or diagnostic source changed during build')
    artifacts = prior._snapshot(output)
    receipt = dict(version=VERSION, profile=PROFILE, intentional_failure_stop=True, continuous_user_runtime=True, fatal_failure_screen=True, normal_ap_idle=True,
        success_path_unchanged=True, view_retirement_deferred=False, no_success_hook=True,
        ordinary_normal_build=False, no_device_ownership_or_dma=True,
        platform_cpu_topology_unchanged=True, stage=STAGE, fields=list(FIELDS), rows=[list(r) for r in ROWS],
        title=TITLE, banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        normal_source=str(normal), normal_build_log=str(log), normal_build_log_sha256=sha(log),
        normal_manifest_sha256=sha(normal/'build-inputs.json'), normal_inputs_sha256=before,
        source_sha256=sources, builder_sha256=sha(__file__), recipe=plan, executed=executed,
        replaced_kernel_objects=list(REPLACED_OBJECTS), kernel_overlay_sha256=overlay,
        report_layout=report, original_services_bundle=bundle, artifacts=artifacts)
    _write_json(output/'user-runtime.json', receipt)
    verify_preflight(output/'esp')
    return output/'esp'


def verify_preflight(esp):
    esp = prior._ordinary(esp, directory=True)
    output = esp.parent
    check(esp.name == 'esp' and output.is_relative_to(ROOT/'build'), 'runtime failure screen ESP path differs')
    check(not (output/'build-inputs.json').exists(), 'runtime diagnostic must not masquerade as a normal build')
    receipt = json.loads(prior._ordinary(output/'user-runtime.json').read_text(encoding='utf-8'))
    expected = dict(version=VERSION, profile=PROFILE, intentional_failure_stop=True, continuous_user_runtime=True, fatal_failure_screen=True, normal_ap_idle=True,
        success_path_unchanged=True, view_retirement_deferred=False, no_success_hook=True,
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
    sources['tools/build_bsp_diagnostic.py'] = sha(ROOT/'tools/build_bsp_diagnostic.py')
    check(sources == receipt['source_sha256'], 'production/diagnostic source identities changed')
    check(command_plan(normal, log, output) == receipt['recipe'], 'runtime failure screen recipe changed')
    check([r['label'] for r in receipt['executed']] == list(COMMAND_ORDER)
          and all(r['returncode'] == 0 and r['command'] == receipt['recipe']['commands'][r['label']]
                  for r in receipt['executed']), 'runtime failure screen execution sequence/command differs')
    check(_verify_overlay(normal, output) == receipt['kernel_overlay_sha256'], 'runtime failure screen overlay identities changed')
    for original,target,patch in (('kernel/entry.asm','entry.asm',patch_entry),('kernel/sched/user_boot.asm','user_boot.asm',patch_user_boot_asm),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm)):
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
    actual.pop('user-runtime.json', None)
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
    print('USER_RUNTIME_BUILD_PASS',esp,flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise SystemExit('runtime failure screen: '+str(error))

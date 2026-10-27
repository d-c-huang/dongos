"""Build an explicit first captured user-entry / trusted BSP failure checkpoint.

Only private build copies are changed. The normal USB-only desktop, its
seventeen service ELFs, CPU topology, DMA policy and all device ownership
rules remain unchanged. Normal AP idle executes; this image may enter CPL3
but stops before the first service callback. Existing framebuffer mappings
remain, while sole initial BSP-bound INIT prevents a compositor writer.
This image deliberately stops; it is not a desktop.
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
PROFILE = 'first-user-entry-checkpoint'
STAGE = 24
REPORT_SIZE = 192
FIELDS = ('version', 'done', 'error_code', 'reason', 'cpu', 'cpus', 'vector', 'operation', 'rip', 'rsp', 'frame_root', 'raw_root', 'mode', 'slot', 'token', 'captured', 'syscalls', 'user_entries', 'header_error', 'bridge_stage', 'first_error', 'domain_failed', 'bridge_failed', 'frame_kind')
ROWS = (('CHECK ERROR', 'error_code'), ('REASON', 'reason'), ('CPU', 'cpu'), ('VECTOR', 'vector'), ('OPERATION', 'operation'), ('SLOT', 'slot'), ('USER RIP', 'rip'), ('USER RSP', 'rsp'), ('FRAME CR3', 'frame_root'), ('CPU MODE', 'mode'), ('CAPTURED', 'captured'), ('SYSCALLS', 'syscalls'), ('USER ENTRIES', 'user_entries'), ('BRIDGE STAGE', 'bridge_stage'), ('FIRST ERROR', 'first_error'))
TITLE = 'DONGOS FIRST USER'
BANNER = b'DongOS FIRST USER R1'
COMPLETION_MARKER = 'DONGOS_FIRST_USER_CHECKPOINT_DONE'
MODULE = 'boot.first_user_checkpoint'
MODULE_PATH = 'boot/first_user_checkpoint.dg'
RUN_EXPORT = 'dong_first_user_checkpoint_run'
POINTER_EXPORT = 'dong_first_user_checkpoint_pointer'
REPLACED_OBJECTS = ('entry.o', 'dong_probe.o', 'services_run.o', 'user_entry.o')
COMMAND_ORDER = ('compile', 'dong_probe', 'entry', 'services_run', 'user_entry', 'kernel',
                 'image', 'efi_main', 'loader')
check, sha = prior.check, prior.sha


def _replace(text, before, after):
    newline = '\r\n' if '\r\n' in text else '\n'
    before, after = before.replace('\n', newline), after.replace('\n', newline)
    check(text.count(before) == 1, 'unique private patch location required: '+before[:70])
    return text.replace(before, after)


def patch_services_run(text):
    return text


def patch_user_boot(text):
    # Held by the original BSP Domain lock, before the first user is admitted.
    # Preserve original mark/unlock and all AP startup/selection code. Keeping
    # this immutable view is safe only while INIT is the sole runnable token.
    return _replace(text, ' user_boot_mark(23);user_boot_retire();',
        ' if (*d).engine==null||(*d).processes==null||(*(*d).engine).count!=1\n'
        '  ||(*(*d).engine).threads[5].affinity!=1||(*((*d).processes+5)).token==0{return 0x060b_0020;}\n'
        ' var initial_slot:usize=0;while initial_slot<16{\n'
        '  if initial_slot!=5&&(*((*d).processes+initial_slot)).token!=0{return 0x060b_0020;}initial_slot+=1;\n'
        ' }\n'
        ' user_boot_mark(23); // FIRST_USER_VIEW_RETAINED: first event stops before service callback.')


def patch_user_bridge(text):
    text = _replace(text, 'unsafe extern "sysv64" fn user_bridge_restore(pointer:u64)void;',
        'unsafe extern "sysv64" fn user_bridge_restore(pointer:u64)void;\n'
        'unsafe extern "sysv64" fn first_user_checkpoint_stop(cpu:usize,frame:u64,event:u64,reason:u64,raw_root:u64)void;')
    return _replace(text, 'user_bridge_restore((*header).kernel_xstate);\n stage(cpu,DEADLINE);',
        'user_bridge_restore((*header).kernel_xstate);\n'
        ' if cpu==0{first_user_checkpoint_stop(cpu,frame,event,0,0);}\n'
        ' stage(cpu,DEADLINE);')


def patch_user_entry_asm(text):
    text = _replace(text, 'extern sched_xstate_save,sched_xstate_restore\n',
        'extern sched_xstate_save,sched_xstate_restore\nextern first_user_checkpoint_stop\n')
    # This is the original trusted-GS boundary. Untrusted GS still bypasses it.
    # Restore the original root inside mapped user_entry code before jumping to
    # entry.o. Only the no-frame failure path may reset the trusted stack top.
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
        '    xor esi,esi\n'
        '    mov rdx,[gs:UserEntryCpu.event]\n'
        '    mov ecx,1\n'
        '    jmp first_user_checkpoint_stop\n'
        'user_smp_fail_untrusted:')


def patch_entry(text):
    """Only the existing guarded screen_draw may display the fixed Report."""
    text = _replace(text, '%include "boot_progress.inc"\n',
        '%include "boot_progress.inc"\n%if RUNTIME_LEVEL >= 7\n%include "user_entry.inc"\nextern '+POINTER_EXPORT+'\nextern sched_xstate_restore\n%endif\n')
    rows = []
    for index, (_, field) in enumerate(ROWS):
        value = '[rel boot_progress_cpus]' if field == 'boot_progress_cpus' else '[rbx + '+str(FIELDS.index(field)*8)+']'
        rows.append('    BOOT_FIRST_USER_CHECKPOINT_LINE first_user_checkpoint_label_'+str(index)+','+str(120+index*24)+','+value)
    body = '''.progress_regular:
    ; FIRST_USER_CHECKPOINT_RENDER_BEGIN: scalar data only, fixed compiler-owned BSS.
    cmp byte [rel boot_progress_phase],24
    jne .first_user_checkpoint_regular
    call dong_first_user_checkpoint_pointer
    mov rbx,rax
    test rbx,rbx
    jz .first_user_checkpoint_regular
    cmp qword [rbx],1
    jne .first_user_checkpoint_regular
    cmp qword [rbx + 8],1
    jne .first_user_checkpoint_regular
%macro BOOT_FIRST_USER_CHECKPOINT_LINE 3
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
%unmacro BOOT_FIRST_USER_CHECKPOINT_LINE 3
    jmp .painted
.first_user_checkpoint_regular:
    ; FIRST_USER_CHECKPOINT_RENDER_END
'''
    text = _replace(text, '.progress_regular:\n', body)
    text = _replace(text, '    cmp ecx,23\n', '    cmp ecx,24\n')
    text = _replace(text, '    dd boot_progress_user_dispatch-boot_progress_titles\n',
        '    dd boot_progress_user_dispatch-boot_progress_titles\n    dd first_user_checkpoint_title-boot_progress_titles\n')
    labels = 'first_user_checkpoint_title: db "'+TITLE+'",0\n'
    labels += ''.join('first_user_checkpoint_label_'+str(i)+': db "'+label+'",0\n' for i,(label,_) in enumerate(ROWS))
    text = _replace(text, 'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n',
                    labels+'boot_progress_unknown_title: db "DONGOS P7 BOOT STAGE",0\n')
    return text+'\nsection .text\nglobal first_user_checkpoint_stop\nextern dong_first_user_checkpoint_run\nfirst_user_checkpoint_stop:\n    ; SysV entry is RSP%16=8. Keep the deeper success call stack intact;\n    ; its raw user Frame is above us at Header.kernel_stack-208.\n    sub rsp,8\n    mov r12,rdi\n    mov r13,rsi\n    mov r14,rdx\n    mov r15,rcx\n    mov rbx,r8\n    test r15,r15\n    jnz .raw_root_saved\n    mov rbx,cr3\n.raw_root_saved:\n    cld\n    ; Success already restored this state. The common restore also makes a\n    ; trusted BSP fail-stop safe before entering any new DG or renderer code.\n    mov rdi,[gs:UserEntryCpu.kernel_xstate]\n    call sched_xstate_restore\n    mov rdi,r12\n    mov rsi,r13\n    mov rdx,r14\n    mov rcx,r15\n    mov r8,rbx\n    call dong_first_user_checkpoint_run\n    HW_BOOT_STAGE 24\n    lea rsi,[rel first_user_checkpoint_done_marker]\n    call serial_write\n    cli\n.stop:\n    hlt\n    jmp .stop\nsection .rodata\nfirst_user_checkpoint_done_marker: db "DONGOS_FIRST_USER_CHECKPOINT_DONE",13,10,0\n'


def patch_probe(raw):
    check(b'import boot.first_user_checkpoint;' not in raw, 'normal graph already imports the diagnostic')
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    return raw+(b'' if raw.endswith(b'\n') else newline)+b'import boot.first_user_checkpoint;'+newline


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
    new['compile'] = compile_command
    new['dong_probe'] = prior._nasm(nasm, 'elf64', (ROOT/'include', output, normal), output/'dong_probe.o', output/'dong_probe.asm', (), warnings)
    new['entry'] = prior._nasm(nasm, 'elf64', (ROOT/'include', output, normal), output/'entry.o', output/'private/entry.asm',
                              ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=1'), warnings)
    new['services_run'] = prior._nasm(nasm, 'elf64', (ROOT/'include', output, normal), output/'services_run.o',
                                     output/'private/services_run.asm', ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=1'), warnings)
    old_user_entry = prior._nasm(nasm,'elf64',(ROOT/'include',normal),normal/'user_entry.o',ROOT/'kernel/sched/user_entry.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    check(one(lambda c: emits(c,normal/'user_entry.o'))==old_user_entry,'normal user-entry recipe differs')
    new['user_entry'] = prior._nasm(nasm,'elf64',(ROOT/'include',output,normal),output/'user_entry.o',output/'private/user_entry.asm',('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'),warnings)
    kernel = base['normal_commands']['kernel']
    new['kernel'] = [*kernel[:kernel.index('-o')+1], str(output/'kernel.elf'),
        *(str(output/name) if name in REPLACED_OBJECTS else str(normal/name) for name in prior.KERNEL_OBJECTS)]
    original = dict(base['normal_commands'], compile=original_compile, dong_probe=old_dong, entry=old_entry, user_entry=old_user_entry)
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
                                    ('kernel/services_run.asm', 'services_run.asm', patch_services_run),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm)):
        text = (ROOT/source).read_bytes().decode('utf-8')
        (output/'private'/target).write_bytes(patch(text).encode('utf-8'))
    firmware = (ROOT/'boot/efi_main.asm').read_bytes()
    check(firmware.count(prior.BANNER_BEFORE) == 1 and BANNER not in firmware, 'one normal EFI banner required')
    (output/'private/efi_main.asm').write_bytes(firmware.replace(prior.BANNER_BEFORE, BANNER))


def _verify_overlay(normal, output):
    before = prior._snapshot(normal/'kernel-profile-src')
    after = prior._snapshot(output/'kernel-profile-src')
    check(MODULE_PATH not in before, 'normal graph already contains the diagnostic module')
    expected = dict(before)
    expected[MODULE_PATH] = sha(ROOT/'kernel'/MODULE_PATH)
    expected['smp_probe.dg'] = hashlib.sha256(patch_probe((normal/'kernel-profile-src/smp_probe.dg').read_bytes())).hexdigest()
    expected['sched/user_boot.dg'] = hashlib.sha256(patch_user_boot((normal/'kernel-profile-src/sched/user_boot.dg').read_text(encoding='utf-8')).encode('utf-8')).hexdigest()
    expected['sched/user_bridge.dg'] = hashlib.sha256(patch_user_bridge((normal/'kernel-profile-src/sched/user_bridge.dg').read_text(encoding='utf-8')).encode('utf-8')).hexdigest()
    check(after == expected, 'private kernel overlay differs beyond explicit module/import/boot/bridge changes')
    return after


def _verify_report_layout(output):
    layout = json.loads((output/'dong_layout.json').read_text(encoding='utf-8'))
    reports = [t for t in layout['types'] if t['full_name'] == MODULE+'.Report']
    check(len(reports) == 1, 'one actual first-user checkpoint Report layout required')
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
    user_boot = output/'kernel-profile-src/sched/user_boot.dg'
    user_boot.write_text(patch_user_boot(user_boot.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    user_bridge = output/'kernel-profile-src/sched/user_bridge.dg'
    user_bridge.write_text(patch_user_bridge(user_bridge.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
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
        check(result.returncode == 0, 'first-user checkpoint '+label+' failed: '+result.stderr[-1800:])
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
    receipt = dict(version=VERSION, profile=PROFILE, intentional_stop=True, first_user_entry_checkpoint=True, no_service_callback=True, normal_ap_idle=True,
        view_retirement_deferred=True, initial_init_slot=5, allows_user_cpl3_before_stop=True,
        ordinary_normal_build=False, no_device_ownership_or_dma=True,
        platform_cpu_topology_unchanged=True, stage=STAGE, fields=list(FIELDS), rows=[list(r) for r in ROWS],
        title=TITLE, banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        normal_source=str(normal), normal_build_log=str(log), normal_build_log_sha256=sha(log),
        normal_manifest_sha256=sha(normal/'build-inputs.json'), normal_inputs_sha256=before,
        source_sha256=sources, builder_sha256=sha(__file__), recipe=plan, executed=executed,
        replaced_kernel_objects=list(REPLACED_OBJECTS), kernel_overlay_sha256=overlay,
        report_layout=report, original_services_bundle=bundle, artifacts=artifacts)
    _write_json(output/'first-user-checkpoint.json', receipt)
    verify_preflight(output/'esp')
    return output/'esp'


def verify_preflight(esp):
    esp = prior._ordinary(esp, directory=True)
    output = esp.parent
    check(esp.name == 'esp' and output.is_relative_to(ROOT/'build'), 'first-user checkpoint ESP path differs')
    check(not (output/'build-inputs.json').exists(), 'intentional stop must not masquerade as a normal build')
    receipt = json.loads(prior._ordinary(output/'first-user-checkpoint.json').read_text(encoding='utf-8'))
    expected = dict(version=VERSION, profile=PROFILE, intentional_stop=True, first_user_entry_checkpoint=True, no_service_callback=True, normal_ap_idle=True,
        view_retirement_deferred=True, initial_init_slot=5, allows_user_cpl3_before_stop=True,
        ordinary_normal_build=False, no_device_ownership_or_dma=True,
        platform_cpu_topology_unchanged=True, stage=STAGE, fields=list(FIELDS), rows=[list(r) for r in ROWS],
        title=TITLE, banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        replaced_kernel_objects=list(REPLACED_OBJECTS))
    check(all(receipt.get(k) == value and type(receipt.get(k)) is type(value) for k,value in expected.items()),
          'first-user checkpoint diagnostic profile differs')
    check(receipt['builder_sha256'] == sha(__file__), 'first-user checkpoint builder changed')
    normal, metadata, bundle = prior._normal_checked(receipt['normal_source'])
    log = prior._ordinary(receipt['normal_build_log'])
    check(sha(log) == receipt['normal_build_log_sha256'] and sha(normal/'build-inputs.json') == receipt['normal_manifest_sha256'],
          'original normal manifest/log identity changed')
    check(prior._snapshot(normal) == receipt['normal_inputs_sha256'], 'original normal tree changed')
    sources = {name: sha(ROOT/name) for name in metadata['source_sha256']}
    sources['kernel/'+MODULE_PATH] = sha(ROOT/'kernel'/MODULE_PATH)
    sources['tools/build_bsp_diagnostic.py'] = sha(ROOT/'tools/build_bsp_diagnostic.py')
    check(sources == receipt['source_sha256'], 'production/diagnostic source identities changed')
    check(command_plan(normal, log, output) == receipt['recipe'], 'first-user checkpoint recipe changed')
    check([r['label'] for r in receipt['executed']] == list(COMMAND_ORDER)
          and all(r['returncode'] == 0 and r['command'] == receipt['recipe']['commands'][r['label']]
                  for r in receipt['executed']), 'first-user checkpoint execution sequence/command differs')
    check(_verify_overlay(normal, output) == receipt['kernel_overlay_sha256'], 'first-user checkpoint overlay identities changed')
    for original,target,patch in (('kernel/entry.asm','entry.asm',patch_entry),('kernel/services_run.asm','services_run.asm',patch_services_run),('kernel/sched/user_entry.asm','user_entry.asm',patch_user_entry_asm)):
        check((output/'private'/target).read_bytes() == patch((ROOT/original).read_bytes().decode('utf-8')).encode('utf-8'),
              'private source patch differs: '+target)
    original = (ROOT/'boot/efi_main.asm').read_bytes()
    check(original.count(prior.BANNER_BEFORE) == 1 and (output/'private/efi_main.asm').read_bytes()
          == original.replace(prior.BANNER_BEFORE, BANNER), 'private firmware changed beyond banner')
    check(_verify_report_layout(output) == receipt['report_layout'], 'first-user Report compiler layout changed')
    check(bundle == receipt['original_services_bundle'] and (esp/'SERVICES.BIN').read_bytes() == (normal/'esp/SERVICES.BIN').read_bytes(),
          'original service bundle changed')
    for name in prior.SERVICE_NAMES:
        check((output/'services'/name/'program.elf').read_bytes() == (normal/'services'/name/'program.elf').read_bytes(),
              'original service ELF changed: '+name)
    actual = prior._snapshot(output)
    actual.pop('first-user-checkpoint.json', None)
    check(actual == receipt['artifacts'], 'first-user checkpoint artifact inventory/hash differs')
    raw = materialize((output/'kernel.elf').read_bytes())
    image = (esp/'DONGOS.IMG').read_bytes()
    check(raw == (output/'kernel.bin').read_bytes() and raw != (normal/'kernel.bin').read_bytes()
          and unpack_image(image, hashlib.sha256(image).digest()) == raw
          and (output/'image_manifest.inc').read_text(encoding='utf-8') == manifest_text(image),
          'diagnostic kernel/image/manifest binding differs')
    digest = hashlib.sha256(image).digest()
    check(digest in (output/'image.obj').read_bytes() and digest in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(),
          'EFI verifier lost the intentional-stop image digest')
    definitions = [line for line in manifest_text(image).splitlines() if line.startswith('%define ')]
    for name in ('image.lst', 'efi_main.lst'):
        listing = (output/name).read_text(encoding='utf-8')
        check(all(len(re.findall(r'(?m)^\s*\d+\s+<1> '+re.escape(line)+r'\s*$',listing)) == 1 for line in definitions),
              'both actual EFI manifest consumers must use this image: '+name)
    check(BANNER+b'\r\n\0' in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(), 'read-only diagnostic banner missing')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal-source',type=Path,required=True)
    parser.add_argument('--normal-build-log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    esp = build_preflight(args.normal_source,args.normal_build_log,args.output)
    print('FIRST_USER_CHECKPOINT_BUILD_PASS',esp,flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise SystemExit('first-user checkpoint: '+str(error))

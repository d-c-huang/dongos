"""Execute actual boot-progress macros/helper and production RAM renderers."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_framebuffer_gate import fragment, production_include, source_census
from tools.gen_offsets import generate
from tools.build import find_tool
from tools.elf_symbols import read_elf_symbols

ROOT=Path(__file__).resolve().parents[1]
REGISTERS=('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def elf_bindings(path):
    raw=Path(path).read_bytes();at=struct.unpack_from('<Q',raw,40)[0]
    stride,count=struct.unpack_from('<HH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*stride) for i in range(count)]
    defined,undefined=set(),set()
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]];names=raw[strings[4]:strings[4]+strings[5]]
        for offset in range(section[4],section[4]+section[5],section[9]):
            name,_,_,index,_,_=struct.unpack_from('<IBBHQQ',raw,offset)
            if not name:continue
            value=names[name:names.index(0,name)].decode()
            (defined if index else undefined).add(value)
    return defined,undefined


def linked_symbol_contract(state,nasm,run,header):
    """Real whole-entry object + real macro callers; never execute this ELF."""
    linker=find_tool('ld.lld','LD_LLD');d=state/'linked-entry';d.mkdir()
    entry=d/'entry.o'
    run([nasm,*nasm_flags(nasm),'-f','elf64','-DRUNTIME_LEVEL=7','-I',str(ROOT/'include')+os.sep,
         '-I',str(state)+os.sep,'-I',str(ROOT)+os.sep,ROOT/'kernel/entry.asm','-o',entry],d,'assemble-actual-entry')
    macro=re.search(r'%macro HW_BOOT_ERROR 0\n.*?%endmacro',header,re.S)
    if not macro:raise AssertionError('one production HW_BOOT_ERROR macro')
    old='''%macro HW_BOOT_ERROR 0
%if RUNTIME_LEVEL >= 7
    pushfq
    cmp byte [rel boot_progress_failed],0
    jne %%recorded
    mov [rel boot_progress_error],rax
    mov byte [rel boot_progress_failed],1
%%recorded:
    popfq
    call boot_progress_draw
%endif
%endmacro'''
    reports=[]
    for variant,contents in [('production',header),('old-cross-tu-local-label',header[:macro.start()]+old+header[macro.end():])]:
        target=d/variant;target.mkdir();(target/'boot_progress.inc').write_text(contents,encoding='utf-8')
        objects=[entry]
        for caller in ('a','b'):
            asm=target/(caller+'.asm');asm.write_text('bits 64\ndefault rel\n%define RUNTIME_LEVEL 7\n%include "boot_progress.inc"\nsection .text\nglobal boot_probe_'+caller+'\nboot_probe_'+caller+':\nHW_BOOT_ERROR\nret\n',encoding='ascii')
            obj=target/(caller+'.o');run([nasm,*nasm_flags(nasm),'-f','elf64','-I',str(target)+os.sep,asm,'-o',obj],target,'assemble-caller-'+caller);objects.append(obj)
        definitions,references=set(),set()
        for obj in objects:
            defined,undefined=elf_bindings(obj);definitions|=defined;references|=undefined
        stubs=target/'stubs.asm';stubs.write_text('bits 64\nsection .text\n'+'\n'.join(
            'global '+name+'\n'+name+':\nret' for name in sorted(references-definitions))+'\n',encoding='ascii')
        stub=target/'stubs.o';run([nasm,*nasm_flags(nasm),'-f','elf64',stubs,'-o',stub],target,'assemble-unexecuted-extern-stubs')
        elf=target/'linked-entry.elf'
        run([linker,'-nostdlib','-e','kernel_entry','-Ttext=0xffffffff80000000','-o',elf,*objects,stub],target,'link-actual-entry')
        if variant=='production':
            symbols=read_elf_symbols(elf)
            for name in ('kernel_entry','boot_progress_draw','boot_progress_record_error','boot_probe_a','boot_probe_b'):
                if name not in symbols:raise AssertionError('missing actual linked entry symbol '+name)
            result=dict(variant=variant,reader_accepted=True,symbol_count=len(symbols),named_error_helper=symbols['boot_progress_record_error'])
        else:
            try:read_elf_symbols(elf)
            except ValueError as error:
                if 'ambiguous ELF symbol' not in str(error) or '.recorded' not in str(error):raise
                result=dict(variant=variant,reader_accepted=False,error=str(error))
            else:raise AssertionError('actual repeated macro-local label regression escaped unchanged ELF observer')
        reports.append(result);save(target/'symbols.json',result)
    save(d/'result.json',dict(results=reports,actual_entry_object=True,actual_macro_callers=2,
         existing_reader='tools.elf_symbols.read_elf_symbols',linked_elf_executed=False,externs_stubbed_for_link_only=True))


def native_bridge():
    out=['bits 64','default rel','%define RUNTIME_LEVEL 7','%define HW_BOOT_PROGRESS_OWNER 1',
         '%include "cpu.inc"','%include "runtime_display.inc"','%include "runtime_view.inc"',
         '%include "boot_progress.inc"','extern panic_saved_frames,panic_saved_frame_count',
         '%include "production.inc"','section .text','%include "helper.asm"','%include "user_boot_hooks.inc"','section .text',
         'global probe_invoke,probe_gate']
    # Only instrument the renderer entry's stack alignment. Its production
    # instructions remain a verbatim body under a private label.
    out+=['screen_draw:','pushfq','push rax','lea rax,[rsp+16]','and eax,15','cmp eax,8',
          'je .aligned','mov qword [rel probe_bad_align],1','.aligned:','pop rax','popfq','jmp production_screen_draw',
          'probe_gate:','lea rax,[rel framebuffer_gate]','ret']
    for phase in range(1,24):out+=[f'probe_stage_{phase}:',f'HW_BOOT_STAGE {phase}','ret']
    out+=['probe_error:','HW_BOOT_ERROR','ret','probe_disable:','HW_BOOT_DISABLE','ret']
    for phase in range(20,24):out+=[f'probe_mark_{phase}:',f'HW_BOOT_MARK {phase}','ret']
    out+=['probe_user_stage:','push rdi','mov edi,18','call user_boot_stage','pop rdi','ret',
          'probe_user_mark:','push rdi','mov edi,23','call user_boot_mark','pop rdi','ret','probe_invoke:',
          'pushfq']+['push '+r for r in REGISTERS]
    # Before CALL the stack is aligned. Save caller XMMs and use distinct
    # snapshots to inspect every GPR before the checker clobbers any of them.
    out+=['sub rsp,552','mov [rsp],rdi','mov [rsp+8],rsi','mov [rsp+16],rdx',
          'lea rax,[rel probe_targets]','mov rax,[rax+rdi*8]','mov [rsp+24],rax',
          'mov qword [rel probe_bad_align],0','mov [rsp+56],rsp',
          'mov rax,0x5b6c7d8e9fa0b1c2','mov [rsp+320],rax']
    for i in range(16):out+=[f'movdqu [rsp+{64+i*16}],xmm{i}',f'movdqu xmm{i},[rel probe_xmm_canary]']
    out+=['mov rax,[rsp+16]','and eax,0xcd5','pushfq','pop rcx','and rcx,~0xcd5','or rax,rcx',
          'push rax','popfq','pushfq','pop qword [rsp+32]']
    for i,r in enumerate(REGISTERS):
        out+=['mov rax,[rsp+8]' if r=='rax' else f'mov {r},0x{0x123456789abcdef0+i:016x}']
    out+=['call [rsp+24]']
    for i,r in enumerate(REGISTERS):out+=[f'mov [rsp+{336+i*8}],{r}']
    out+=['pushfq','pop qword [rsp+40]','cld','xor r10d,r10d']
    for i,r in enumerate(REGISTERS):
        out+=['mov rax,[rsp+8]' if r=='rax' else f'mov rax,0x{0x123456789abcdef0+i:016x}',
              f'cmp [rsp+{336+i*8}],rax','je $+6','or r10d,1']
    out+=['mov rax,[rsp+32]','xor rax,[rsp+40]','and eax,0xed5','jz .flags_ok','or r10d,2','.flags_ok:']
    for i in range(16):
        out+=[f'movdqa xmm0,xmm{i}' if i else 'movdqa xmm0,xmm0',
              'pcmpeqb xmm0,[rel probe_xmm_canary]','pmovmskb eax,xmm0','cmp eax,65535','je $+6','or r10d,4']
    out+=['cmp rsp,[rsp+56]','je .stack_ok','or r10d,8','.stack_ok:',
          'mov rax,0x5b6c7d8e9fa0b1c2','cmp [rsp+320],rax','je .sentinel_ok','or r10d,8','.sentinel_ok:',
          'cmp qword [rel probe_bad_align],0','je .align_ok','or r10d,16','.align_ok:']
    for i in range(16):out+=[f'movdqu xmm{i},[rsp+{64+i*16}]']
    # Saved caller RAX is the last pop; substitute the explicit oracle result.
    out+=['mov [rsp+664],r10','add rsp,552']+['pop '+r for r in reversed(REGISTERS)]
    out+=['popfq','ret','section .data','align 8','probe_bad_align:dq 0','probe_targets:dq boot_progress_draw']
    out+=['dq probe_stage_'+str(i) for i in range(1,24)]
    out+=['dq probe_error,probe_disable']
    out+=['dq probe_mark_'+str(i) for i in range(20,24)]
    out+=['dq probe_user_stage,probe_user_mark,user_boot_retire','section .rodata','align 16',
          'probe_xmm_canary:dq 0x0123456789abcdef,0xfedcba9876543210',
          '%ifidn __OUTPUT_FORMAT__,elf64','section .note.GNU-stack noalloc noexec nowrite','%endif']
    return '\n'.join(out)+'\n'


def ordered_hooks(overrides=None):
    files={'entry':'kernel/entry.asm','runtime':'kernel/runtime.asm','smp':'kernel/smp_runtime.asm',
           'services':'kernel/services_run.asm','boot':'kernel/sched/user_boot.asm','dg':'kernel/sched/user_boot.dg'}
    contents={name:(ROOT/path).read_text(encoding='utf-8') for name,path in files.items()}
    contents.update(overrides or {})
    entry,runtime,smp,services,boot,dg=(contents[n] for n in ('entry','runtime','smp','services','boot','dg'))
    arm=runtime.index('call dong_platform_arm');stop=runtime.index('call platform_timer_stop',arm)
    if re.search(r'HW_BOOT_STAGE',runtime[arm:stop]):raise AssertionError('rendering entered active scheduler timer interval')
    prepared=runtime.index('HW_BOOT_STAGE 2')
    if not(runtime.rfind('mov rdi, rax',0,prepared)<prepared<runtime.index('call dong_platform_init',prepared)):
        raise AssertionError('platform parameters/checkpoint ordering')
    at=services.index('call user_smp_boot_begin');prefix=services[:at].rsplit('HW_BOOT_STAGE 14',1)
    if len(prefix)!=2 or not re.fullmatch(r'\s*',prefix[1]):
        raise AssertionError('SMP preparation retired observation before preflight')
    at=services.index('call user_run');prefix=services[:at].rsplit('HW_BOOT_STAGE 14',1)
    if len(prefix)!=2 or not re.fullmatch(r'\s*HW_BOOT_DISABLE\s*',prefix[1]):
        raise AssertionError('legacy CPL3 transition must disable final diagnostic')
    if not (dg.index('user_boot_stage(15);')<dg.index('try device_host.preflight_discovery();')
            <dg.index('user_boot_stage(16);')<dg.index('var meta=resources.Block')):
        raise AssertionError('PCI/domain checkpoints do not bracket actual work')
    if not(dg.index('user_boot_stage(17);')<dg.index('id=0;while id<count')):
        raise AssertionError('CPU checkpoint follows actual CPU preparation')
    begin=boot.index('user_smp_boot_begin:');publication=boot.index('call dong_user_smp_boot_publish',begin)
    prepare=boot.index('call dong_user_smp_boot_prepare',begin);activate=boot.index('call user_smp_activate',begin)
    if not(prepare<boot.index('HW_BOOT_STAGE 18',begin)<activate<publication):
        raise AssertionError('BSP activation checkpoint ordering')
    if re.search(r'HW_BOOT_(?:STAGE|MARK|ERROR|DISABLE)',boot[boot.index('user_smp_try_handoff:'):begin]):
        raise AssertionError('AP handoff unexpectedly draws or retires BSP diagnostics')
    error=boot[boot.index('.publish_error:',publication):boot.index('.error:',publication)]
    if not re.fullmatch(r'\s*(?:;[^\n]*\n\s*)*HW_BOOT_ERROR\s+jmp user_smp_fail\s*',error.split(':',1)[1]):
        raise AssertionError('BSP publish failure must preserve original RAX before existing fail-stop')
    if not re.search(r'call dong_user_smp_boot_publish\s+test eax,eax\s+jnz \.publish_error',boot[publication:]):
        raise AssertionError('BSP publish error route bypasses actual error recorder')
    publish=dg[dg.index('fn publish()'):dg.index('unsafe extern "sysv64" fn user_boot_project')]
    until=publish.index('let until=arch.read_tsc()')
    if publish.index('user_boot_stage(19);')>=until or re.search(r'user_boot_stage\s*\(',publish[until:]):
        raise AssertionError('timed AP/domain publication contains framebuffer drawing')
    ordered=('user_boot_mark(20);','services.enable_smp()','user_boot_mark(21);','if user_boot_publish(',
             'user_boot_mark(22);','let projected=user_boot_project();','user_boot_mark(23);','user_boot_retire();','ud.unlock(d,0)')
    if any(value not in publish for value in ordered):
        raise AssertionError('required store-only publication checkpoint/retirement is absent')
    positions=[publish.index(value) for value in ordered]
    if positions!=sorted(positions) or publish.count('user_boot_retire();')!=1:
        raise AssertionError('store-only publication phases/retirement must precede user unlock')
    if smp.index('HW_BOOT_STAGE 6')>smp.index('call dong_smp_begin'):raise AssertionError('SMP START too late')
    if entry.index('call screen_draw')>entry.index('mov [rel boot_progress_view],r12'):
        raise AssertionError('view armed before first validated renderer')
    return dict(timer_interval_has_no_checkpoint=True,legacy_cpl3_final_stage_then_disable=True,
                smp_prepare_observation_retained=True,ap_deadline_updates_are_store_only=True,
                user_dispatch_retires_before_unlock=True,bsp_publish_preserves_original_error=True,
                fresh_view_after_first_validated_draw=True,source_census=source_census(entry))


class BootProgressTests(unittest.TestCase):
    def test_actual_macros_helper_renderer_pixels_abi_and_bad_sources(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native NASM/GCC required; zero skips')
        inputs=sorted({p for tree in ('kernel','include','lang/examples','lang/std','lang/dongc')
                       for p in (ROOT/tree).rglob('*') if p.is_file() and p.suffix in ('.dg','.asm','.inc','.py')}
                      |{Path(__file__),ROOT/'tests/boot_progress_probe.c',ROOT/'tests/test_framebuffer_gate.py',
                        ROOT/'lang/tests/test_dongc.py',ROOT/'tools/gen_offsets.py',ROOT/'tools/elf_symbols.py',ROOT/'tools/build.py',
                        ROOT/'tests/device_policy_probe.dg'})
        fingerprint=lambda:{p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
        before=fingerprint();state=ROOT/'build/test/boot-progress'/('run-'+uuid.uuid4().hex[:12]);state.mkdir(parents=True)
        save(state/'source-before.json',before);commands=[];results=[]
        def run(command,d,label,expected=0):
            command=list(map(str,command));r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
            receipt=dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
            save(d/(label+'.json'),receipt);commands.append(receipt)
            self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
        try:
            save(state/'hook-order.json',ordered_hooks())
            services=(ROOT/'kernel/services_run.asm').read_text(encoding='utf-8')
            dg=(ROOT/'kernel/sched/user_boot.dg').read_text(encoding='utf-8')
            boot=(ROOT/'kernel/sched/user_boot.asm').read_text(encoding='utf-8')
            bad_hooks={
                'old-early-retire':{'services':services.replace('HW_BOOT_STAGE 14\n    call user_smp_boot_begin','HW_BOOT_STAGE 14\n    HW_BOOT_DISABLE\n    call user_smp_boot_begin',1)},
                'draw-inside-ap-deadline':{'dg':dg.replace('user_boot_mark(21);','user_boot_stage(21);',1)},
                'omit-before-unlock-retire':{'dg':dg.replace('user_boot_retire();','',1)},
                'discard-publish-error':{'boot':boot.replace('    HW_BOOT_ERROR\n    jmp user_smp_fail','    jmp user_smp_fail',1)},
            }
            hook_rejections=[]
            for name,override in bad_hooks.items():
                with self.assertRaises(AssertionError):ordered_hooks(override)
                hook_rejections.append(name)
            save(state/'hook-bad-sources.json',dict(rejected=hook_rejections))
            compiled=compile_file(ROOT/'kernel/memory_probe.dg',roots=[ROOT/'kernel',ROOT/'lang/std',ROOT/'lang/examples'],mode='debug')
            layout=compiled.layout_manifest;save(state/'layout.json',layout)
            view=next(t for t in layout['types'] if t['full_name']=='boot.runtime_view.View')
            self.assertEqual(next(f for f in view['fields'] if f['name']=='display')['offset'],0)
            diagnostic=compile_file(ROOT/'tests/device_policy_probe.dg',roots=[ROOT/'tests',ROOT/'kernel',ROOT/'lang/std',ROOT/'lang/examples'],mode='debug')
            save(state/'device-policy-layout.json',diagnostic.layout_manifest)
            conflict=next(t for t in diagnostic.layout_manifest['types'] if t['full_name']=='boot.device_policy.Conflict')
            fields=('version','valid','error_code','slot','address','page','descriptor_index','kind','base','pages','attributes')
            self.assertEqual((88,8),(conflict['size'],conflict['alignment']))
            self.assertEqual([(name,8*i,'u64',8) for i,name in enumerate(fields)],
                [(f['name'],f['offset'],f['type'],f['size']) for f in conflict['fields']])
            for name,typ,alias in [
                    ('bootinfo_layout.inc','boot.abi.BootInfo',None),
                    ('memory_layout.inc','boot.memory_resources.Layout','MemoryLayout'),
                    ('memory_report.inc','boot.memory_startup.Report','MemoryReport'),
                    ('memory_resource.inc','boot.memory_resources.Resource','MemoryResource'),
                    ('runtime_display.inc','boot.runtime_view.Display','RuntimeDisplay'),
                    ('runtime_view.inc','boot.runtime_view.View','RuntimeView'),
                    ('control_state.inc','boot.preflight.State','ControlState'),
                    ('control_plan.inc','boot.preflight.Plan','ControlPlan'),
                    ('activation_report.inc','boot.activation.Report','ActivationReport'),
                    ('mutation_report.inc','boot.live_memory.Report','MutationReport'),
                    ('hardening_report.inc','cpu.hardening.Report','HardeningReport'),
                    ('object_memory_report.inc','boot.object_memory.Report','ObjectMemoryReport'),
                    ('acpi_report.inc','boot.acpi_startup.Report','AcpiReport')]:
                (state/name).write_text(generate(layout,typ,alias),encoding='ascii')
            entry=(ROOT/'kernel/entry.asm').read_text(encoding='utf-8');header=(ROOT/'include/boot_progress.inc').read_text(encoding='utf-8')
            helper=(ROOT/'kernel/boot_progress.asm').read_text(encoding='utf-8')
            linked_symbol_contract(state,nasm,run,header)
            native=production_include(entry)+'\nsection .bss\n'+fragment(entry,'BOOT_PROGRESS_STORAGE')
            self.assertEqual(native.count('\nscreen_draw:'),1)
            native=native.replace('\nscreen_draw:','\nproduction_screen_draw:',1)
            boot=(ROOT/'kernel/sched/user_boot.asm').read_text(encoding='utf-8')
            hooks=boot[boot.index('user_boot_stage:'):boot.index('user_entry_mapped:')]
            self.assertIn('HW_BOOT_MARK dil',hooks);self.assertIn('HW_BOOT_DISABLE',hooks)
            variants={'production':(header,helper,native,hooks)}
            trunc='mov [rel boot_progress_error],rax';disable='mov qword [rel boot_progress_view],0'
            self.assertEqual(helper.count(trunc),1);self.assertEqual(header.count(disable),1)
            variants['truncate-first-error']=(header,helper.replace(trunc,'mov [rel boot_progress_error],eax',1),native,hooks)
            variants['omit-disable']=(header.replace(disable,'; actual bad source does not retire boot framebuffer access',1),helper,native,hooks)
            wrong_offset='BOOT_MMIO_LINE boot_progress_kind_label,260,[rel boot_progress_mmio + BootProgressMmio.kind]'
            truncate_values='    mov rax,%3\n'
            truncate_valid='cmp qword [rel boot_progress_mmio + BootProgressMmio.valid],1'
            for needle in (wrong_offset,truncate_values,truncate_valid):self.assertEqual(1,native.count(needle))
            variants['mmio-wrong-kind-offset']=(header,helper,native.replace(wrong_offset,wrong_offset.replace('BootProgressMmio.kind','BootProgressMmio.base'),1),hooks)
            variants['mmio-truncate-values']=(header,helper,native.replace(truncate_values,'    mov eax,%3\n',1),hooks)
            variants['mmio-truncate-valid']=(header,helper,native.replace(truncate_valid,truncate_valid.replace('qword','dword'),1),hooks)
            mark=re.search(r'%macro HW_BOOT_MARK 1\n.*?%endmacro',header,re.S)
            self.assertIsNotNone(mark)
            marked_draw=header[:mark.start()]+'%macro HW_BOOT_MARK 1\n    HW_BOOT_STAGE %1\n%endmacro'+header[mark.end():]
            variants['mark-draws-in-timed-window']=(marked_draw,helper,native,hooks)
            variants['omit-retire-wrapper']=(header,helper,native,hooks.replace('    HW_BOOT_DISABLE','    ; actual bad wrapper skips retirement',1))
            for name,(selected_header,selected_helper,selected_native,selected_hooks) in variants.items():
                d=state/name;d.mkdir();(d/'production.inc').write_text(selected_native,encoding='utf-8')
                (d/'boot_progress.inc').write_text(selected_header,encoding='utf-8');(d/'helper.asm').write_text(selected_helper,encoding='utf-8');(d/'user_boot_hooks.inc').write_text(selected_hooks,encoding='utf-8')
                asm=d/'probe.asm';asm.write_text(native_bridge(),encoding='ascii');objects={}
                for fmt in ('elf64','win64'):
                    obj=d/(fmt+'.o');run([nasm,*nasm_flags(nasm),'-f',fmt,'-I',str(d)+os.sep,
                        '-I',str(state)+os.sep,'-I',str(ROOT/'include')+os.sep,asm,'-o',obj],d,'assemble-'+fmt);objects[fmt]=obj
                symbols=read_elf_symbols(objects['elf64'])
                self.assertEqual(conflict['size'],symbols['BootProgressMmio_size'])
                for field in conflict['fields']:
                    asm_name='error' if field['name']=='error_code' else field['name']
                    self.assertEqual(field['offset'],symbols['BootProgressMmio.'+asm_name])
                for optimization in ('O0','O2'):
                    exe=d/(optimization+('.exe' if os.name=='nt' else ''))
                    run([cc,'-std=c11','-'+optimization,'-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',
                         '-DRUNTIME_VIEW_BYTES='+str(view['size']),'-DMMIO_CONTEXT_BYTES='+str(conflict['size']),*([] if os.name=='nt' else ['-no-pie']),
                         ROOT/'tests/boot_progress_probe.c',objects['win64' if os.name=='nt' else 'elf64'],'-o',exe],d,'link-'+optimization)
                    r=run([exe],d,'native-'+optimization,0 if name=='production' else 1)
                    self.assertIn('returned normally',r.stdout+r.stderr)
                    self.assertIn('boot progress oracle passed' if name=='production' else 'boot progress oracle failed',r.stdout+r.stderr)
                    results.append(dict(variant=name,optimization=optimization,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            self.assertEqual(before,fingerprint(),'production/test source changed during native run')
        finally:
            save(state/'source-after.json',fingerprint());save(state/'commands.json',commands)
            save(state/'result.json',dict(source_stable=before==fingerprint(),results=results,actual_renderer_and_helper=True,
                 real_macros_executed=True,actual_user_boot_callbacks_executed=True,mark_only_and_retirement_verified=True,assembled_formats=['elf64','win64'],vm_executed=False,physical_devices_accessed=False))
        print('BOOT_PROGRESS_EVIDENCE '+str(state))


if __name__=='__main__':unittest.main(verbosity=2)

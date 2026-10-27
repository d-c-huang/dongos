"""Execute the actual first-entry capture against independent native inputs.

Only getter boundaries and owned input storage are supplied by the fixture.
The production capture body and its actual shared declarations are compiled.
Bad-body variants must fail C assertions, not panic or crash.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_service_ipc_cancellation import block

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('version', 'done', 'error_code', 'reason', 'cpu', 'cpus', 'vector',
          'operation', 'rip', 'rsp', 'frame_root', 'raw_root', 'mode', 'slot',
          'token', 'captured', 'syscalls', 'user_entries', 'header_error',
          'bridge_stage', 'first_error', 'domain_failed', 'bridge_failed', 'frame_kind')
SUPPLIERS = ('kernel/sched/user_boot.dg', 'kernel/sched/user_domain.dg',
             'kernel/sched/user_bridge.dg', 'kernel/sched/user_entry_plan.dg',
             'kernel/user/abi.dg')
MUTATIONS = {
    'repeat': ('if STATE.version!=0{return &STATE;}', 'if false{return &STATE;}'),
    'ignore-capture': ('if *((frame as *const u64)+word)!=*(((*c).capture as *const u64)+word){STATE.error_code=INVALID;}', ''),
    'ignore-raw-root': ('||raw_root!=(*d).kernel_root', ''),
    'ignore-process-token': ('(*p).token!=STATE.token||', ''),
    'wrong-rip': ('STATE.rip=(*f).rip;', 'STATE.rip=(*f).rsp;'),
    'ignore-first-error': ('if atomic_load(&bridge.FAILURES[cpu].published)==1', 'if false'),
    'false-failure-frame': ('selected=(*c).returned;STATE.frame_kind=2;', 'selected=(*c).returned;STATE.frame_kind=1;'),
    'missing-done': ('compiler_fence();STATE.done=1;', 'compiler_fence();'),
}


def fixtures():
    sources = {p: (ROOT/p).read_text(encoding='utf-8') for p in SUPPLIERS}
    domain = sources[SUPPLIERS[1]]
    bridge = sources[SUPPLIERS[2]]
    # Engine is only an opaque pointee in Domain; capture never reads it.
    result = {
        'sched/multicore.dg': 'module sched.multicore;pub struct Engine{pub opaque:u64}\n',
        'sched/user_boot.dg': 'module sched.user_boot;\n'+block(sources[SUPPLIERS[0]], 'pub struct Report{')+'\npub extern "sysv64" ("checkpoint_boot") fn report()*const Report;\n',
        'sched/user_domain.dg': 'module sched.user_domain;import sched.multicore as q;pub const KERNEL:u64=4;\n'+'\n'.join(block(domain, 'pub struct '+name+'{') for name in ('Seen', 'Process', 'Cpu', 'Domain'))+'\n',
        'sched/user_entry_plan.dg': 'module sched.user_entry_plan;\n'+'\n'.join(block(sources[SUPPLIERS[3]], 'pub struct '+name+'{') for name in ('Cpu', 'Metrics'))+'\n',
        'user/abi.dg': 'module user.abi;\n'+block(sources[SUPPLIERS[4]], 'pub struct Frame {')+'\n',
    }
    empty = block(bridge, 'const EMPTY_FAILURE:Failure=')+';'
    globals_ = '\n'.join(re.search(r'^pub var '+name+r':.*;$', bridge, re.M).group(0) for name in ('FAILURES', 'PROGRESS'))
    result['sched/user_bridge.dg'] = ('module sched.user_bridge;import sched.user_domain as ud;\n'
        +'\n'.join(block(bridge, prefix) for prefix in ('pub struct Pending{', 'pub struct Bridge{', 'pub struct Progress{', 'pub struct Failure{'))
        +'\n'+empty+'\n'+globals_+'\npub extern "sysv64" ("checkpoint_bridge") fn pointer()*Bridge;\n'
        +'export("checkpoint_progress_pointer") fn trace()*Progress{unsafe{return &PROGRESS[0];}}\n'
        +'export("checkpoint_failures_pointer") fn failures()*Failure{unsafe{return &FAILURES[0];}}\n')
    return result


class FirstUserCheckpointTests(unittest.TestCase):
    def test_actual_capture_and_bad_bodies(self):
        out = ROOT/'build/test/first-user-checkpoint'/('run-'+uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        paths = [ROOT/'kernel/boot/first_user_checkpoint.dg', ROOT/'tests/first_user_checkpoint_probe.c', Path(__file__), *(ROOT/p for p in SUPPLIERS)]
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        original = paths[0].read_text(encoding='utf-8')
        fixture_sources = fixtures()
        results = []
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'real native toolchain required; no skip')
        for kind in ('normal', *MUTATIONS):
            for mode in ('debug', 'release'):
                d = out/kind/mode
                d.mkdir(parents=True)
                source = original
                if kind != 'normal':
                    old, new = MUTATIONS[kind]
                    self.assertEqual(1, source.count(old), kind)
                    source = source.replace(old, new)
                graph = dict(fixture_sources)
                graph['boot/first_user_checkpoint.dg'] = source+'\nexport("checkpoint_reset") fn reset()void{unsafe{STATE=EMPTY;}}\n'
                for name, body in graph.items():
                    target = d/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(body, encoding='utf-8')
                c = compile_file(d/'boot/first_user_checkpoint.dg', roots=[d], mode=mode)
                types = {t['full_name']: t for t in c.layout_manifest['types']}
                expected = {'boot.first_user_checkpoint.Report': 192, 'sched.user_boot.Report': 80,
                            'sched.user_domain.Domain': 120, 'sched.user_domain.Cpu': 120,
                            'sched.user_domain.Process': 56, 'sched.user_bridge.Bridge': 64,
                            'sched.user_bridge.Progress': 48, 'sched.user_bridge.Failure': 224,
                            'sched.user_entry_plan.Cpu': 256, 'sched.user_entry_plan.Metrics': 192,
                            'user.abi.Frame': 200}
                for name, size in expected.items():
                    self.assertEqual(size, types[name]['size'], name)
                    self.assertEqual(8, types[name]['alignment'], name)
                self.assertEqual(list(FIELDS), [f['name'] for f in types['boot.first_user_checkpoint.Report']['fields']])
                self.assertEqual(list(range(0, 192, 8)), [f['offset'] for f in types['boot.first_user_checkpoint.Report']['fields']])
                for name, fields in {'sched.user_entry_plan.Cpu': {'logical_id': 80, 'kernel_xstate': 168, 'ready': 200, 'last_error': 208, 'raw_frame': 224}, 'sched.user_entry_plan.Metrics': {'user_entries': 24}, 'user.abi.Frame': {'rax': 112, 'rip': 120, 'rsp': 136, 'cr3': 144}}.items():
                    offsets = {f['name']: f['offset'] for f in types[name]['fields']}
                    for field, offset in fields.items():
                        self.assertEqual(offset, offsets[field], name+'.'+field)
                self.assertIsNone(re.search(r'^\s*(?:in|out|rdmsr|wrmsr|invlpg|cli|sti|hlt)\b', c.assembly, re.M))
                symbol = '__dg_m'+'boot.first_user_checkpoint'.encode().hex()+'_g'+'STATE'.encode().hex()
                allocation = re.compile(r'(?m)^\$?'+re.escape(symbol)+r':\r?\n\s+resb 192\b')
                self.assertEqual(1, len(allocation.findall(c.assembly.split('section .bss', 1)[1])))
                asm_body = allocation.sub('global first_checkpoint_canary_low\nfirst_checkpoint_canary_low:\n    resq 4\n'+symbol+':\n    resb 192\nglobal first_checkpoint_canary_high\nfirst_checkpoint_canary_high:\n    resq 4', c.assembly)
                asm = d/'probe.asm'
                asm.write_text(asm_body, encoding='utf-8')
                (d/'layout.json').write_text(json.dumps(c.layout_manifest, indent=2)+'\n', encoding='utf-8')

                def command(args, label):
                    args = list(map(str, args))
                    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=90)
                    (d/(label+'.json')).write_text(json.dumps(dict(args=args, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr), indent=2)+'\n', encoding='utf-8')
                    return r

                obj = d/'probe.o'
                for fmt in ('elf64', 'win64'):
                    target = obj if fmt == ('win64' if os.name == 'nt' else 'elf64') else d/(fmt+'.o')
                    r = command([nasm, '-f', fmt, *nasm_flags(nasm), '-o', target, asm], 'assemble-'+fmt)
                    self.assertEqual(0, r.returncode, r.stderr)
                for opt in ('-O0', '-O2') if kind == 'normal' else ('-O2',):
                    exe = d/('probe'+opt+('.exe' if os.name == 'nt' else ''))
                    r = command([cc, '-std=c11', opt, '-Wall', '-Wextra', '-Werror', *(['-mno-sse'] if os.name == 'nt' else ['-no-pie']), paths[1], obj, '-o', exe], 'link'+opt)
                    self.assertEqual(0, r.returncode, r.stderr)
                    r = command([exe], 'native'+opt)
                    if kind == 'normal':
                        self.assertEqual(0, r.returncode, r.stdout+r.stderr)
                        self.assertRegex(r.stdout, r'FIRST_USER_NATIVE_OK cases=\d+ checks=\d+')
                    else:
                        self.assertEqual(1, r.returncode, r.stdout+r.stderr)
                        self.assertIn('FIRST_USER_ASSERT', r.stderr)
                    self.assertNotIn('unexpected panic', r.stderr)
                    results.append(dict(kind=kind, mode=mode, opt=opt, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr))
        self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        (out/'result.json').write_text(json.dumps(dict(passed=True, source_stable=True, skips=0, sources=before, results=results), indent=2)+'\n', encoding='utf-8')

    def test_exact_private_hooks_and_renderer(self):
        # Lazy import keeps native capture independent of builder imports.
        from tools import build_first_user_checkpoint as builder
        names = ('tools/build_first_user_checkpoint.py', 'kernel/sched/user_boot.dg',
                 'kernel/sched/user_bridge.dg', 'kernel/sched/user_entry.asm',
                 'kernel/entry.asm', 'kernel/services_run.asm')
        before = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
        boot, bridge, entry_asm, entry, services = [(ROOT/name).read_text(encoding='utf-8') for name in names[1:]]
        retained = builder.patch_user_boot(boot)
        begin = boot.index(' user_boot_mark(23);user_boot_retire();')
        end = begin+len(' user_boot_mark(23);user_boot_retire();')
        self.assertTrue(retained.startswith(boot[:begin]))
        self.assertTrue(retained.endswith(boot[end:]))
        patch = retained[begin:len(retained)-len(boot[end:])]
        self.assertIn('(*d).engine==null||(*d).processes==null||(*(*d).engine).count!=1', patch)
        self.assertIn('(*(*d).engine).threads[5].affinity!=1', patch)
        self.assertIn('(*((*d).processes+5)).token==0', patch)
        self.assertIn('while initial_slot<16', patch)
        self.assertIn('initial_slot!=5&&(*((*d).processes+initial_slot)).token!=0', patch)
        self.assertEqual(2, patch.count('return 0x060b_0020;'))
        self.assertIn('user_boot_mark(23);', patch)
        self.assertNotIn('user_boot_retire();', patch)
        self.assertEqual(1, boot.count('let unlocked=ud.unlock(d,0);'))
        self.assertEqual(1, retained.count('let unlocked=ud.unlock(d,0);'))

        captured = builder.patch_user_bridge(bridge)
        hook = ' if cpu==0{first_user_checkpoint_stop(cpu,frame,event,0,0);}\n'
        declaration = 'unsafe extern "sysv64" fn first_user_checkpoint_stop(cpu:usize,frame:u64,event:u64,reason:u64,raw_root:u64)void;\n'
        self.assertEqual(1, captured.count(hook))
        self.assertEqual(bridge, captured.replace(declaration, '').replace(hook, ''))
        ordered = ['let d=try checked(cpu);', 'try ud.begin_entry(d,cpu);',
                   'user_bridge_copy((*c).capture,frame,200);', 'try ud.complete_entry(d,cpu);',
                   'user_bridge_restore((*header).kernel_xstate);', hook.strip(),
                   'stage(cpu,DEADLINE);']
        capture = block(captured, 'unsafe fn capture(')
        positions = [capture.index(part) for part in ordered]
        self.assertEqual(sorted(positions), positions)

        failed = builder.patch_user_entry_asm(entry_asm)
        insertion = '''    cmp qword [gs:UserSmpCpu.logical_id],0
    jne user_smp_fail_untrusted
    mov r8,cr3
    call user_smp_to_kernel
    mov rsp,[gs:UserCpu.kernel_stack]
    sub rsp,8
    xor edi,edi
    xor esi,esi
    mov rdx,[gs:UserEntryCpu.event]
    mov ecx,1
    jmp first_user_checkpoint_stop
'''
        self.assertEqual(1, failed.count(insertion))
        self.assertEqual(entry_asm, failed.replace('extern first_user_checkpoint_stop\n', '').replace(insertion, ''))
        anchor = '    mov qword [rax+1024+UserEntryMetrics.failed],1\n'
        self.assertIn(anchor+insertion+'user_smp_fail_untrusted:', failed)
        self.assertEqual(entry_asm[entry_asm.index('user_smp_fail_untrusted:'):], failed[failed.index('user_smp_fail_untrusted:'):])

        painted = builder.patch_entry(entry)
        stop = painted[painted.index('first_user_checkpoint_stop:'):]
        saved = ['mov r12,rdi', 'mov r13,rsi', 'mov r14,rdx', 'mov r15,rcx', 'mov rbx,r8']
        for line in saved:
            self.assertLess(stop.index(line), stop.index('call sched_xstate_restore'))
        self.assertNotIn('mov rsp,', stop)
        self.assertIn('test r15,r15\n    jnz .raw_root_saved\n    mov rbx,cr3', stop)
        self.assertIn('mov rdi,r12\n    mov rsi,r13\n    mov rdx,r14\n    mov rcx,r15\n    mov r8,rbx\n    call dong_first_user_checkpoint_run\n    HW_BOOT_STAGE 24', stop)
        self.assertIn('cli\n.stop:\n    hlt\n    jmp .stop', stop)
        self.assertEqual(FIELDS, builder.FIELDS)
        self.assertEqual(192, builder.REPORT_SIZE)
        self.assertEqual(15, len(builder.ROWS))
        for label, field in builder.ROWS:
            self.assertLessEqual(len(label), 13)
            self.assertIn(field, FIELDS)
        self.assertEqual(238, 56+13*14)
        self.assertEqual(470, 120+14*24+14)
        self.assertIn('mov edi,238', painted)
        self.assertIn('cmp qword [rbx],1', painted)
        self.assertIn('cmp qword [rbx + 8],1', painted)
        self.assertEqual(services, builder.patch_services_run(services))
        self.assertEqual(9, len(builder.COMMAND_ORDER))
        self.assertIn('user_entry.o', builder.REPLACED_OBJECTS)
        self.assertNotIn('user_boot.o', builder.REPLACED_OBJECTS)
        self.assertNotIn('ap_checkpoint_park', failed+retained+captured)
        for function, source, anchor in (
            (builder.patch_user_boot, boot, ' user_boot_mark(23);user_boot_retire();'),
            (builder.patch_user_bridge, bridge, 'user_bridge_restore((*header).kernel_xstate);\n stage(cpu,DEADLINE);'),
            (builder.patch_user_entry_asm, entry_asm, '    mov qword [rax+1024+UserEntryMetrics.failed],1\nuser_smp_fail_untrusted:'),
            (builder.patch_entry, entry, '.progress_regular:\n'),
        ):
            with self.assertRaises(ValueError):
                function(source.replace(anchor, ''))
            with self.assertRaises(ValueError):
                function(source+anchor)
        self.assertEqual(before, {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names})


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Actual failure-only producer with independent read-only native inputs."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import unittest
import uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_first_user_checkpoint import fixtures, SUPPLIERS

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('version','done','error_code','cpu','cpus','failure_cpu','failure_code','failure_detail',
          'entry','event','stage','domain_failed','bridge_failed','lock','owner','online','mode','slot',
          'token','captured','syscalls','user_entries','header_error','operation','rip','rsp','frame_root',
          'raw_root','pcid','calls','failure_mask','frame_kind')
MUTATIONS = {
    'repeat': ('if STATE.version!=0{return &STATE;}', 'if false{return &STATE;}'),
    'ignore-published': ('if atomic_load(&(*f).published)==1', 'if atomic_load(&(*f).published)!=0'),
    'last-error': ('if STATE.failure_cpu==16{', 'if true{'),
    'wrong-detail': ('STATE.failure_detail=(*f).detail_code;', 'STATE.failure_detail=(*f).error_code;'),
    'wrong-frame-kind': ('STATE.frame_kind=2;', 'STATE.frame_kind=1;'),
    'missing-done': ('compiler_fence();STATE.done=1;', 'compiler_fence();'),
    'wrong-rip': ('STATE.rip=(*f).rip;', 'STATE.rip=(*f).rsp;'),
    'ignore-fallback-event': ('STATE.event=(*h).event;', 'STATE.event=bridge.PROGRESS[0].vector;'),
    'ignore-mask': ('STATE.failure_mask|=1<<id as u64;', ''),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class UserRuntimeTests(unittest.TestCase):
    def test_actual_failure_status_and_bad_bodies(self):
        out = ROOT/'build/test/user-runtime'/('run-'+uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        paths = [ROOT/'kernel/boot/user_runtime_status.dg',ROOT/'tests/user_runtime_probe.c',Path(__file__),ROOT/'tests/test_first_user_checkpoint.py',*(ROOT/n for n in SUPPLIERS)]
        before = {str(p):sha(p) for p in paths}
        original = paths[0].read_text(encoding='utf-8')
        self.assertTrue(original.rstrip().endswith('compiler_fence();STATE.done=1;return &STATE;\n}}'))
        nasm, cc = tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'real native tools required; no skip')
        results = []
        for kind in ('normal',*MUTATIONS):
            for mode in ('debug','release'):
                d = out/kind/mode
                d.mkdir(parents=True)
                source = original
                if kind != 'normal':
                    old,new = MUTATIONS[kind]
                    self.assertEqual(1,source.count(old),kind)
                    source=source.replace(old,new)
                graph = fixtures()
                graph['boot/user_runtime_status.dg'] = source+'\nexport("checkpoint_reset") fn reset()void{unsafe{STATE=EMPTY;}}\n'
                for name,body in graph.items():
                    target=d/name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text(body,encoding='utf-8')
                c=compile_file(d/'boot/user_runtime_status.dg',roots=[d],mode=mode)
                types={t['full_name']:t for t in c.layout_manifest['types']}
                for name,size in {'boot.user_runtime_status.Report':256,'sched.user_boot.Report':80,
                    'sched.user_domain.Domain':120,'sched.user_domain.Cpu':120,'sched.user_domain.Process':56,
                    'sched.user_bridge.Bridge':64,'sched.user_bridge.Progress':48,'sched.user_bridge.Failure':224,
                    'sched.user_entry_plan.Cpu':256,'sched.user_entry_plan.Metrics':192,'user.abi.Frame':200}.items():
                    self.assertEqual(size,types[name]['size'],name)
                    self.assertEqual(8,types[name]['alignment'],name)
                report=types['boot.user_runtime_status.Report']
                self.assertEqual([(n,i*8,8) for i,n in enumerate(FIELDS)],[(f['name'],f['offset'],f['size']) for f in report['fields']])
                self.assertIsNone(re.search(r'^\s*(?:in|out|rdmsr|wrmsr|invlpg|cli|sti|hlt)\b',c.assembly,re.M))
                symbol='__dg_m'+'boot.user_runtime_status'.encode().hex()+'_g'+'STATE'.encode().hex()
                pattern=re.compile(r'(?m)^\$?'+re.escape(symbol)+r':\r?\n\s+resb 256\b')
                self.assertEqual(1,len(pattern.findall(c.assembly.split('section .bss',1)[1])))
                body=pattern.sub('global runtime_canary_low\nruntime_canary_low:\n    resq 4\n'+symbol+':\n    resb 256\nglobal runtime_canary_high\nruntime_canary_high:\n    resq 4',c.assembly)
                asm=d/'probe.asm';asm.write_text(body,encoding='utf-8')
                (d/'layout.json').write_text(json.dumps(c.layout_manifest,indent=2)+'\n',encoding='utf-8')
                def command(args,label):
                    args=list(map(str,args));r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=90)
                    (d/(label+'.json')).write_text(json.dumps(dict(args=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8')
                    return r
                obj=d/'probe.o'
                for fmt in ('elf64','win64'):
                    target=obj if fmt==('win64' if os.name=='nt' else 'elf64') else d/(fmt+'.o')
                    r=command([nasm,'-f',fmt,*nasm_flags(nasm),'-o',target,asm],'assemble-'+fmt)
                    self.assertEqual(0,r.returncode,r.stderr)
                for opt in ('-O0','-O2') if kind=='normal' else ('-O2',):
                    exe=d/('probe'+opt+('.exe' if os.name=='nt' else ''))
                    r=command([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror',*(['-mno-sse'] if os.name=='nt' else ['-no-pie']),paths[1],obj,'-o',exe],'link'+opt)
                    self.assertEqual(0,r.returncode,r.stderr)
                    r=command([exe],'native'+opt)
                    if kind=='normal':
                        self.assertEqual(0,r.returncode,r.stdout+r.stderr)
                        self.assertRegex(r.stdout,r'USER_RUNTIME_NATIVE_OK cases=\d+ checks=\d+')
                    else:
                        self.assertEqual(1,r.returncode,r.stdout+r.stderr)
                        self.assertIn('USER_RUNTIME_ASSERT',r.stderr)
                    self.assertNotIn('unexpected panic',r.stderr)
                    results.append(dict(kind=kind,mode=mode,opt=opt,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        self.assertEqual(before,{str(p):sha(p) for p in paths})
        (out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before,results=results),indent=2)+'\n',encoding='utf-8')

    def test_sole_init_bsp_f4_returns_same_user(self):
        out=ROOT/'build/test/user-runtime-f4'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        paths=[*(p for p in (ROOT/'kernel').rglob('*') if p.is_file()),*(ROOT/'include').glob('*.inc'),ROOT/'tests/user_current_entry_probe.dg',ROOT/'tests/user_current_entry_probe.c',Path(__file__)]
        before={str(p):sha(p) for p in paths}
        original=(ROOT/'tests/user_current_entry_probe.c').read_text(encoding='utf-8')
        eoi='U ABI user_bridge_eoi(U who,U vector){C(who==cpu&&(vector==0x40||vector==0xf4||vector==0xff));return 0;}'
        self.assertEqual(1,original.count(eoi))
        original=original.replace(eoi,'static U runtime_eois;\n'+eoi.replace('return 0;','runtime_eois++;return 0;'))
        self.assertEqual(1,original.count('int main(void)'))
        original=original.replace('int main(void)','int prior_entry_main(void)')+'''
U ABI user_bridge_service_policy(U slot,U vector,U frame){(void)slot;(void)vector;(void)frame;return 0;}
int main(void){
 setup();cpu=0;C(!ue_lock(0));admit(5,1);C(!ue_unlock(0));
 memset(xstates[5],0xa6,1024);start(0,5);C(timer[0]==0&&service_calls==0&&runtime_eois==0);
 U token=d->cpus[0].token,root=d->cpus[0].root,returned=d->cpus[0].returned,return_xstate=d->cpus[0].return_xstate;
 Frame interrupted=*(Frame*)(uintptr_t)returned;unsigned char expected_xstate[1024];memcpy(expected_xstate,hardware[0],1024);
 C(token&&d->cpus[0].slot==5&&d->cpus[0].mode==2&&roots[0]==root);
 roots[0]=0x100000;U next=dong_user_smp_event(0,(U)(uintptr_t)&interrupted,0xf4);
 C(next==returned&&runtime_eois==1&&service_calls==0&&timer[0]==0&&!d->failed);
 C(d->cpus[0].token==token&&d->cpus[0].slot==5&&d->cpus[0].root==root&&d->cpus[0].mode==6);
 C(d->cpus[0].returned==returned&&d->cpus[0].return_xstate==return_xstate);
 C(!memcmp(&interrupted,(void*)(uintptr_t)returned,200)&&!memcmp(&interrupted,&frames[5],200));
 C(!memcmp(expected_xstate,xstates[5],1024)&&!memcmp(expected_xstate,(void*)(uintptr_t)return_xstate,1024));
 C(dong_user_smp_return(0)==1&&d->cpus[0].mode==2&&roots[0]==root);
 C(d->cpus[0].token==token&&runtime_eois==1&&service_calls==0&&!ue_audit()&&!d->failed);
 printf("USER_RUNTIME_F4_OK checks=%lu EOI=1 calls=0 same-token-frame-xstate\\n",(unsigned long)checks);return 0;
}
'''
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
        evidence=[]
        for mode in ('debug','release'):
            for kind in ('normal','missing-eoi','duplicate-eoi'):
                d=out/mode/kind;shutil.copytree(ROOT/'kernel',d/'kernel');shutil.copytree(ROOT/'include',d/'include')
                if kind!='normal':
                    path=d/'kernel/sched/user_bridge.dg';source=path.read_text(encoding='utf-8')
                    anchor='else if user_bridge_eoi(cpu as u64,event)!=0{return error.Held;}'
                    self.assertEqual(2,source.count(anchor))
                    replacement='else if false{return error.Held;}' if kind=='missing-eoi' else 'else if user_bridge_eoi(cpu as u64,event)!=0||user_bridge_eoi(cpu as u64,event)!=0{return error.Held;}'
                    path.write_text(source.replace(anchor,replacement,1),encoding='utf-8')
                (d/'probe.c').write_text(original,encoding='utf-8')
                c=compile_file(ROOT/'tests/user_current_entry_probe.dg',roots=[ROOT/'tests',d/'kernel'],mode=mode)
                self.assertNotRegex(c.assembly.lower(),r'\b(?:xmm\d+|ymm\d+|zmm\d+|cli|sti|invpcid|wrmsr|rdmsr)\b')
                (d/'probe.asm').write_text(c.assembly,encoding='utf-8')
                def command(args,label):
                    args=list(map(str,args));r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=90)
                    (d/(label+'.json')).write_text(json.dumps(dict(args=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8');return r
                objects=[]
                for name,source in [('dong',d/'probe.asm'),('entry',d/'kernel/sched/user_entry.asm'),('legacy',d/'kernel/sched/user_legacy.asm')]:
                    for fmt in ('elf64','win64'):
                        obj=d/(name+'-'+fmt+'.o')
                        r=command([nasm,'-f',fmt,*nasm_flags(nasm),'-I',str(d/'include')+os.sep,source,'-o',obj],'assemble-'+name+'-'+fmt)
                        self.assertEqual(0,r.returncode,r.stderr)
                        if fmt==('win64' if os.name=='nt' else 'elf64'):objects.append(obj)
                for opt in ('-O0','-O2') if kind=='normal' else ('-O2',):
                    exe=d/('probe'+opt+('.exe' if os.name=='nt' else ''))
                    r=command([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror',*(['-no-pie'] if os.name!='nt' else []),d/'probe.c',*objects,'-o',exe],'link'+opt)
                    self.assertEqual(0,r.returncode,r.stderr)
                    r=command([exe],'native'+opt)
                    self.assertEqual(0 if kind=='normal' else 1,r.returncode,r.stdout+r.stderr)
                    self.assertIn('USER_RUNTIME_F4_OK' if kind=='normal' else 'user CPL3 current-source oracle line',r.stdout if kind=='normal' else r.stderr)
                    self.assertNotIn('Dong panic',r.stderr)
                    evidence.append(dict(kind=kind,mode=mode,opt=opt,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        self.assertEqual(before,{str(p):sha(p) for p in paths})
        (out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before,results=evidence),indent=2)+'\n',encoding='utf-8')

    def test_exact_failure_only_private_hooks(self):
        from tools import build_user_runtime as builder
        names=('tools/build_user_runtime.py','kernel/entry.asm','kernel/sched/user_entry.asm','kernel/sched/user_boot.asm','kernel/sched/user_boot.dg','kernel/sched/user_bridge.dg')
        before={name:sha(ROOT/name) for name in names}
        entry,asm,boot,boot_dg,bridge=[(ROOT/name).read_text(encoding='utf-8') for name in names[1:]]
        failed=builder.patch_user_entry_asm(asm)
        injection='''    cmp qword [gs:UserSmpCpu.logical_id],0
    jne user_smp_fail_untrusted
    mov r8,cr3
    call user_smp_to_kernel
    mov rsp,[gs:UserCpu.kernel_stack]
    sub rsp,8
    xor edi,edi
    mov rsi,r8
    jmp user_runtime_failure_stop
'''
        self.assertEqual(1,failed.count(injection))
        self.assertEqual(asm,failed.replace('extern user_runtime_failure_stop\n','').replace(injection,''))
        self.assertIn('    mov qword [rax+1024+UserEntryMetrics.failed],1\n'+injection+'user_smp_fail_untrusted:',failed)
        self.assertEqual(asm[asm.index('user_smp_fail_untrusted:'):],failed[failed.index('user_smp_fail_untrusted:'):])
        retired=builder.patch_user_boot_asm(boot)
        save='''%if RUNTIME_LEVEL >= 7
    push rax
    mov rax,[rel boot_progress_view]
    mov [rel runtime_failure_view],rax
    pop rax
%endif
'''
        self.assertEqual(1,retired.count(save))
        self.assertEqual(boot,retired.replace('extern runtime_failure_view\n','').replace(save,''))
        self.assertIn('user_boot_retire:\n'+save+'    HW_BOOT_DISABLE\n    ret',retired)
        self.assertIn(' user_boot_mark(23);user_boot_retire();',boot_dg)
        self.assertFalse(hasattr(builder,'patch_user_boot'))
        self.assertFalse(hasattr(builder,'patch_user_bridge'))
        self.assertNotIn('user_runtime_failure_stop',boot_dg+bridge)
        painted=builder.patch_entry(entry);stop=painted[painted.index('user_runtime_failure_stop:'):]
        self.assertLess(stop.index('mov r12,rdi'),stop.index('call sched_xstate_restore'))
        self.assertLess(stop.index('mov r13,rsi'),stop.index('call sched_xstate_restore'))
        self.assertIn('mov rdi,r12\n    mov rsi,r13\n    call dong_user_runtime_status_run',stop)
        self.assertIn('mov r14,[rel boot_progress_view]',stop)
        self.assertIn('mov rax,[rel runtime_failure_view]',stop)
        self.assertIn('HW_BOOT_STAGE 24\n    mov [rel boot_progress_view],r14',stop)
        self.assertIn('cli\n.stop:\n    hlt\n    jmp .stop',stop)
        self.assertNotRegex(painted,r'mov (?:qword|byte) \[rel boot_progress_(?:error|failed)\],0')
        title=painted[painted.index('    cmp byte [rel boot_progress_phase],24'):painted.index('.runtime_failure_regular_title:')]
        self.assertIn('cmp qword [rax],1',title);self.assertIn('cmp qword [rax+8],1',title)
        self.assertIn('lea rsi,[rel runtime_failure_title]',title)
        self.assertEqual(FIELDS,builder.FIELDS);self.assertEqual(256,builder.REPORT_SIZE)
        self.assertEqual(15,len(builder.ROWS));self.assertTrue(all(len(label)<=13 and field in FIELDS for label,field in builder.ROWS))
        self.assertIn('mov edi,238',painted);self.assertEqual(470,120+14*24+14)
        self.assertEqual(9,len(builder.COMMAND_ORDER));self.assertNotIn('services_run.o',builder.REPLACED_OBJECTS)
        self.assertNotIn('ap_checkpoint_park',failed+retired+painted)
        for function,source,anchor in ((builder.patch_user_entry_asm,asm,'    mov qword [rax+1024+UserEntryMetrics.failed],1\nuser_smp_fail_untrusted:'),(builder.patch_user_boot_asm,boot,'user_boot_retire:\n    HW_BOOT_DISABLE\n    ret'),(builder.patch_entry,entry,'.progress_regular:\n')):
            with self.assertRaises(ValueError):function(source.replace(anchor,''))
            with self.assertRaises(ValueError):function(source+anchor)
        self.assertEqual(before,{name:sha(ROOT/name) for name in names})


if __name__=='__main__':
    unittest.main(verbosity=2)

"""Execute the actual UART routine and actual init with only hardware I/O mocked."""
from pathlib import Path
import hashlib,json,os,subprocess,unittest,uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import tool,nasm_flags
ROOT=Path(__file__).resolve().parents[1]

class ServicesConsoleTests(unittest.TestCase):
    def test_actual_init_death_propagates_after_retirement(self):
        from tests import test_user_smp_services as s
        from tests.test_service_ipc_cancellation import block
        from tests.test_service_gui_wiring import modules
        out=ROOT/'build/test/init-fatal'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        before=s.source_hashes()
        source=(ROOT/'kernel/user/services.dg').read_text(encoding='utf-8')
        needles=('unsafe fn process(', 'unsafe fn managed(', 'unsafe fn retire_one(', 'pub unsafe fn enable_smp(', 'unsafe fn runtime_poll(', 'unsafe fn large_poll(', 'export("dong_user_smp_project")', 'export("dong_user_smp_service")', 'export("dong_user_smp_interrupt")')
        actual='\n'.join(block(source,n) for n in needles)
        declarations='\n'.join(block(source,n) for n in ('struct LargeTicket{','align(64) struct LargeStorage{'))
        tail=s.TAIL.replace('match catalog_start(configuration as usize,7){ok=>{},err(e)=>{return e;},}','').replace('+7','+5').replace('[7]','[5]').replace('smp_service(7,','smp_service(5,')
        tail+='\nexport("us_status") fn status(value:u64)void{unsafe{(*(memory.processes()+5)).frame.rdi=value;}}\n'
        tail+='\nexport("us_invalid") fn invalid(value:u64)u64{unsafe{let f=&(*(memory.processes()+5)).frame;(*f).rflags=0;(*f).rax=0xff;return smp_service(5,value,f as u64);}}\n'
        prefix=s.PREFIX.replace('proc.EXITED,73','proc.EXITED,(*frame).rdi')
        entry=(ROOT/'tests/user_current_entry_probe.dg').read_text(encoding='utf-8')+prefix+declarations+s.DORMANT+actual+tail
        c=(ROOT/'tests/user_current_entry_probe.c').read_text(encoding='utf-8')
        for needle in ('U ABI dong_user_smp_service(', 'U ABI dong_user_smp_project('):c=c.replace(block(c,needle),'')
        cb=s.CMAIN[:s.CMAIN.index('int main(')].replace('slot==7','slot==5').replace('us_get(0)==7','us_get(0)==5').replace('[7]','[5]')
        c=c[:c.index('int main(void)')]+cb+s.MUTATION_POLICY+'''
extern void ABI us_status(U);
extern U ABI us_invalid(U);
int main(int argc,char**argv){C(argc==2);setup();cpu=0;C(!ue_lock(0));C(!us_setup(0));C(!us_project());C(!us_select());
 C(!us_op(1)&&performed==1&&us_get(0)==16);U expected;
 if(!strcmp(argv[1],"fault")){expected=0x050b0106;C(us_fault()==expected);}
 else if(!strcmp(argv[1],"invalid")||!strcmp(argv[1],"irq-invalid")){us_status(0xdeadbeef);expected=0x04050001;C(us_invalid(!strcmp(argv[1],"invalid")?257:258)==expected);}
 else{U status=!strcmp(argv[1],"zero")?0:0x050b0004;expected=status?status:0x050b0003;us_status(status);C(us_op(0xff)==expected);}
 C(withdrawn==1&&!us_get(5)&&us_get(7)==UINT64_MAX&&us_get(0)==16&&!d->processes[5].token&&!d->cpus[0].token&&!ue_audit());
 printf("INIT_FATAL_OK scenario=%s cleaned_before_error=%x\\n",argv[1],(unsigned)expected);return 0;}
'''
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
        def run(args,d,name,expected=0):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=90)
            (d/(name+'.json')).write_text(json.dumps(dict(args=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8')
            self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
        controls={'ignored-init-death':('failure==0&&was_init&&!managed(slot)','false'),
                  'lost-exit-status':('init_detail=init_status;','init_detail=0x050b_0003;'),
                  'unvalidated-exit-argument':('init_detail=0x0405_0001;','init_detail=init_status;')}
        for mode in ('debug','release'):
            for variant in ('normal',*controls):
                d=out/(mode+'-'+variant);stage=d/'kernel';text=entry
                if variant!='normal':old,new=controls[variant];self.assertEqual(2 if variant=='unvalidated-exit-argument' else 1,text.count(old));text=text.replace(old,new)
                overrides={'user_current_entry_probe':text,'user.memory':s.MEMORY+s.dormant_memory(),'boot.service_memory':s.dormant_resources(),
                    'user.window_broker':s.WINDOWS,'user.device_host':s.DEVICE,'boot.trace_runtime':'module boot.trace_runtime;pub unsafe fn event(a:u64,b:u64,c:u64,d:u64)void{return;}'}
                s.copy_graph(stage,['user_current_entry_probe'],overrides)
                # The older graph helper writes with the host locale. Restore
                # exact UTF-8 suppliers; never change compiler inputs by locale.
                suppliers=modules()
                for path in stage.rglob('*.dg'):
                    name=path.relative_to(stage).with_suffix('').as_posix().replace('/','.')
                    path.write_text(overrides[name] if name in overrides else suppliers[name].read_text(encoding='utf-8'),encoding='utf-8')
                compiled=compile_file(stage/'user_current_entry_probe.dg',roots=[stage],mode=mode)
                (d/'probe.asm').write_text(compiled.assembly,encoding='utf-8');(d/'probe.c').write_text(c,encoding='utf-8')
                objs=[]
                for name,path in (('dong',d/'probe.asm'),('entry',ROOT/'kernel/sched/user_entry.asm'),('legacy',ROOT/'kernel/sched/user_legacy.asm')):
                    obj=d/(name+'.o');run([nasm,'-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),'-I',str(ROOT/'include')+os.sep,path,'-o',obj],d,'assemble-'+name);objs.append(obj)
                exe=d/'probe.exe';run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',d/'probe.c',*objs,'-o',exe],d,'link')
                for case in ('zero','error','fault','invalid','irq-invalid') if variant=='normal' else (('invalid',) if variant=='unvalidated-exit-argument' else ('error',)):
                    r=run([exe,case],d,case,0 if variant=='normal' else 1)
                    if variant!='normal':self.assertIn('user CPL3 current-source oracle line',r.stderr)
        self.assertEqual(before,s.source_hashes())
        (out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before),indent=2)+'\n',encoding='utf-8')
        print('INIT_FATAL_EVIDENCE',out)

    def test_actual_console_and_init_without_working_uart(self):
        out=ROOT/'build/test/services-console'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        names=['kernel/services_run.asm','kernel/user/services.dg','tests/services_console_probe.c','tests/services_console_probe.asm','tests/test_services_console.py','tests/init_lifecycle_probe.dg','tests/init_lifecycle_probe.c']
        paths=[ROOT/n for n in names]+list((ROOT/'services/init').glob('*.dg'))+list((ROOT/'services/lib').glob('*.dg'))
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
        source=(ROOT/'kernel/services_run.asm').read_text(encoding='utf-8')
        body=source.split('; SERVICES_CONSOLE_BEGIN\n',1)[1].split('; SERVICES_CONSOLE_END',1)[0]
        legacy='''services_write_bytes:
    mov r8,rdi
    mov r9,rsi
.next:
    test r9,r9
    jz .ok
    mov ecx,0x100000
    mov dx,0x3fd
.wait:
    in al,dx
    test al,0x20
    jnz .send
    dec ecx
    jnz .wait
    mov eax,0x050b0004
    ret
.send:
    mov dx,0x3f8
    mov al,[r8]
    out dx,al
    inc r8
    dec r9
    jmp .next
.ok:
    xor eax,eax
    ret
'''
        # Pin the pre-fix production routine, not an invented failure model.
        self.assertEqual('1dbf09cb124ed6eea8a69efb466eae04addf4a5cb233a0b5c15b82357ee00ac1',hashlib.sha256(legacy.encode()).hexdigest())
        def command(argv,d,name,expected=0):
            r=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,timeout=90)
            (d/(name+'.json')).write_text(json.dumps(dict(argv=list(map(str,argv)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8')
            self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
        fmt='win64' if os.name=='nt' else 'elf64'
        evidence=[]
        for variant in ('normal','legacy','drop-ring','uart-fatal','unbounded-polls'):
            d=out/variant;d.mkdir();text=legacy if variant=='legacy' else body
            if variant=='drop-ring':text=text.replace('mov [r9+r8],al','nop')
            if variant=='uart-fatal':text=text.replace('.drop:\n    add [rel services_console_dropped],r13','.drop:\n    add [rel services_console_dropped],r13\n    mov eax,0x050b0004\n    jmp .return').replace('.ok:\n    xor eax,eax','.ok:\n    xor eax,eax\n.return:')
            if variant=='unbounded-polls':text=text.replace('mov ebx,65536','mov ebx,65537')
            text=text.replace('in al,dx','call console_test_in').replace('out dx,al','call console_test_out').replace('    rdtsc','    call console_test_clock')
            asm=d/'console.asm';asm.write_text('bits 64\ndefault rel\nsection .text\nglobal services_write_bytes\nextern console_test_in,console_test_out,console_test_clock\n'+text,encoding='utf-8')
            for target in ('win64','elf64'):command([nasm,'-f',target,*nasm_flags(nasm),asm,'-o',d/(target+'.o')],d,'assemble-'+target)
            shim=d/'shim.o';command([nasm,'-f',fmt,*nasm_flags(nasm),ROOT/'tests/services_console_probe.asm','-o',shim],d,'shim')
            obj=d/(fmt+'.o');exe=d/'probe.exe'
            flags=['-DLEGACY'] if variant=='legacy' else []
            for opt in ('-O0','-O2') if variant=='normal' else ('-O2',):
                command([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror',*flags,ROOT/'tests/services_console_probe.c',obj,shim,'-o',exe],d,'link'+opt)
                r=command([exe],d,'run'+opt,0 if variant in ('normal','legacy') else 1)
                if variant not in ('normal','legacy'):self.assertIn('CONSOLE_ASSERT',r.stderr)
                evidence.append(dict(variant=variant,opt=opt,stdout=r.stdout,stderr=r.stderr))
            if variant not in ('normal','legacy'):continue
            c=(ROOT/'tests/init_lifecycle_probe.c').read_text(encoding='utf-8')
            needle='if(number==0x70){CK(b&&b<=4096);logs++;return 0;}'
            self.assertEqual(1,c.count(needle))
            c=c.replace(needle,'if(number==0x70){CK(b&&b<=4096);logs++;return services_write_bytes((void*)(uintptr_t)a,b);}')
            c=c.replace('static int main_mode;','extern ABI U services_write_bytes(const void*,U);\nextern void console_scenario(U);\nstatic int main_mode;')
            c=c.replace('static void launcher(void){main_mode=1;','static void launcher(void){console_scenario(1);main_mode=1;')
            if variant=='legacy':c=c.replace('CK(result==0x051100ff);CK(spawns==3&&kills==1&&qhead==qtail);','CK(result==0x050b0004);CK(spawns==0&&kills==0&&logs==1);')
            cpath=d/'init.c';cpath.write_text(c,encoding='utf-8')
            for mode in ('debug','release'):
                compiled=compile_file(ROOT/'tests/init_lifecycle_probe.dg',roots=[ROOT/'tests',ROOT/'services',ROOT/'lang/std'],mode=mode)
                initasm=d/(mode+'.asm');initasm.write_text(compiled.assembly,encoding='utf-8');initobj=d/(mode+'.o')
                command([nasm,'-f',fmt,*nasm_flags(nasm),initasm,'-o',initobj],d,mode+'-assemble')
                command([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-DINTEGRATED_INIT',*flags,cpath,ROOT/'tests/services_console_probe.c',initobj,obj,shim,'-o',exe],d,mode+'-link')
                r=command([exe],d,mode+'-run');evidence.append(dict(variant=variant,init_mode=mode,stdout=r.stdout))
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        (out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before,evidence=evidence),indent=2)+'\n',encoding='utf-8')
        print('SERVICES_CONSOLE_EVIDENCE',out)

if __name__=='__main__':unittest.main(verbosity=2)

"""Execute actual diagnostic producer/ASM with explicit architecture models."""
from pathlib import Path
import hashlib,json,os,re,subprocess,unittest,uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import tool,nasm_flags
from tests.test_first_user_checkpoint import fixtures,SUPPLIERS
from tools import build_startup_console as b
ROOT=Path(__file__).resolve().parents[1]
MUTANTS={
 'no-handoff':('if STATE.stopped!=0{return 0;}','if false{return 0;}'),
 'wrong-frame':('if kind==3{frame=(*c).capture;}','if false{frame=(*c).capture;}'),
 'wrong-uppercase':('value-=32;','value-=31;'),
 'wrong-wrap':('if row==7{','if row==6{'),
 'no-first-pin':('FIRST_KIND==0&&kind!=0','kind!=0'),
 'no-terminal-pin':('if TERMINAL_KIND==0{lines(ring,count,count);}','if true{lines(ring,count,count);}'),
 'false-handoff':('(*c).slot==3&&(*c).mode==6','(*c).slot==5&&(*c).mode==6'),
}
ASM_MUTANTS={
 'asm-no-fast':('    cmp byte [rel startup_console_disabled],0\n    jne .return\n',''),
 'asm-no-close':('    mov byte [rel startup_console_disabled],1','    mov byte [rel startup_console_disabled],0'),
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class StartupConsoleTests(unittest.TestCase):
 def test_actual_producer_and_hooks(self):
  paths=[ROOT/'kernel/boot/startup_console.dg',Path(__file__),ROOT/'tests/startup_console_probe.c',ROOT/'tests/startup_console_shim.asm',ROOT/'tools/build_startup_console.py',ROOT/'kernel/entry.asm',ROOT/'kernel/sched/user_entry.asm',ROOT/'kernel/services_run.asm',*(ROOT/p for p in SUPPLIERS)]
  before={str(p):sha(p) for p in paths};out=ROOT/'build/test/startup-console'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
  original=paths[0].read_text(encoding='utf-8');results=[]
  for variant in ('normal',*MUTANTS,*ASM_MUTANTS):
   for mode in ('debug','release'):
    d=out/variant/mode;d.mkdir(parents=True);source=original
    if variant in MUTANTS:old,new=MUTANTS[variant];self.assertEqual(1,source.count(old));source=source.replace(old,new)
    graph=fixtures();graph['boot/startup_console.dg']=source+'\nexport("checkpoint_reset") fn reset()void{unsafe{STATE=EMPTY;FIRST_KIND=0;FIRST_CLOSED=false;TERMINAL_KIND=0;TERMINAL_CLOSED=false;}}\n'
    for name,body in graph.items():
     p=d/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
    compiled=compile_file(d/'boot/startup_console.dg',roots=[d],mode=mode);b.console_layout(compiled.layout_manifest)
    self.assertNotRegex(compiled.assembly.lower(),r'\b(?:xmm\d+|ymm\d+|wrmsr|rdmsr|cli|sti|hlt)\b')
    sym='__dg_m'+b'boot.startup_console'.hex()+'_g'+b'STATE'.hex()
    pattern=re.compile(r'(?m)^\$?'+sym+r':\r?\n((?:[ \t]+db [0-9, ]+\r?\n)+)')
    self.assertEqual(1,len(pattern.findall(compiled.assembly)))
    data=pattern.search(compiled.assembly).group(1)
    self.assertEqual(792,len(re.findall(r'\d+',data)))
    asm=pattern.sub(lambda m:'global console_canary_low\nconsole_canary_low: times 4 dq 0\n'+sym+':\n'+m.group(1)+'global console_canary_high\nconsole_canary_high: times 4 dq 0\n',compiled.assembly)
    (d/'probe.asm').write_text(asm,encoding='utf-8')
    entry=b.patch_entry((ROOT/'kernel/entry.asm').read_text(encoding='utf-8'))
    tick=entry[entry.index('startup_console_tick:\n'):]
    if variant in ASM_MUTANTS:
     old,new=ASM_MUTANTS[variant];self.assertEqual(1,tick.count(old));tick=tick.replace(old,new)
    replacements={ 'cmp qword [gs:UserSmpCpu.logical_id],0':'cmp qword [rel test_cpu],0', 'mov rax,cr3':'mov rax,[rel test_root]', 'cmp rax,[gs:UserCpu.original_cr3]':'cmp rax,[rel test_kernel_root]', 'pushfq\n    pop rax':'mov rax,[rel test_flags]', 'HW_BOOT_STAGE 25':'mov byte [rel boot_progress_phase],25\n    call boot_progress_draw'}
    for old,new in replacements.items():self.assertEqual(1,tick.count(old));tick=tick.replace(old,new)
    services=b.patch_services_run((ROOT/'kernel/services_run.asm').read_text(encoding='utf-8'))
    wrapper=services[services.index('services_write_bytes:\n'):services.index('startup_console_write_bytes:\n')]
    (d/'hooks.asm').write_text((ROOT/'tests/startup_console_shim.asm').read_text()+tick+'\nsection .text\n'+wrapper,encoding='utf-8')
    def run(args,name,expected=0):
     r=subprocess.run(list(map(str,args)),cwd=ROOT,text=True,capture_output=True,timeout=90);(d/(name+'.json')).write_text(json.dumps(dict(args=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8');self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
    native='win64' if os.name=='nt' else 'elf64'
    for name in ('probe','hooks'):
     for fmt in ('elf64','win64'):run([nasm,'-f',fmt,*nasm_flags(nasm),d/(name+'.asm'),'-o',d/(name+'-'+fmt+'.o')],'assemble-'+name+'-'+fmt)
    for opt in ('-O0','-O2') if variant=='normal' else ('-O2',):
     exe=d/('probe'+opt+'.exe');run([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror',ROOT/'tests/startup_console_probe.c',d/('probe-'+native+'.o'),d/('hooks-'+native+'.o'),'-o',exe],'link'+opt)
     r=run([exe],'run'+opt,0 if variant=='normal' else 1);self.assertIn('STARTUP_CONSOLE_OK' if variant=='normal' else 'STARTUP_CONSOLE_ASSERT',r.stdout if variant=='normal' else r.stderr);self.assertNotIn('unexpected panic',r.stderr);results.append(dict(variant=variant,mode=mode,opt=opt,stdout=r.stdout,stderr=r.stderr))
  self.assertEqual(before,{str(p):sha(p) for p in paths});(out/'result.json').write_text(json.dumps(dict(passed=True,skips=0,source_stable=True,sources=before,results=results),indent=2)+'\n',encoding='utf-8');print('STARTUP_CONSOLE_EVIDENCE',out)
 def test_precise_private_hooks(self):
  from tools import build_user_runtime as old
  read=lambda n:(ROOT/n).read_text(encoding='utf-8')
  original=read('kernel/sched/user_entry.asm');actual=b.patch_user_entry_asm(original);prior=old.patch_user_entry_asm(original)
  hook='    ; BOOT_CONSOLE_RETURN: trusted kernel root/xstate, before commit/IRET.\n    mov edi,1\n    call startup_console_tick\n'
  self.assertEqual(prior,actual.replace(hook,'').replace('extern startup_console_tick\n',''));self.assertNotIn('hlt',hook)
  bridge=read('kernel/sched/user_bridge.dg');actual=b.patch_user_bridge(bridge)
  self.assertEqual(bridge,actual.replace('\nunsafe extern "sysv64" fn startup_console_tick(kind:u64)void;','').replace('\n if cpu==0{startup_console_tick(3);}',''))
  self.assertIn('if cpu==0{startup_console_tick(3);}\n stage(cpu,DEADLINE)',actual)
  self.assertEqual(old.patch_user_boot_asm(read('kernel/sched/user_boot.asm')),b.patch_user_boot_asm(read('kernel/sched/user_boot.asm')))
  self.assertEqual('user-startup-console',b.PROFILE);self.assertEqual(10,len(b.COMMAND_ORDER));self.assertEqual('DongOS BOOT LIVE R2',b.BANNER.decode())
  for fn,path in ((b.patch_entry,'kernel/entry.asm'),(b.patch_user_entry_asm,'kernel/sched/user_entry.asm'),(b.patch_services_run,'kernel/services_run.asm')):
   with self.assertRaises(ValueError):fn(fn(read(path)))
if __name__=='__main__':unittest.main(verbosity=2)

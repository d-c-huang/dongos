"""Actual checkpoint capture native execution, and exact private hook boundaries."""
from pathlib import Path
import hashlib,json,os,subprocess,unittest,uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tools import build_ap_boot_checkpoint as builder
from tests.test_service_ipc_cancellation import block
ROOT=Path(__file__).resolve().parents[1]
class ApCheckpointTests(unittest.TestCase):
 def test_actual_capture_and_bad_bodies(self):
  out=ROOT/'build/test/ap-checkpoint'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  paths=[ROOT/'kernel/boot/ap_boot_checkpoint.dg',ROOT/'tools/build_ap_boot_checkpoint.py',ROOT/'tests/ap_boot_checkpoint_probe.c',Path(__file__),ROOT/'kernel/sched/user_entry_plan.dg']
  before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};results=[]
  original=paths[0].read_text(encoding='utf-8')
  for kind in ('normal','wrong-lock','repeat','missing-done','ignore-error','accept-ready1','ignore-park','last-error'):
   for mode in ('debug','release'):
    d=out/kind/mode;d.mkdir(parents=True);(d/'boot').mkdir();(d/'sched').mkdir();source=original
    if kind!='normal':
     a,b={'wrong-lock':('STATE.lock=atomic_load(&(*d).lock);','STATE.lock=0;'),'repeat':('if STATE.version!=0{return &STATE;}','if false{return &STATE;}'),'missing-done':('compiler_fence();STATE.done=1;','compiler_fence();'),'ignore-error':('||STATE.error_mask!=0',''),'accept-ready1':('if ready==2','if ready>=1'),'ignore-park':('||STATE.parked_mask!=(STATE.online&~1)',''),'last-error':('if STATE.first_cpu==16','if true')}[kind];self.assertEqual(1,source.count(a));source=source.replace(a,b)
    (d/'boot/ap_boot_checkpoint.dg').write_text(source+'\nexport("checkpoint_reset") fn reset()void{unsafe{STATE=EMPTY;}}\n',encoding='utf-8')
    (d/'sched/user_boot.dg').write_text('module sched.user_boot;pub struct Report{pub ready:u64,pub failed:u64,pub published:u64,pub count:u64,pub online:u64,pub domain:u64,pub headers:u64,pub contexts:u64,pub root:u64,pub tsc_hz:u64}\npub extern "sysv64" ("checkpoint_boot") fn report()*const Report;\n',encoding='utf-8')
    (d/'sched/user_domain.dg').write_text('module sched.user_domain;pub struct Engine{pub ready:u64,pub online:u64,pub sequence:u64,pub count:u64}pub struct Domain{pub ready:u64,pub failed:u64,pub lock:u64,pub owner:u64,pub online:u64,pub sequence:u64,pub barrier:u64,pub expected:u64,pub completed:u64,pub kernel_root:u64,pub engine:*Engine,pub cpus:u64,pub processes:u64,pub arena:u64,pub bytes:u64,}',encoding='utf-8')
    (d/'sched/user_entry_plan.dg').write_text('module sched.user_entry_plan;\n'+block((ROOT/'kernel/sched/user_entry_plan.dg').read_text(encoding='utf-8'),'pub struct Cpu{')+'\n',encoding='utf-8')
    c=compile_file(d/'boot/ap_boot_checkpoint.dg',roots=[d],mode=mode);types={t['full_name']:t for t in c.layout_manifest['types']};self.assertEqual(136,types['boot.ap_boot_checkpoint.Report']['size']);self.assertEqual(list(builder.FIELDS),[f['name'] for f in types['boot.ap_boot_checkpoint.Report']['fields']]);self.assertEqual(120,types['sched.user_domain.Domain']['size']);self.assertEqual(256,types['sched.user_entry_plan.Cpu']['size']);self.assertEqual(200,next(f['offset'] for f in types['sched.user_entry_plan.Cpu']['fields'] if f['name']=='ready'));self.assertEqual(208,next(f['offset'] for f in types['sched.user_entry_plan.Cpu']['fields'] if f['name']=='last_error'))
    self.assertIn('g5354415445:',c.assembly.split('section .bss',1)[1]);self.assertIn('resb 136',c.assembly.split('section .bss',1)[1]);asm=d/'probe.asm';asm.write_text(c.assembly,encoding='utf-8');obj=d/'probe.o';nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc,'real tools required; no skip')
    def command(args,label):
     r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=90);(d/(label+'.json')).write_text(json.dumps(dict(args=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8');return r
    for fmt in ('elf64','win64'):
     target=obj if fmt==('win64' if os.name=='nt' else 'elf64') else d/(fmt+'.o');r=command([nasm,'-f',fmt,*nasm_flags(nasm),'-o',target,asm],'assemble-'+fmt);self.assertEqual(0,r.returncode,r.stderr)
    for opt in ('-O0','-O2') if kind=='normal' else ('-O2',):
     exe=d/('probe'+opt+('.exe' if os.name=='nt' else ''));r=command([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror',*(['-mno-sse'] if os.name=='nt' else ['-no-pie']),paths[2],obj,'-o',exe],'link'+opt);self.assertEqual(0,r.returncode,r.stderr);r=command([exe],'native'+opt)
     if kind=='normal':self.assertEqual(0,r.returncode,r.stdout+r.stderr);self.assertIn('CHECKPOINT_NATIVE_OK',r.stdout)
     else:self.assertEqual(1,r.returncode,r.stdout+r.stderr);self.assertIn('CHECKPOINT_ASSERT',r.stderr)
     results.append(dict(kind=kind,mode=mode,opt=opt,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
  self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths});(out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before,results=results),indent=2)+'\n',encoding='utf-8')
 def test_private_hook_and_renderer_contract(self):
  s=(ROOT/'kernel/sched/user_boot.dg').read_text(encoding='utf-8');p=builder.patch_user_boot(s)
  self.assertLess(p.index('let projected=user_boot_project();'),p.index(' ap_boot_checkpoint_stop();'));self.assertLess(p.index(' ap_boot_checkpoint_stop();'),p.index('user_boot_retire();'))
  self.assertIn('if arch.read_tsc()>=until{return 0x060b_0021;}',p)
  source=(ROOT/'kernel/sched/user_boot.asm').read_text(encoding='utf-8');patched=builder.patch_user_boot_asm(source)
  self.assertLess(patched.index('call user_smp_activate',patched.index('user_smp_try_handoff:')),patched.index('lock bts qword [rel ap_checkpoint_parked],rcx'))
  self.assertIn('cli\n.ap_checkpoint_park:\n    hlt\n    jmp .ap_checkpoint_park',patched)
  self.assertEqual(source[source.index('user_smp_boot_begin:'):],patched[patched.index('user_smp_boot_begin:'):].split('\nsection .bss\nalign 8, resb 1\nglobal ap_checkpoint_parked')[0])
  with self.assertRaises(ValueError):builder.patch_user_boot(s.replace(' user_boot_mark(23);user_boot_retire();',' user_boot_retire();'))
  with self.assertRaises(ValueError):builder.patch_user_boot_asm(source.replace('    jmp user_smp_idle\n.return:','    ret\n.return:'))
  self.assertEqual((ROOT/'kernel/services_run.asm').read_text(encoding='utf-8'),builder.patch_services_run((ROOT/'kernel/services_run.asm').read_text(encoding='utf-8')))
  entry=builder.patch_entry((ROOT/'kernel/entry.asm').read_text(encoding='utf-8'));self.assertIn('global ap_boot_checkpoint_stop',entry);self.assertIn('call dong_ap_boot_checkpoint_run\n    HW_BOOT_STAGE 24',entry);self.assertIn('cli\n.stop:\n    hlt\n    jmp .stop',entry);self.assertEqual(15,len(builder.ROWS));self.assertEqual(470,120+14*24+14);self.assertEqual(9,len(builder.COMMAND_ORDER));self.assertIn('user_boot.o',builder.REPLACED_OBJECTS)
if __name__=='__main__':unittest.main(verbosity=2)

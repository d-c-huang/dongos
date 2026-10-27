"""Actual checkpoint capture native execution, and exact private hook boundaries."""
from pathlib import Path
import hashlib,json,os,subprocess,unittest,uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tools import build_user_boot_checkpoint as builder
ROOT=Path(__file__).resolve().parents[1]
class CheckpointTests(unittest.TestCase):
 def test_actual_capture_and_bad_bodies(self):
  out=ROOT/'build/test/user-checkpoint'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  paths=[ROOT/'kernel/boot/user_boot_checkpoint.dg',ROOT/'tools/build_user_boot_checkpoint.py',ROOT/'tests/user_boot_checkpoint_probe.c',Path(__file__)]
  before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};results=[]
  original=paths[0].read_text(encoding='utf-8')
  for kind in ('normal','wrong-lock','repeat','missing-done'):
   for mode in ('debug','release'):
    d=out/kind/mode;d.mkdir(parents=True);(d/'boot').mkdir();(d/'sched').mkdir();source=original
    if kind!='normal':
     a,b={'wrong-lock':('STATE.lock=atomic_load(&(*d).lock);','STATE.lock=0;'),'repeat':('if STATE.version!=0{return &STATE;}','if false{return &STATE;}'),'missing-done':('compiler_fence();STATE.done=1;','compiler_fence();')}[kind];self.assertEqual(1,source.count(a));source=source.replace(a,b)
    (d/'boot/user_boot_checkpoint.dg').write_text(source+'\nexport("checkpoint_reset") fn reset()void{unsafe{STATE=EMPTY;}}\n',encoding='utf-8')
    (d/'sched/user_boot.dg').write_text('module sched.user_boot;pub struct Report{pub ready:u64,pub failed:u64,pub published:u64,pub count:u64,pub online:u64,pub domain:u64,pub headers:u64,pub contexts:u64,pub root:u64,pub tsc_hz:u64}\npub extern "sysv64" ("checkpoint_boot") fn report()*const Report;\n',encoding='utf-8')
    (d/'sched/user_domain.dg').write_text('module sched.user_domain;pub struct Domain{'+''.join('pub '+n+':u64,' for n in ('ready','failed','lock','owner','online','sequence','barrier','expected','completed','kernel_root','engine','cpus','processes','arena','bytes'))+'}',encoding='utf-8')
    c=compile_file(d/'boot/user_boot_checkpoint.dg',roots=[d],mode=mode);types={t['full_name']:t for t in c.layout_manifest['types']};self.assertEqual(136,types['boot.user_boot_checkpoint.Report']['size']);self.assertEqual(list(builder.FIELDS),[f['name'] for f in types['boot.user_boot_checkpoint.Report']['fields']]);self.assertEqual(120,types['sched.user_domain.Domain']['size'])
    asm=d/'probe.asm';asm.write_text(c.assembly,encoding='utf-8');obj=d/'probe.o';nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc,'real tools required; no skip')
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
  anchor=' let enabled=services.enable_smp();match enabled{ok=>{},err(e)=>{return e;},}'
  self.assertLess(p.index(anchor),p.index(' user_boot_checkpoint_stop();'));self.assertLess(p.index(' user_boot_checkpoint_stop();'),p.index(' if user_boot_publish('));self.assertEqual(s,p.replace('\nunsafe extern "sysv64" fn user_boot_checkpoint_stop()void;','').replace(' user_boot_checkpoint_stop();\n',''))
  with self.assertRaises(ValueError):builder.patch_user_boot(s.replace(' user_boot_mark(21);',' user_boot_mark(22);'))
  self.assertEqual((ROOT/'kernel/services_run.asm').read_text(encoding='utf-8'),builder.patch_services_run((ROOT/'kernel/services_run.asm').read_text(encoding='utf-8')))
  entry=builder.patch_entry((ROOT/'kernel/entry.asm').read_text(encoding='utf-8'));self.assertIn('global user_boot_checkpoint_stop',entry);self.assertIn('call dong_user_boot_checkpoint_run\n    HW_BOOT_STAGE 24',entry);self.assertIn('cli\n.stop:\n    hlt\n    jmp .stop',entry);self.assertEqual(15,len(builder.ROWS));self.assertEqual(470,120+14*24+14)
  self.assertIn('call screen_draw',(ROOT/'kernel/boot_progress.asm').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main(verbosity=2)

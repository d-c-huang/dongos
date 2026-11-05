"""Execute exact lifecycle branches; hardware/memory boundaries are explicit stubs."""
import hashlib,json,os,re,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import tool,nasm_flags
from tests.test_p5_recovery_context import block
from tests.test_gui_font_portal import collect,ROOT
HERE=Path(__file__).resolve().parent
CAND=HERE.parent/'src/p5/dma-call/user'

class DmaCallTests(unittest.TestCase):
 def test_actual_lifecycle_and_mutants(self):
  paths=[CAND/'services.dg',CAND/'device_host.dg',HERE/'p5_dma_call_fixture.dg',HERE/'p5_dma_call_probe.c',Path(__file__)]
  before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
  out=ROOT/'build/test/p5-dma-call'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
  records=[]
  def run(args,d,label):
   r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=90,cwd=ROOT)
   (d/(label+'.json')).write_text(json.dumps(dict(args=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2));return r
  for mode in ('debug','release'):
   for variant in ('normal','skip-prepare','before-stop','lost-error'):
    d=out/(mode+'-'+variant);d.mkdir();services,host=paths[0].read_text(),paths[1].read_text()
    if variant=='skip-prepare':
     old='try dma_prepare_retirement(slot);';self.assertEqual(host.count(old),1);host=host.replace(old,'')
    if variant=='before-stop':
     old='if SMP_ENABLED{let stopped=smp_bridge.retire(id);';self.assertEqual(services.count(old),1)
     services=services.replace(old,'if SMP_ENABLED{device_host.dma_retire_stopped(id,incarnation);let stopped=smp_bridge.retire(id);')
    if variant=='lost-error':
     old='DMA_CONTINUATIONS[slot].error_code=e;';self.assertEqual(host.count(old),1);host=host.replace(old,'DMA_CONTINUATIONS[slot].error_code=0;')
    template=paths[2].read_text()
    replacements={
     '// PRODUCTION_HARDWARE':block(host,'unsafe fn hardware('),
     '// PRODUCTION_CONTEXT':host.split('// P5_CONTEXT_BEGIN')[1].split('// P5_CONTEXT_END')[0],
     '// PRODUCTION_HOST_REVOKE':block(host,'pub unsafe fn revoke_owner('),
     '// PRODUCTION_HOST_MANAGER':block(host,'pub unsafe fn revoke('),
     '// PRODUCTION_DMA_HOST':host.split('// P5_DMA_HOST_BEGIN')[1].split('// P5_DMA_HOST_END')[0],
     '// PRODUCTION_DMA_CONTINUE':host.split('// P5_DMA_CONTINUE_BEGIN')[1].split('// P5_DMA_CONTINUE_END')[0],
     '// PRODUCTION_SYSCALL':block(services,'if code==0x63 {'),
     '// PRODUCTION_RETIRE':block(services,'unsafe fn retire_one('),
     '// PRODUCTION_REVOKE_LOADED':block(services,'unsafe fn revoke_loaded('),
     '// PRODUCTION_DISCARD':block(services,'unsafe fn discard_preloaded('),
     '// PRODUCTION_CASCADE':block(services,'unsafe fn retire('),
    }
    for key,value in replacements.items():self.assertEqual(template.count(key),1);template=template.replace(key,value)
    ledger=(ROOT/'kernel/user/device_manager.dg').read_text();policy=(ROOT/'services/drivers/device_policy.dg').read_text()
    template=template.replace(block(template,'pub unsafe fn same_identity('),block(policy,'pub unsafe fn same_identity('))
    template=template.replace(block(template,'pub unsafe fn binding('),'\n'.join(block(ledger,n) for n in ('unsafe fn require(','unsafe fn index(','pub unsafe fn binding(')))
    sections=re.split(r'(?m)^// FILE (.+)\n',template)
    for i in range(1,len(sections),2):
     p=d/sections[i].strip();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sections[i+1])
    for source,target in [('kernel/user/abi.dg','user/abi.dg'),('services/lib/device_abi.dg','lib/device_abi.dg')]:
     p=d/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/source).read_bytes())
    c=compile_file(d/'p5_recovery_context_fixture.dg',roots=[d],mode=mode)
    layout={x['full_name']:x for x in c.layout_manifest['types']};self.assertEqual(layout['user.device_host.DmaContext']['size'],424)
    asm=d/'probe.asm';asm.write_text(c.assembly);obj=d/'probe.o'
    r=run([nasm,'-O0','-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),asm,'-o',obj],d,'assemble');self.assertEqual(r.returncode,0,r.stderr)
    exe=d/('probe.exe' if os.name=='nt' else 'probe')
    r=run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',* ([] if os.name=='nt' else ['-no-pie']),paths[3],obj,'-o',exe],d,'link');self.assertEqual(r.returncode,0,r.stderr)
    cases=['normal','up','manager','preload','not-pinned','cascade','cascade-barrier']+['failure'+str(n) for n in (5,6,7,8,11,12,13,22,24,32,33)]+['context'+str(n) for n in range(1,7)]
    if variant!='normal':cases=['failure32' if variant=='lost-error' else 'normal']
    for case in cases:
     r=run([exe,case],d,case);self.assertEqual(r.returncode,0 if variant=='normal' else 1,r.stdout+r.stderr)
     if variant!='normal':self.assertIn('P5 call check failed',r.stderr)
     records.append(dict(mode=mode,variant=variant,case=case,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
    (d/'fragments.json').write_text(json.dumps({k:hashlib.sha256(v.encode()).hexdigest() for k,v in replacements.items()},indent=2))
  self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
  (out/'summary.json').write_text(json.dumps(dict(passed=True,source_sha256=before,records=records,guest_verified=False),indent=2));print('P5_DMA_CALL_EVIDENCE',out)

 def test_production_graph(self):
  out=ROOT/'build/test/p5-dma-call'/('graph-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  collect(out,['user.services'],{n:(CAND/(n.split('.')[-1]+'.dg')).read_text() for n in ('user.services','user.device_host')})
  for mode in ('debug','release'):
   c=compile_file(out/'user/services.dg',roots=[out],mode=mode);(out/(mode+'.asm')).write_text(c.assembly)

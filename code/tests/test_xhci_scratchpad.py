"""Execute actual scratch controller/authority/allocator with independent C oracles."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tests.test_service_ipc_cancellation import block
ROOT=Path(__file__).resolve().parents[1]

class XhciScratchpadTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/'build/test/xhci-scratchpad'/('run-'+uuid.uuid4().hex[:12]);cls.out.mkdir(parents=True)
  cls.paths=[*sorted((ROOT/'services').rglob('*.dg')),ROOT/'kernel/user/memory.dg',ROOT/'kernel/user/devices.dg',Path(__file__),ROOT/'tests/xhci_scratchpad_probe.c',*[ROOT/'tests'/n for n in ('xhci_controller_probe.dg','xhci_controller_probe.c','xhci_core_probe.c','xhci_authority_probe.dg','dma_lease_fixture.dg','dma_lease_adapter.dg','dma_lease_probe.c')]]
  cls.before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths};cls.results=[]
  (cls.out/'source-before.json').write_text(json.dumps(cls.before,indent=2)+'\n',encoding='utf-8')
 @classmethod
 def tearDownClass(cls):
  after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}
  if after!=cls.before:raise AssertionError('scratchpad production/oracle source changed')
  (cls.out/'result.json').write_text(json.dumps(dict(source_stable=True,source_sha256=after,results=cls.results),indent=2)+'\n',encoding='utf-8')
 def command(self,args,d,name):
  args=list(map(str,args));r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=120)
  (d/(name+'.json')).write_text(json.dumps(dict(command=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8')
  return r
 def assemble(self,source,roots,d,name,mode):
  c=compile_file(source,roots=roots,mode=mode);asm=d/(name+'.asm');asm.write_text(c.assembly,encoding='utf-8')
  (d/(name+'-layout.json')).write_text(json.dumps(c.layout_manifest,indent=2)+'\n',encoding='utf-8')
  nasm=tool('nasm','NASM');self.assertTrue(nasm,'real NASM required; no skip')
  obj=d/(name+'.o')
  for fmt in ('elf64','win64'):
   output=obj if fmt==('win64' if os.name=='nt' else 'elf64') else d/(name+'-'+fmt+'.o')
   r=self.command([nasm,'-f',fmt,*nasm_flags(nasm),'-o',output,asm],d,name+'-'+fmt);self.assertEqual(0,r.returncode,r.stdout+r.stderr)
  return obj
 def execute(self,objects,csource,d,family,mutant):
  cc=tool('gcc','CC');self.assertTrue(cc,'real C compiler required; no skip')
  for opt in ('-O0','-O2') if not mutant else ('-O2',):
   exe=d/('probe'+opt+('.exe' if os.name=='nt' else ''))
   r=self.command([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror','-fno-strict-aliasing',*(['-mno-sse'] if os.name=='nt' else ['-no-pie']),'-I',d,'-I',ROOT/'tests',csource,*objects,'-o',exe],d,'link'+opt);self.assertEqual(0,r.returncode,r.stdout+r.stderr)
   r=self.command([exe,*([family] if family!='allocator' else [])],d,'native'+opt)
   if mutant:self.assertEqual(1,r.returncode,r.stdout+r.stderr);self.assertIn('check failed line',r.stderr);self.assertNotIn('unexpected panic',r.stderr)
   else:self.assertEqual(0,r.returncode,r.stdout+r.stderr);self.assertIn('checks',r.stdout)
   self.results.append(dict(family=family,mutant=mutant,mode=d.name,optimization=opt,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
 def native(self,family):
  mutations={
   'controller':{'missing-dcbaa':('volatile_store((*s).setup.pointer as *u64,(*s).setup.physical+dma.TABLE);',''),
                 'wrong-buffer':('(*s).setup.physical+dma.BUFFERS+i*4096','(*s).setup.physical+dma.BUFFERS+i*4096+8'),
                 'uncleared-tail':('while i<(*s).setup.bytes/8','while i<DMA_BYTES/8')},
   'authority':{'unchecked-tail':('while offset<dma.len {','while offset<dma_layout.BASE_BYTES as usize {'),
                'unchecked-dcbaa':('if offset==0&&dma_layout.count(h.hcs2)!=0{expected=h.lease_physical+dma_layout.TABLE;}','if offset==0&&dma_layout.count(h.hcs2)!=0{expected=read_unaligned(dma.ptr as *const u64);}'),
                'restore-command':('r.usbcmd!=0||','(r.usbcmd&~0x100)!=0||')},
  }[family]
  for mutation in (None,*mutations):
   for mode in ('debug','release'):
    d=self.out/family/(mutation or 'normal')/mode;d.mkdir(parents=True);services=d/'services';shutil.copytree(ROOT/'services',services)
    if mutation:
     p=services/('usb/xhci_controller.dg' if family=='controller' else 'drivers/xhci_authority.dg');text=p.read_text(encoding='utf-8');a,b=mutations[mutation];self.assertEqual(1,text.count(a));p.write_text(text.replace(a,b),encoding='utf-8')
    objects=[self.assemble(ROOT/'tests/xhci_controller_probe.dg',[ROOT/'tests',services],d,'controller',mode),self.assemble(ROOT/'tests/xhci_authority_probe.dg',[ROOT/'tests',services],d,'authority',mode)]
    fixture=(ROOT/'tests/xhci_controller_probe.c').read_text(encoding='utf-8');self.assertEqual(1,fixture.count('int main(int argc,char**argv)'));(d/'xhci_scratch_controller_fixture.c').write_text(fixture.replace('int main(int argc,char**argv)','int scratch_old_main(int argc,char**argv)'),encoding='utf-8')
    self.execute(objects,ROOT/'tests/xhci_scratchpad_probe.c',d,family,mutation)
 def test_actual_controller_scratch_initialization(self):self.native('controller')
 def test_actual_authority_scratch_graph_and_zero_pages(self):self.native('authority')
 def test_actual_extended_allocator_and_partial_failures(self):
  original=(ROOT/'kernel/user/memory.dg').read_text(encoding='utf-8')
  metadata=original[original.index('pub struct DmaLease'):original.index('// One exclusive BSP loader transaction.')]
  body=block(original,'pub unsafe fn contiguous_xhci(').replace('pub unsafe fn contiguous_xhci(','pub unsafe fn contiguous(')
  fixture=(ROOT/'tests/dma_lease_fixture.dg').read_text(encoding='utf-8').replace('[64]','[256]').replace(';64]',';256]').replace('CAPACITY:usize=64','CAPACITY:usize=256')
  c=(ROOT/'tests/dma_lease_probe.c').read_text(encoding='utf-8').replace('requested<=32','requested<=128').replace('reset(ext,64,0)','reset(ext,256,0)').replace('invalid[]={0,33,','invalid[]={0,129,')
  marker='    const U invalid[]='
  extra='''    for(U ext=0;ext<2;ext++)for(U stage=1;stage<=3;stage++)for(U page=1;page<=128;page++){
        reset(ext,256,0);expected_pages=128;fail_stage=stage;fail_page=page;U out=99;Lease l;
        CK(dma_allocate(65,0x68000000,&out)==0x052a0001&&out==99&&dma_is_pinned());
        CK(dma_get(&l)==0&&l.pages==128&&l.state==1&&l.physical==(stage==1?0:0x200000));
        CK(l.attempted==(stage==1?0:page)&&l.mapped==(stage==1?0:page-1));
        Lease before=l;U oldcalls=calls;CK(dma_allocate(1,0x68000000,&out)==0x04060003&&calls==oldcalls);
        CK(dma_get(&l)==0&&!memcmp(&before,&l,sizeof l));
    }
'''
  self.assertEqual(1,c.count(marker));c=c.replace(marker,extra+marker)
  mutations={'unbounded':('requested > 128','requested > 256'),'premature-complete':('attempted:0,mapped:0,state:DMA_HELD','attempted:0,mapped:0,state:DMA_COMPLETE')}
  for mutation in (None,*mutations):
   for mode in ('debug','release'):
    d=self.out/'allocator'/(mutation or 'normal')/mode;d.mkdir(parents=True);actual=body
    if mutation:
     a,b=mutations[mutation];self.assertEqual(1,actual.count(a));actual=actual.replace(a,b)
    source=d/'dma_lease_fixture.dg';source.write_text(fixture.replace('// PRODUCTION_METADATA',metadata).replace('// PRODUCTION_CONTIGUOUS',actual),encoding='utf-8');shutil.copyfile(ROOT/'tests/dma_lease_adapter.dg',d/'dma_lease_adapter.dg')
    model=d/'allocator.c';model.write_text(c,encoding='utf-8');obj=self.assemble(source,[d,ROOT/'lang/std'],d,'allocator',mode);self.execute([obj],model,d,'allocator',mutation)

if __name__=='__main__':unittest.main(verbosity=2)

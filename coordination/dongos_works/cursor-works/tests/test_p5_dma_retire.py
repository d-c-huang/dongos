"""Real Dong mapping withdrawal, independent C page-table oracle; no guest boot."""
import hashlib,json,os,re,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tests.test_gui_font_portal import collect,boundaries,ROOT
from tests.test_framebuffer_ledger import RESOURCES
from tools.kernel_storage_profile import module_bytes
HERE=Path(__file__).resolve().parent
CAND=HERE.parent/'src/p5/dma-retire/user'
STARTUP='''module boot.memory_startup;
import mm.paging as paging;import mm.phys_buddy as buddy;import boot.runtime_view as runtime;
var SPACE:paging.Space=paging.EMPTY_SPACE;var POOL:[128]paging.Table=[paging.Table{entries:[0;512]};128];var META:[128]u8=[0;128];
var ALLOC:buddy.Allocator=buddy.EMPTY_ALLOCATOR;var VIEW:runtime.View=runtime.EMPTY_VIEW;
pub fn space_pointer()*paging.Space{unsafe{return &SPACE;}}pub fn allocator_pointer()*buddy.Allocator{unsafe{return &ALLOC;}}
pub fn runtime_pointer()*const runtime.View{unsafe{return &VIEW;}}
export("dr_kernel") fn setup()u64{unsafe{match paging.init(&SPACE,POOL[..],0x1000000,META[..],48,true){ok=>{return 0;},err(e)=>{return e;},}}}
export("dr_kernel_tables") fn tables()u64{unsafe{return &POOL[0] as u64;}}
'''
PAGING='''
var DR_FAIL:u64=0;var DR_CALLS:u64=0;
export("dr_fail_at") fn fail_at(n:u64)void{unsafe{DR_FAIL=n;DR_CALLS=0;}return;}
pub unsafe fn unmap_live(s:*Space,v:u64,r:*Retired)!void{unsafe{
 DR_CALLS+=1;if DR_FAIL!=0&&DR_CALLS==DR_FAIL{return error.errors.InvalidArgument;}
 return dr_real_unmap_live(s,v,r);
}}
'''
def reachable_probe(assembly):
 """Keep compiler-emitted reachable bodies verbatim; trap unused entry points.

 The entire graph has already passed Dong checking. Native roots include all
 fixture exports AND every function address in static data, then all body
 symbol references (calls and callback addresses). No tested body is rewritten.
 """
 cut=assembly.index('\nsection .rodata');code,data=assembly[:cut],assembly[cut:]
 starts=list(re.finditer(r'(?m)^align 16\n\$(\w+):\n',code))
 if not starts:raise AssertionError('missing generated function boundaries')
 bodies={m[1]:code[m.start():starts[i+1].start() if i+1<len(starts) else len(code)] for i,m in enumerate(starts)}
 refs=lambda s:set(re.findall(r'\$(\w+)',s))&bodies.keys()
 keep={name for name in bodies if name.startswith('dr_')}|refs(data)
 pending=list(keep)
 while pending:
  more=refs(bodies[pending.pop()])-keep;keep.update(more);pending.extend(more)
 result=code[:starts[0].start()]+''.join(body if name in keep else 'align 16\n$'+name+':\n    ud2\n' for name,body in bodies.items())+data
 return result,dict(kept=sorted(keep),trapped=sorted(bodies.keys()-keep))
class DmaRetireTests(unittest.TestCase):
 def test_actual_mapping_and_mutants(self):
  out=ROOT/'build/test/p5-dma-retire'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  inputs=[CAND/'memory.dg',CAND/'device_host.dg',HERE/'p5_dma_retire_fixture.dg',HERE/'p5_dma_retire_probe.c',Path(__file__),ROOT/'kernel/mm/paging.dg',ROOT/'kernel/mm/runtime_roots.dg',ROOT/'kernel/sched/user_bridge.dg',ROOT/'kernel/sched/user_domain.dg']
  before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};records=[]
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc,'native tools required')
  def run(args,d,label):
   p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=180)
   (d/(label+'.json')).write_text(json.dumps(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2));return p
  fragments=inputs[2].read_text().split('// HOST_FIXTURE');mem=fragments[0];host,bridge=fragments[1].split('// BRIDGE_FIXTURE')
  variants={'normal':None,'ignore-ack':('||atomic_load(&(*c).acknowledged)!=(*d).sequence','','barrier3'),
   'ignore-missing-alias':('if seen[n]!=3','if false','memory7'),
   'retry-allocation':('DMA_PREPARE_ATTEMPTED[id]=true;','DMA_PREPARE_ATTEMPTED[id]=false;','prepare-failure')}
  for mode,variant in ((m,v) for m in ('debug','release') for v in variants):
   d=out/(mode+'-'+variant);d.mkdir();stage=d/'source';overrides=boundaries();overrides.pop('irq.platform')
   overrides['boot.memory_startup']=STARTUP;overrides['boot.service_memory']=RESOURCES.replace('fb_allocate','dr_allocate').replace('pub bundle:Span','pub bundle:Span,pub arena:Span')+'\npub const ARENA_BASE:u64=0xffff_d400_0000_0000;\n'
   overrides['build.storage_profile']=module_bytes(7).decode()
   source=inputs[0].read_text()
   if variants[variant]:
    old,new,_=variants[variant];self.assertEqual(source.count(old),1);source=source.replace(old,new)
   overrides['user.memory']=source+'\n'+mem
   overrides['user.device_host']=inputs[1].read_text()+'\n'+host
   overrides['sched.user_bridge']=inputs[7].read_text()+'\n'+bridge
   pg=inputs[5].read_text();self.assertEqual(pg.count('pub unsafe fn unmap_live('),1)
   overrides['mm.paging']=pg.replace('pub unsafe fn unmap_live(','unsafe fn dr_real_unmap_live(')+PAGING
   collect(stage,['user.device_host'],overrides)
   c=compile_file(stage/'user/device_host.dg',roots=[stage],mode=mode)
   layouts={x['full_name']:x for x in c.layout_manifest['types']}
   self.assertEqual(layouts['user.memory.DmaLease']['size'],64)
   self.assertEqual(layouts['user.memory.DmaRetirementView']['size'],80)
   (d/'layout.json').write_text(json.dumps(c.layout_manifest,indent=2))
   (d/'full-probe.asm').write_text(c.assembly)
   native,reach=reachable_probe(c.assembly);(d/'reachability.json').write_text(json.dumps(reach,indent=2))
   asm=d/'probe.asm';asm.write_text(native)
   mocked={'__dong_panic','dr_allocate','user_current_root','user_smp_arch_if0','user_smp_arch_cpu','user_shared_barrier'}
   externs={m.group(1).lstrip('$') for m in re.finditer(r'^extern (\$?\w+)',c.assembly,re.M)}-mocked
   stub=d/'unused.asm';stub.write_text('bits 64\nsection .text\n'+''.join('global $'+x+'\n$'+x+': ud2\n' for x in sorted(externs)))
   objects=[]
   for label,file in [('probe',asm),('unused',stub)]:
    obj=d/(label+'.o');objects.append(obj);r=run([nasm,'-O0','-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),file,'-o',obj],d,label);self.assertEqual(r.returncode,0,r.stderr)
   exe=d/('probe.exe' if os.name=='nt' else 'probe');r=run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-strict-aliasing',* ([] if os.name=='nt' else ['-no-pie']),inputs[3],*objects,'-o',exe],d,'link');self.assertEqual(r.returncode,0,r.stderr)
   cases=['normal','unprepared','prepare-failure','prepare-partial','prepare-zero']+[prefix+str(n) for prefix,count in [('prepare-host',8),('prepare-domain',5)] for n in range(1,count+1)]+[prefix+str(n) for prefix,count in [('host',8),('memory',10),('domain',5),('barrier',5),('unmap',4)] for n in range(1,count+1)] if variant=='normal' else [variants[variant][2]]
   for case in cases:
    r=run([exe,case],d,case);self.assertEqual(r.returncode,0 if variant=='normal' else 1,r.stdout+r.stderr)
    if variant!='normal':self.assertIn('retire check failed line',r.stderr)
    records.append(dict(mode=mode,variant=variant,case=case,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
  self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
  (out/'summary.json').write_text(json.dumps(dict(passed=True,source_sha256=before,records=records,hardware_mocked=True,guest_boots=0),indent=2))
  print('P5_DMA_RETIRE_EVIDENCE',out)

 def test_production_module_graph(self):
  out=ROOT/'build/test/p5-dma-retire'/('graph-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  collect(out,['user.device_host'],{name:(CAND/(name.split('.')[-1]+'.dg')).read_text() for name in ('user.memory','user.device_host')})
  for mode in ('debug','release'):
   c=compile_file(out/'user/device_host.dg',roots=[out],mode=mode);(out/(mode+'.asm')).write_text(c.assembly)

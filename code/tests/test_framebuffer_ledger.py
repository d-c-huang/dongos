"""Native real memory/paging ledger; only physical allocation and CPU boundaries mocked."""
import hashlib,json,os,re,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tests.test_gui_font_portal import collect,boundaries
from tools.kernel_storage_profile import module_bytes
ROOT=Path(__file__).resolve().parents[1]
STARTUP="""module boot.memory_startup;
import mm.paging as paging;import mm.phys_buddy as buddy;import boot.runtime_view as runtime;import boot.abi as abi;
var SPACE:paging.Space=paging.EMPTY_SPACE;var POOL:[128]paging.Table=[paging.Table{entries:[0;512]};128];var META:[128]u8=[0;128];
var ALLOC:buddy.Allocator=buddy.EMPTY_ALLOCATOR;var VIEW:runtime.View=runtime.EMPTY_VIEW;
pub fn space_pointer()*paging.Space{unsafe{return &SPACE;}}pub fn allocator_pointer()*buddy.Allocator{unsafe{return &ALLOC;}}
pub fn runtime_pointer()*const runtime.View{unsafe{return &VIEW;}}
export("fb_kernel") fn setup(raw:u64)u64{unsafe{
 VIEW.boot_info=raw;VIEW.display.framebuffer_base=0xffff800004000003;VIEW.display.framebuffer_size=8192;
 match paging.init(&SPACE,POOL[..],0x1000000,META[..],48,true){ok=>{},err(e)=>{return e;},}
 var off:u64=0;while off<12288{match paging.map_live(&SPACE,0xffff800004000000+off,0x4000000+off,paging.WRITE|paging.WRITE_COMBINING){ok=>{},err(e)=>{return e;},}off+=4096;}
 return 0;
}}
export("fb_kernel_tables") fn tables()u64{unsafe{return &POOL[0] as u64;}}
"""
RESOURCES="""module boot.service_memory;import exec.bundle as bundle;pub error Invalid=0x0f010001;
pub const BUNDLE_BASE:u64=0xffff_d800_0000_0000;pub struct Block{pub physical:u64,pub virtual:u64,pub pages:usize}
pub struct Span{pub physical:u64,pub length:u64}pub struct Plan{pub bundle:Span}
unsafe extern "sysv64" fn fb_allocate(pages:usize,alignment:usize,out:*Block)u64;
pub unsafe fn allocate(pages:usize,alignment:usize,out:*Block)!void{unsafe{if fb_allocate(pages,alignment,out)!=0{return error.Invalid;}}return;}
pub unsafe fn reserve(pages:usize,alignment:usize,out:*Block)!void{return error.Invalid;}
pub unsafe fn find(name:[]const u8,out:*bundle.Contents)!void{return error.Invalid;}pub fn plan_pointer()*const Plan{return null;}
"""
PAGING="""
var FB_MAP_FAIL:u64=0;var FB_MAP_COUNT:u64=0;
export("fb_map_fail") fn fail_at(n:u64)void{unsafe{FB_MAP_FAIL=n;FB_MAP_COUNT=0;}return;}
pub unsafe fn map_live(s:*Space,v:u64,p:u64,f:u64)!void{unsafe{
 FB_MAP_COUNT+=1;if FB_MAP_FAIL!=0&&FB_MAP_COUNT==FB_MAP_FAIL{return error.errors.InvalidArgument;}
 return fb_real_map_live(s,v,p,f);
}}
"""
class LedgerTests(unittest.TestCase):
 def test_native_ledger_lifecycle(self):
  out=ROOT/'build/test/framebuffer-ledger'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  inputs=[ROOT/x for x in ('kernel/user/memory.dg','kernel/mm/paging.dg','kernel/mm/runtime_roots.dg','tests/framebuffer_ledger_probe.dg','tests/framebuffer_ledger_probe.c','tests/test_framebuffer_ledger.py')]
  before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};records=[]
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
  def run(args,d,label):
   p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=90)
   (d/(label+'.json')).write_text(json.dumps(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2));return p
  variants={
   'normal':None,
   'no-held':('(*ledger).held=1;','(*ledger).held=0;','partial'),
   'view-instead-of-raw':('let base=(*raw).framebuffer_base as u64;','let base=(*view).display.framebuffer_base-0xffff800000000000;','raw-mismatch'),
   'hidden-extra-alias':('||(*ledger).report.aliases!=(*ledger).snapshot.count as u64','','hidden'),
   'retire-early':('(*ledger).held=2;(*ledger).journal=a;','(*ledger).held=0;(*ledger).journal=a;','normal'),
   'allow-external-gop':('if WC_FRAMEBUFFER_PHYSICAL!=0&&first<','if WC_FRAMEBUFFER_PHYSICAL==0&&first<','normal'),
  }
  for mode,variant in ((m,v) for m in ('debug','release') for v in variants):
   d=out/(mode+'-'+variant);d.mkdir();stage=d/'source';overrides=boundaries()
   overrides['boot.memory_startup']=STARTUP;overrides['boot.service_memory']=RESOURCES
   overrides['build.storage_profile']=module_bytes(7).decode()
   source=inputs[0].read_text()
   if variants[variant]:
    old,new,_=variants[variant];self.assertEqual(source.count(old),1);source=source.replace(old,new)
   overrides['user.memory']=source+'\n'+inputs[3].read_text()
   pg=inputs[1].read_text();self.assertEqual(pg.count('pub unsafe fn map_live('),1)
   overrides['mm.paging']=pg.replace('pub unsafe fn map_live(','unsafe fn fb_real_map_live(')+PAGING
   collect(stage,['user.memory'],overrides)
   c=compile_file(stage/'user/memory.dg',roots=[stage],mode=mode)
   layouts={x['full_name']:x for x in c.layout_manifest['types']}
   self.assertEqual(layouts['user.memory.FramebufferSnapshot']['size'],4128)
   (d/'layout.json').write_text(json.dumps(c.layout_manifest,indent=2))
   asm=d/'probe.asm';asm.write_text(c.assembly)
   mocked={'__dong_panic','fb_allocate','user_current_root','user_pcid_flush_all','user_pcid_unbind','user_pcid_bind','runtime_invalidate','runtime_flush_root','runtime_copy_bytes','user_pcid_invalidate_root'}
   externs={m.group(1).lstrip('$') for m in re.finditer(r'^extern (\$?\w+)',c.assembly,re.M)}-mocked
   stub=d/'unused.asm';stub.write_text('bits 64\nsection .text\n'+''.join('global $'+x+'\n$'+x+': ud2\n' for x in sorted(externs)))
   objects=[]
   for label,file in [('probe',asm),('unused',stub)]:
    obj=d/(label+'.o');objects.append(obj);r=run([nasm,'-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),file,'-o',obj],d,label);self.assertEqual(r.returncode,0,r.stderr)
   exe=d/('probe.exe' if os.name=='nt' else 'probe');r=run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-strict-aliasing',* ([] if os.name=='nt' else ['-no-pie']),inputs[4],*objects,'-o',exe],d,'link');self.assertEqual(r.returncode,0,r.stderr)
   cases=('normal','abort','hidden','partial','overflow','raw-mismatch','retire-failed','root-change','transition','hhdm-overflow') if variant=='normal' else (variants[variant][2],)
   for case in cases:
    r=run([exe,case],d,case);self.assertEqual(r.returncode,0 if variant=='normal' else 1,r.stdout+r.stderr)
    if variant!='normal':self.assertIn('ledger check failed line',r.stderr)
    records.append(dict(mode=mode,variant=variant,case=case,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
  self.assertEqual(before,{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
  (out/'summary.json').write_text(json.dumps(dict(passed=True,source_sha256=before,records=records,hardware_mocked=True,guest_boots=0),indent=2))
  print('FRAMEBUFFER_LEDGER_EVIDENCE',out)



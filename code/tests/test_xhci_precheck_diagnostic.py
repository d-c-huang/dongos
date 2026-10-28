"""Execute actual precheck and the service's actual failure formatter."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,unittest,uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
ROOT=Path(__file__).resolve().parents[1]
class PrecheckDiagnosticTests(unittest.TestCase):
 def test_actual_decision_samples_and_failure_log(self):
  paths=[ROOT/'services/usb/xhci_controller.dg',ROOT/'services/drivers/xhci_service.dg',ROOT/'tests/xhci_precheck_diagnostic_probe.c',Path(__file__),*(ROOT/'services/usb'/n for n in ('xhci_dma.dg','xhci_trb.dg','xhci_ring.dg'))]
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  before={str(p):sha(p) for p in paths};out=ROOT/'build/test/xhci-precheck'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
  source=paths[0].read_text(encoding='utf-8');service=paths[1].read_text(encoding='utf-8')
  formatter=service[service.index('unsafe fn hex('):service.index('unsafe fn describe(')]
  start=service.index('let check=controller.precheck_report();')
  body=service[start:service.index('return e;},}',start)+len('return e;')].replace('controller.precheck_report()','precheck_report()')
  suffix='''
var STATE:State=EMPTY_STATE;
export("xhp_check") unsafe fn check_actual(ops:*const Ops,context:u64,s:*const Setup,out:*Caps)u64{unsafe{match precheck(ops,context,s,out){ok=>{return 0;},err(e)=>{return e;},}}}
export("xhp_report") fn report_actual()*const PrecheckReport{return precheck_report();}
'''+formatter+'\nexport("xhp_emit") fn emit_actual(e:u64)u64{unsafe{'+body+'}}\n'
  mutations={
   'wrong-reason':('rejected(10,offset,header as u64,0)','rejected(11,offset,header as u64,0)'),
   'wrong-sample':('PRECHECK_VALUE=value as u64','PRECHECK_VALUE=value as u64+1'),
   'stale-record':('PRECHECK=EMPTY_PRECHECK;PRECHECK_VALUE=0;','PRECHECK_VALUE=0;'),
   'missing-value-log':('hex("xhci_value=0x",(*check).value);',''),
  }
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc);results=[]
  for variant in ('normal',*mutations):
   for mode in ('debug','release'):
    d=out/variant/mode;stage=d/'services';(stage/'usb').mkdir(parents=True);(stage/'lib').mkdir()
    for p in paths[4:]:shutil.copyfile(p,stage/'usb'/p.name)
    text=source.replace('module usb.xhci_controller;','module usb.xhci_controller;\nimport lib.sys as sys;')+suffix
    if variant!='normal':a,b=mutations[variant];self.assertEqual(1,text.count(a));text=text.replace(a,b)
    p=stage/'usb/xhci_controller.dg';p.write_text(text,encoding='utf-8')
    (stage/'lib/sys.dg').write_text('module lib.sys;\nunsafe extern "sysv64" fn record_log(p:*const u8,n:u64)u64;\npub unsafe fn log(s:[]const u8)u64{unsafe{return record_log(s.ptr,s.len as u64);}}\n',encoding='utf-8')
    c=compile_file(p,roots=[stage],mode=mode);layout={t['full_name']:t for t in c.layout_manifest['types']}
    for n,size in {'PrecheckReport':40,'Setup':112,'Caps':328,'State':1280}.items():self.assertEqual(size,layout['usb.xhci_controller.'+n]['size'])
    asm=d/'probe.asm';asm.write_text(c.assembly,encoding='utf-8')
    def run(args,label,expected=0):
     r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=120);(d/(label+'.json')).write_text(json.dumps(dict(args=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2)+'\n',encoding='utf-8');self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
    for fmt in ('elf64','win64'):run([nasm,'-f',fmt,*nasm_flags(nasm),'-o',d/(fmt+'.o'),asm],'assemble-'+fmt)
    for opt in ('-O0','-O2') if variant=='normal' else ('-O2',):
     exe=d/('probe'+opt+'.exe');run([cc,'-std=c11',opt,'-Wall','-Wextra','-Werror','-mno-sse',paths[2],d/('win64.o' if os.name=='nt' else 'elf64.o'),'-o',exe],'link'+opt)
     r=run([exe],'native'+opt,0 if variant=='normal' else 1);self.assertIn('PRECHECK_DIAGNOSTIC_OK' if variant=='normal' else 'PRECHECK_ASSERT',r.stdout+r.stderr);self.assertNotIn('unexpected panic',r.stderr);results.append(dict(variant=variant,mode=mode,optimization=opt,stdout=r.stdout,stderr=r.stderr))
  self.assertEqual(before,{str(p):sha(p) for p in paths});(out/'result.json').write_text(json.dumps(dict(passed=True,source_stable=True,skips=0,sources=before,results=results),indent=2)+'\n',encoding='utf-8');print('PRECHECK_DIAGNOSTIC_EVIDENCE',out)
if __name__=='__main__':unittest.main(verbosity=2)

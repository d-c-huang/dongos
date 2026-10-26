"""Real capability decoding and private guard/map/load native oracles."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest
import uuid
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags,tool
from tests.test_xhci_kernel import dependencies
from tests.test_ecam_mmio import declarations,function
from tests.test_service_ipc_cancellation import block
from tools import build_xhci_capability_probe as builder

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('version','done','error_code','flags','bar_physical','pci_command','cap0','hcs1','hcs2','hcc1','db_off','rt_off','hcc2','operational','pagesize','usbcmd','usbsts','extended_first','extended_count','legacy_offset','legacy_support','legacy_control','protocols2','protocols3','unsupported_first','scratchpads','context_bytes','ac64','reject_mask','inventory_error','read_count','reserved')
CAP_RESET='\nexport("xhci_caps_reset") fn native_reset()void{unsafe{STATE=EMPTY;}return;}\n'
MAP_RESET='''
export("xhci_map_reset") fn reset(limit:u64,current:u64,cache:u64)void{unsafe{
 PHYSICAL_LIMIT=limit;REGION_BASE=0xe0000000;REGION_FIRST=0;REGION_LAST=255;
 CURRENT_PAGE=current;USB_CAPABILITY_PAGE=cache;PCI_CONFLICT=EMPTY_CONFIGURATION_CONFLICT;
}return;}
export("xhci_map_read") fn native_read(pa:u64,offset:u64,out:*u32)u64{unsafe{
 match usb_capability_read32(pa,offset){ok(value)=>{*out=value;return 0;},err(e)=>{return e;},}
}}
export("xhci_map_current") fn current()u64{unsafe{return CURRENT_PAGE;}}
export("xhci_map_cache") fn cached()u64{unsafe{return USB_CAPABILITY_PAGE;}}
export("xhci_map_conflict") fn context()*const ConfigurationConflict{unsafe{return &PCI_CONFLICT;}}
'''
MAP_STUBS={
 'boot.memory_startup':'''module boot.memory_startup;
import boot.runtime_view as runtime;
import mm.paging as paging;
pub extern "sysv64" ("xhci_map_host_view") fn runtime_pointer()*const runtime.View;
pub extern "sysv64" ("xhci_map_host_space") fn space_pointer()*paging.Space;
''',
 'boot.device_memory':'''module boot.device_memory;
pub extern "sysv64" ("xhci_map_host_invalidate") fn runtime_invalidate(address:u64)void;
''',
 'mm.paging':'''module mm.paging;
pub const WRITE:u64=1;pub const UNCACHED:u64=8;
pub struct Space{pub words:[8]u64}
pub error Injected=0x0203_0999;
unsafe extern "sysv64" ("xhci_map_host_map") fn effect(s:*Space,va:u64,pa:u64,flags:u64,replace:u64)u64;
pub unsafe fn map_live(s:*Space,va:u64,pa:u64,flags:u64)!void{unsafe{if effect(s,va,pa,flags,0)!=0{return error.Injected;}}return;}
pub unsafe fn replace_live(s:*Space,va:u64,pa:u64,flags:u64)!void{unsafe{if effect(s,va,pa,flags,1)!=0{return error.Injected;}}return;}
'''}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def replace_once(source,old,new,label):
    if source.count(old)!=1:raise AssertionError('unique actual mutation anchor required: '+label)
    return source.replace(old,new,1)

def cap_mutation(source,kind):
    if kind=='read-cross-page':
        source=replace_once(source,'if (offset&3)!=0||offset>4092','if (offset&3)!=0',kind+'-inner')
        return replace_once(source,'if offset>4096-bytes{STATE.flags|=256;return;}','if false{STATE.flags|=256;return;}',kind+'-structure')
    rules={
      'wrong-scratch':('STATE.hcs2>>27','STATE.hcs2>>26'),
      'ignore-bios':('(header&0xfeff_0000)!=0','false'),
      'ignore-os-bit':('(header&0x0100_0000)==0','false'),
      'read-partial-extension':('if offset>4096-bytes{STATE.flags|=256;return;}','if false{STATE.flags|=256;return;}'),
      'repeat-run':('if STATE.version!=0{return &STATE;}','if false{return &STATE;}'),
      'unknown-payload-read':('STATE.flags|=16384;STATE.reject_mask|=128;','STATE.flags|=16384;STATE.reject_mask|=128;let ignored=try read(offset+4);'),
      'count-failed-as-success':('STATE.read_count+=1;','STATE.read_count+=2;'),
    }
    return replace_once(source,*rules[kind],kind)

def guarded_caps_assembly(assembly):
    symbol='__dg_m'+b'boot.xhci_capability_probe'.hex()+'_g'+b'STATE'.hex()
    lines=assembly.splitlines(keepends=True);found=[i for i,line in enumerate(lines) if line.strip().lstrip('$')==symbol+':']
    if len(found)!=1:raise AssertionError('one actual capability STATE required')
    at=found[0]
    if not re.fullmatch(r'\s*(?:resb\s+256|times\s+256\s+db\s+0)\s*\n?',lines[at+1]):raise AssertionError('actual STATE allocation geometry differs')
    return ''.join(lines[:at])+'global xhci_caps_canary_low\nxhci_caps_canary_low: resq 4\n'+''.join(lines[at:at+2])+'global xhci_caps_canary_high\nxhci_caps_canary_high: resq 4\n'+''.join(lines[at+2:])

def map_source(original,kind):
    functions={name:function(original,name) for name in ('raw64','record_configuration_denied','mmio_range')}
    extra=builder.APPEND_SOURCE
    if kind=='allow-runtime':functions['mmio_range']=replace_once(functions['mmio_range'],'!runtime_ecam','false',kind)
    elif kind=='allow-ram':functions['mmio_range']=replace_once(functions['mmio_range'],'kind != 11 && !reserved_ecam && !reserved_pci','kind != 11 && kind != 7 && !reserved_ecam && !reserved_pci',kind)
    elif kind=='write-map-flags':
        if extra.count('paging.UNCACHED);')!=2:raise AssertionError('two actual RO map flags expected')
        extra=extra.replace('paging.UNCACHED);','paging.WRITE|paging.UNCACHED);')
    elif kind=='omit-guard':extra=replace_once(extra,'try mmio_range(physical,4096,false);','',kind)
    elif kind=='omit-forced-ro':extra=replace_once(extra,'USB_CAPABILITY_PAGE!=physical||CURRENT_PAGE!=physical','CURRENT_PAGE!=physical',kind)
    elif kind=='late-guard':
        extra=replace_once(extra,'try mmio_range(physical,4096,false);','',kind)
        extra=replace_once(extra,'return volatile_load((WINDOW+offset) as *const u32);','try mmio_range(physical,4096,false);\n return volatile_load((WINDOW+offset) as *const u32);',kind)
    elif kind!='normal':raise AssertionError(kind)
    extra=replace_once(extra,'return volatile_load((WINDOW+offset) as *const u32);','return native_load(WINDOW+offset);','sole final volatile-load boundary')
    window=re.search(r'(?m)^const WINDOW:\s*u64\s*=\s*([^;]+);',original)
    if not window:raise AssertionError('actual configuration WINDOW missing')
    prefix='''module xhci_map_probe;
import boot.memory_startup as startup;
import boot.device_memory as devices;
import mm.paging as paging;
pub error Invalid=0x050a_0001;pub error Denied=0x050a_0002;
var REGION_BASE:u64=0;var REGION_FIRST:u64=0;var REGION_LAST:u64=0;var PHYSICAL_LIMIT:u64=0;var CURRENT_PAGE:u64=0;
unsafe extern "sysv64" ("xhci_map_host_load") fn native_load(address:u64)u32;
'''
    return prefix+'const WINDOW:u64='+window[1]+';\n'+declarations(original)+'\n'+'\n'.join(functions.values())+'\n'+extra+MAP_RESET

class XhciCapabilityProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/'build/test/xhci-capability'/('run-'+uuid.uuid4().hex[:12]);cls.out.mkdir(parents=True)
        cls.paths={Path(__file__).resolve(),ROOT/'tests/xhci_capability_probe.c',ROOT/'tools/build_xhci_capability_probe.py'}
        for tree in ('kernel','lang/std','lang/examples'):cls.paths.update((ROOT/tree).rglob('*.dg'))
        cls.paths.update((ROOT/'lang/dongc').rglob('*.py'))
        cls.before={p.relative_to(ROOT).as_posix():digest(p) for p in cls.paths};save(cls.out/'source-before.json',cls.before)
        cls.results=[];cls.completed=[]
    @classmethod
    def tearDownClass(cls):
        after={p.relative_to(ROOT).as_posix():digest(p) for p in cls.paths};save(cls.out/'source-after.json',after)
        if after!=cls.before:raise AssertionError('capability source/probe/compiler changed')
        if cls.completed==['capability','map']:
            save(cls.out/'validation-summary.json',dict(passed=True,skips=0,source_stable=True,source_sha256=after,actual_capability_module=True,
              actual_private_reader_and_mmio_guard=True,actual_hardware_io=False,configuration_or_mmio_writes=0,results=cls.results))
            print('XHCI_CAPABILITY_EVIDENCE',cls.out)
    def execute(self,command,where,label):
        command=list(map(str,command));r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90)
        save(where/(label+'.json'),dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));return r
    def native(self,family,variant,mode,compiled):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc,'real native toolchain required; no skips')
        where=self.out/family/variant/mode;where.mkdir(parents=True,exist_ok=True)
        save(where/'layout.json',compiled.layout_manifest);types={t['full_name']:t for t in compiled.layout_manifest['types']}
        if family=='capability':
            report=types['boot.xhci_capability_probe.Report'];self.assertEqual((256,8),(report['size'],report['alignment']))
            self.assertEqual([(name,i*8,'u64') for i,name in enumerate(FIELDS)],[(f['name'],f['offset'],f['type']) for f in report['fields']])
            self.assertEqual(232,types['boot.usb_preflight.Report']['size']);assembly=guarded_caps_assembly(compiled.assembly)
        else:
            self.assertEqual(160,types['boot.runtime_view.View']['size']);self.assertEqual(48,types['boot.runtime_view.Display']['size']);assembly=compiled.assembly
        self.assertNotRegex('\n'.join(line.split(';',1)[0] for line in assembly.splitlines()),r'(?mi)^\s*(?:in|out|invlpg|rdmsr|wrmsr|cli|sti|hlt)\b')
        asm=where/'probe.asm';asm.write_text(assembly,encoding='utf-8');obj=where/'probe.o'
        for fmt in ('elf64','win64'):
            target=obj if fmt==('win64' if os.name=='nt' else 'elf64') else where/(fmt+'.o')
            r=self.execute([nasm,'-f',fmt,*nasm_flags(nasm),'-o',target,asm],where,'assemble-'+fmt);self.assertEqual(0,r.returncode,r.stdout+r.stderr)
        for optimization in ('-O0','-O2') if variant=='normal' else ('-O2',):
            binary=where/('probe'+optimization+('.exe' if os.name=='nt' else ''))
            r=self.execute([cc,'-std=c11',optimization,'-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',*(['-DXHCI_MAP_ORACLE=1'] if family=='map' else []),*(['-mno-sse'] if os.name=='nt' else ['-no-pie']),ROOT/'tests/xhci_capability_probe.c',obj,'-o',binary],where,'link'+optimization);self.assertEqual(0,r.returncode,r.stdout+r.stderr)
            r=self.execute([binary],where,'native'+optimization)
            if variant=='normal':self.assertEqual(0,r.returncode,r.stdout+r.stderr);self.assertIn('XHCI_'+('MAP' if family=='map' else 'CAPS')+'_NATIVE_OK',r.stdout)
            else:self.assertEqual(1,r.returncode,r.stdout+r.stderr);self.assertIn('XHCI_CAPS_ASSERT',r.stderr);self.assertNotRegex(r.stderr.lower(),r'panic|segmentation|access violation')
            self.results.append(dict(family=family,variant=variant,mode=mode,optimization=optimization,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,assembly_sha256=digest(asm)))
    def test_actual_capability_decoder_and_bad_bodies(self):
        original=(ROOT/'kernel/boot/xhci_capability_probe.dg').read_text(encoding='utf-8');inventory=(ROOT/'kernel/boot/usb_preflight.dg').read_text(encoding='utf-8')
        inventory_stub='module boot.usb_preflight;\n'+block(inventory,'pub struct Report')+'''\n
pub extern "sysv64" ("xhci_caps_host_inventory") fn run()*const Report;
pub fn pointer()*const Report{unsafe{return run();}}
'''
        stubs={'boot.usb_preflight':inventory_stub,'user.devices':'''module user.devices;
pub error Injected=0x050a_0002;
unsafe extern "sysv64" ("xhci_caps_host_pci") fn pci(address:u64,out:*u32)u64;
unsafe extern "sysv64" ("xhci_caps_host_mmio") fn mmio(physical:u64,offset:u64,out:*u32)u64;
pub unsafe fn configuration_read(address:u64)!u32{unsafe{var v:u32=0;if pci(address,&v)!=0{return error.Injected;}return v;}}
pub unsafe fn usb_capability_read32(physical:u64,offset:u64)!u32{unsafe{var v:u32=0;if mmio(physical,offset,&v)!=0{return error.Injected;}return v;}}
'''}
        for variant in ('normal','wrong-scratch','ignore-bios','ignore-os-bit','read-partial-extension','read-cross-page','repeat-run','unknown-payload-read','count-failed-as-success'):
            for mode in ('debug','release'):
                stage=self.out/'capability'/variant/mode/'source'
                source=original if variant=='normal' else cap_mutation(original,variant)
                dependencies(stage,['boot.xhci_capability_probe'],{**stubs,'boot.xhci_capability_probe':source+CAP_RESET})
                self.assertEqual(source+CAP_RESET,(stage/'boot/xhci_capability_probe.dg').read_text(encoding='utf-8'))
                compiled=compile_file(stage/'boot/xhci_capability_probe.dg',roots=[stage],mode=mode)
                self.native('capability',variant,mode,compiled)
        self.completed.append('capability')
    def test_private_reader_actual_guard_map_load_and_bad_bodies(self):
        original=(ROOT/'kernel/user/devices.dg').read_text(encoding='utf-8')
        for variant in ('normal','allow-runtime','allow-ram','write-map-flags','omit-guard','omit-forced-ro','late-guard'):
            for mode in ('debug','release'):
                stage=self.out/'map'/variant/mode/'source'
                text=map_source(original,variant);dependencies(stage,['boot.memory_startup','boot.device_memory','mm.paging'],MAP_STUBS)
                source=stage/'xhci_map_probe.dg';source.write_text(text,encoding='utf-8')
                compiled=compile_file(source,roots=[stage],mode=mode);self.native('map',variant,mode,compiled)
        self.completed.append('map')

if __name__=='__main__':unittest.main(verbosity=2)

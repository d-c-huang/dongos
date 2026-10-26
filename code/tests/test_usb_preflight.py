"""Execute the real once-only USB inventory with PCI-read/View boundaries."""
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

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('version','done','error_code','flags','xhci_count','ehci_count','ohci_count','uhci_count','other_count','pci_count','usb_counts','ecam','identity','class_code','header','bar0','bar1','bar_physical','descriptor_found','descriptor_index','descriptor_type','descriptor_base','descriptor_pages','descriptor_attributes','framebuffer_base','framebuffer_bytes','mcfg_base','mcfg_first','mcfg_last')
RESET='''
// Test-only reset between independent hardware epochs; production has no reset.
export("usb_preflight_reset") fn native_reset()void{unsafe{STATE=EMPTY;}return;}
'''
STUBS={
 'boot.memory_startup':'''module boot.memory_startup;
import boot.runtime_view as runtime;
pub extern "sysv64" ("usb_info_runtime_view") fn runtime_pointer()*const runtime.View;
''',
 'user.devices':'''module user.devices;
pub error Injected=0x050a_0002;
pub extern "sysv64" ("usb_info_region_base") fn region_base()u64;
pub extern "sysv64" ("usb_info_region_first") fn region_first()u64;
pub extern "sysv64" ("usb_info_region_last") fn region_last()u64;
unsafe extern "sysv64" ("usb_info_configuration_read") fn native_read(address:u64,out:*u32)u64;
pub unsafe fn configuration_read(address:u64)!u32{unsafe{
 var value:u32=0;if native_read(address,&value)!=0{return error.Injected;}return value;
}}
'''}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def mutation(source,kind):
    rules={
      'truncate-attributes':('let attrs=raw64(raw,at+32);','let attrs=(raw64(raw,at+32) as u32) as u64;'),
      'omit-bar-high':('physical|=STATE.bar1<<32;','physical|=0;'),
      'wrong-usb-class':('(class_code&0xffff00)==0x0c0300','(class_code&0xffff00)==0x0c0200'),
      'wrong-ehci-counter':('STATE.ehci_count+=1;','STATE.xhci_count+=1;'),
      'last-xhci-wins':('(header&127)==0&&(STATE.flags&1)==0','(header&127)==0'),
      'fb-touch-is-overlap':('page<STATE.framebuffer_base+STATE.framebuffer_bytes&&STATE.framebuffer_base<page+4096','page<=STATE.framebuffer_base+STATE.framebuffer_bytes&&STATE.framebuffer_base<=page+4096'),
      'repeat-scan':('if STATE.version!=0{return &STATE;}','if false{return &STATE;}'),
      'omit-done':('compiler_fence();STATE.done=1;','compiler_fence();'),
      'wrap-packed-count':('if value>65535{STATE.flags|=2048;return 65535;}','if value>65535{STATE.flags|=2048;return value&65535;}'),
    }
    old,new=rules[kind]
    if source.count(old)!=1:raise AssertionError('unique actual bad-body anchor changed: '+kind)
    return source.replace(old,new,1)

def guarded_assembly(assembly):
    # Add storage canaries around the actual compiler-owned STATE allocation;
    # every instruction and the real 232-byte object itself remain unchanged.
    symbol='__dg_m'+b'boot.usb_preflight'.hex()+'_g'+b'STATE'.hex()
    lines=assembly.splitlines(keepends=True);matches=[i for i,s in enumerate(lines) if s.strip().lstrip('$')==symbol+':']
    if len(matches)!=1:raise AssertionError('one actual private STATE allocation required')
    at=matches[0];following=lines[at+1]
    if not re.fullmatch(r'\s*(?:resb\s+232|times\s+232\s+db\s+0)\s*\n?',following):
        raise AssertionError('actual STATE allocation geometry differs: '+repr(following))
    before='global usb_preflight_report_canary_low\nusb_preflight_report_canary_low: resq 4\n'
    after='global usb_preflight_report_canary_high\nusb_preflight_report_canary_high: resq 4\n'
    return ''.join(lines[:at])+before+''.join(lines[at:at+2])+after+''.join(lines[at+2:])

class UsbPreflightTests(unittest.TestCase):
    def test_actual_whole_module_reads_reports_bounds_and_bad_bodies(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native USB inventory needs real NASM/GCC, no skips')
        out=ROOT/'build/test/usb-preflight'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        paths={Path(__file__).resolve(),ROOT/'tests/usb_preflight_probe.c'}
        for tree in ('kernel','lang/std','lang/examples'):
            paths.update((ROOT/tree).rglob('*.dg'))
        paths.update((ROOT/'lang/dongc').rglob('*.py'))
        before={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
        original=(ROOT/'kernel/boot/usb_preflight.dg').read_text(encoding='utf-8')
        self.assertEqual(1,original.count('var STATE:Report=EMPTY;'))
        variants=('normal','truncate-attributes','omit-bar-high','wrong-usb-class','wrong-ehci-counter','last-xhci-wins','fb-touch-is-overlap','repeat-scan','omit-done','wrap-packed-count')
        results=[]
        def execute(command,where,label):
            command=list(map(str,command));r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90)
            save(where/(label+'.json'),dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));return r
        for variant in variants:
            for mode in ('debug','release'):
                where=out/variant/mode;stage=where/'source';where.mkdir(parents=True)
                source=original if variant=='normal' else mutation(original,variant)
                overrides={**STUBS,'boot.usb_preflight':source+RESET}
                dependencies(stage,['boot.usb_preflight'],overrides)
                self.assertEqual(source+RESET,(stage/'boot/usb_preflight.dg').read_text(encoding='utf-8'))
                compiled=compile_file(stage/'boot/usb_preflight.dg',roots=[stage],mode=mode)
                save(where/'layout.json',compiled.layout_manifest)
                types={t['full_name']:t for t in compiled.layout_manifest['types']}
                report=types['boot.usb_preflight.Report'];self.assertEqual((232,8),(report['size'],report['alignment']))
                self.assertEqual([(name,i*8,'u64') for i,name in enumerate(FIELDS)],[(f['name'],f['offset'],f['type']) for f in report['fields']])
                self.assertEqual(160,types['boot.runtime_view.View']['size']);self.assertEqual(48,types['boot.runtime_view.Display']['size'])
                instructions='\n'.join(line.split(';',1)[0] for line in compiled.assembly.splitlines())
                self.assertNotRegex(instructions,r'(?mi)^\s*(?:in|out|invlpg|rdmsr|wrmsr|cli|sti|hlt)\b')
                guarded=guarded_assembly(compiled.assembly)
                asm=where/'probe.asm';asm.write_text(guarded,encoding='utf-8');obj=where/'probe.o'
                for fmt in ('elf64','win64'):
                    target=obj if fmt==('win64' if os.name=='nt' else 'elf64') else where/(fmt+'.o')
                    r=execute([nasm,'-f',fmt,*nasm_flags(nasm),'-o',target,asm],where,'assemble-'+fmt)
                    self.assertEqual(0,r.returncode,r.stdout+r.stderr)
                for optimization in ('-O0','-O2') if variant=='normal' else ('-O2',):
                    binary=where/('probe'+optimization+('.exe' if os.name=='nt' else ''))
                    r=execute([cc,'-std=c11',optimization,'-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',*(['-mno-sse'] if os.name=='nt' else ['-no-pie']),ROOT/'tests/usb_preflight_probe.c',obj,'-o',binary],where,'link'+optimization)
                    self.assertEqual(0,r.returncode,r.stdout+r.stderr)
                    r=execute([binary],where,'native'+optimization)
                    if variant=='normal':
                        self.assertEqual(0,r.returncode,r.stdout+r.stderr);self.assertIn('USB_PREFLIGHT_NATIVE_OK',r.stdout)
                    else:
                        self.assertEqual(1,r.returncode,r.stdout+r.stderr);self.assertIn('USB_PREFLIGHT_ASSERT',r.stderr)
                        self.assertNotRegex(r.stderr.lower(),r'panic|segmentation|access violation')
                    results.append(dict(variant=variant,mode=mode,optimization=optimization,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,assembly_sha256=digest(asm)))
                save(where/'extraction.json',dict(actual_whole_module=True,production_source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                    compiled_source_sha256=hashlib.sha256(source.encode()).hexdigest(),test_only_reset=RESET,hardware_boundary_stubs=STUBS,
                    report_guard_bytes_each_side=32,production_instructions_unchanged_by_guards=True,no_real_pci_or_mmio=True))
        after={p.relative_to(ROOT).as_posix():digest(p) for p in paths};self.assertEqual(before,after)
        save(out/'validation-summary.json',dict(passed=True,skips=0,source_stable=True,source_sha256=after,actual_whole_module=True,
            actual_hardware_io=False,configuration_writes=0,results=results))
        print('USB_PREFLIGHT_EVIDENCE',out)

if __name__=='__main__':unittest.main(verbosity=2)

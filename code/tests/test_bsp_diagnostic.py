"""Actual assembly/link pipeline and fail-closed BSP diagnostic packaging tests.

The fixture is deliberately not a bootable OS: production services_run and
loader assembly are real; unexecuted kernel providers are explicit stubs and
the 17 service ELFs are one minimal PIE. Full OS/HID/FS evidence belongs to the
root's separate VM run. No VM or physical storage is opened by this module.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import unittest
import uuid

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'kernel/services_run.asm').is_file())
sys.path.insert(0,str(ROOT))
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags
from tools.build import find_tool
from tools.elf_image import materialize
from tools.gen_offsets import generate
from tools.mkimage import pack_image,manifest_text,unpack_image
from tools.service_bundle import pack,ELF
from tools.usb_only_profile import generate as usb_profile
from tools.build_usb import verify_build

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def extract(source,needle):
    start=source.index(needle);first=source.index('{',start);depth=1;at=first+1
    while depth:
        depth+=(source[at]=='{')-(source[at]=='}');at+=1
    return source[start:at]

def elf_symbols(path):
    data=Path(path).read_bytes();offset=struct.unpack_from('<Q',data,40)[0]
    stride,count=struct.unpack_from('<HH',data,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*stride) for i in range(count)]
    defined,undefined=set(),set()
    for entry in sections:
        if entry[1]!=2:continue
        names=sections[entry[6]];strings=data[names[4]:names[4]+names[5]]
        for at in range(entry[4],entry[4]+entry[5],entry[9]):
            name,info,_,section,_,_=struct.unpack_from('<IBBHQQ',data,at)
            if not name or info>>4==0:continue
            text=strings[name:strings.index(0,name)].decode('utf-8')
            (defined if section else undefined).add(text)
    return defined,undefined

def coff_symbols(path):
    data=Path(path).read_bytes();offset,count=struct.unpack_from('<II',data,8)
    strings=data[offset+count*18:];defined,undefined=set(),set();index=0
    while index<count:
        raw,value,section,typ,storage,aux=struct.unpack_from('<8sIhHBB',data,offset+index*18)
        if raw[:4]==bytes(4):
            n=struct.unpack_from('<I',raw,4)[0];name=strings[n:strings.index(0,n)].decode('utf-8')
        else:name=raw.rstrip(b'\0').decode('utf-8')
        if storage==2 and name:(defined if section else undefined).add(name)
        index+=1+aux
    return defined,undefined

class BspDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=ROOT/'tools/build_bsp_diagnostic.py'
        if not source.is_file():source=ROOT/'build/hardware/usb-s19-20261026-r1/pending/build_bsp_diagnostic.py'
        spec=importlib.util.spec_from_file_location('actual_bsp_diagnostic_under_test',source)
        cls.builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.builder)
        cls.out=ROOT/'build/test/bsp-diagnostic'/('run-'+uuid.uuid4().hex[:12]);cls.out.mkdir(parents=True)
        cls.normal=cls.out/'normal';cls.normal.mkdir();cls.log=cls.out/'normal-build.log'
        cls.commands=[];cls.records=[]
        cls.inputs={p for tree in ('include','boot','tools','lang/dongc') for p in (ROOT/tree).rglob('*') if p.is_file() and p.suffix in ('.inc','.asm','.py')}
        cls.inputs.update((Path(__file__),source,ROOT/'kernel/services_run.asm',ROOT/'kernel/linker.ld',ROOT/'kernel/boot/runtime_view.dg',ROOT/'kernel/smp/runtime.dg',ROOT/'kernel/user/services.dg',ROOT/'lang/examples/boot/abi.dg'))
        cls.before={str(p.relative_to(ROOT)):sha(p) for p in cls.inputs}
        cls.tools={n:str(Path(find_tool(n,e)).resolve()) for n,e in (('nasm','NASM'),('ld.lld','LD_LLD'),('lld-link','LLD_LINK'))}
        cls.nasm_warnings=nasm_flags(cls.tools['nasm'])[2:]
        cls.make_fixture()

    @classmethod
    def execute(cls,command,label):
        command=list(map(str,command));cls.commands.append(command)
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        record=dict(label=label,command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
        cls.records.append(record);save(cls.out/(label+'.json'),record)
        if result.returncode:raise AssertionError(label+': '+result.stderr[-2000:])

    @classmethod
    def assemble(cls,source,target,fmt='elf64',defines=()):
        target.parent.mkdir(parents=True,exist_ok=True)
        command=[cls.tools['nasm'],'-f',fmt,'-Wall','-Werror','-I',str(ROOT/'include')+os.sep,
            '-I',str(cls.normal)+os.sep,'-l',str(target.with_suffix('.lst')),'-o',str(target),*cls.nasm_warnings,*defines,str(source)]
        cls.execute(command,'fixture-assemble-'+target.relative_to(cls.normal).as_posix().replace('/','-'))

    @classmethod
    def make_fixture(cls):
        # Compile production declarations verbatim (only two same-named Report
        # identifiers are renamed), rather than inventing NASM offsets.
        decls=[]
        for file,needle,name in (
            ('lang/examples/boot/abi.dg','pub struct BootInfo','BootInfo'),
            ('kernel/boot/runtime_view.dg','pub struct Display','Display'),
            ('kernel/boot/runtime_view.dg','pub struct View','View'),
            ('kernel/user/services.dg','pub struct Report','ServiceReport'),
            ('kernel/smp/runtime.dg','pub struct Report','SmpReport')):
            text=(ROOT/file).read_text(encoding='utf-8');decl=extract(text,needle)
            decls.append(decl.replace(needle,'pub struct '+name,1))
        entry=cls.normal/'fixture_abi.dg';entry.write_text('module fixture_abi;\n'+'\n'.join(decls)+'\nexport("fixture_abi_sizes") fn sizes()u64{return (sizeof(BootInfo)+sizeof(View)+sizeof(ServiceReport)+sizeof(SmpReport)) as u64;}\n',encoding='utf-8')
        compiled=compile_file(entry,roots=[cls.normal],mode='release');layout=compiled.layout_manifest
        save(cls.normal/'dong_layout.json',layout)
        for typename,nasm_name,filename in (('BootInfo','BootInfo','bootinfo_layout.inc'),('View','RuntimeView','runtime_view.inc'),('ServiceReport','ServiceReport','service_report.inc'),('SmpReport','SmpReport','smp_report.inc')):
            (cls.normal/filename).write_text(generate(layout,'fixture_abi.'+typename,nasm_name),encoding='ascii')
        cls.assemble(ROOT/'kernel/services_run.asm',cls.normal/'services_run.o',defines=('-DRUNTIME_LEVEL=7','-DP6_USER_SMP=1'))
        _,externs=elf_symbols(cls.normal/'services_run.o')
        providers=cls.normal/'fixture-providers.asm'
        providers.write_text('bits 64\ndefault rel\nsection .text.entry\nglobal kernel_entry\nextern service_runtime_begin\nkernel_entry: call service_runtime_begin\nret\nsection .text\n'+''.join('global '+n+'\n'+n+': xor eax,eax\nret\n' for n in sorted(externs)),encoding='ascii')
        cls.assemble(providers,cls.normal/'entry.o')
        empty=cls.normal/'fixture-empty.asm';empty.write_text('bits 64\nsection .text\nnop\n',encoding='ascii')
        for name in cls.builder.KERNEL_OBJECTS:
            if name in ('entry.o','services_run.o'):continue
            cls.assemble(empty,cls.normal/name)
        cls.execute([cls.tools['ld.lld'],'-nostdlib','--gc-sections','-z','max-page-size=0x1000','-T',ROOT/'kernel/linker.ld','-o',cls.normal/'kernel.elf',*(cls.normal/n for n in cls.builder.KERNEL_OBJECTS)],'fixture-link-normal-kernel')
        raw=materialize((cls.normal/'kernel.elf').read_bytes());(cls.normal/'kernel.bin').write_bytes(raw)
        esp=cls.normal/'esp';(esp/'EFI/BOOT').mkdir(parents=True)
        image=pack_image(raw);(esp/'DONGOS.IMG').write_bytes(image)
        (cls.normal/'image_manifest.inc').write_text(manifest_text(image),encoding='utf-8')
        # Real minimal PIE service ELF, duplicated for the 17 fixture names.
        service=cls.normal/'fixture-service.asm';service.write_text('bits 64\nsection .text\nglobal _start\n_start: xor eax,eax\nret\n',encoding='ascii')
        cls.assemble(service,cls.normal/'fixture-service.o')
        program=cls.normal/'fixture-service.elf'
        cls.execute([cls.tools['ld.lld'],'-pie','--no-dynamic-linker','-z','norelro','--build-id=none','-T',ROOT/'services/lib/service.ld','-o',program,cls.normal/'fixture-service.o'],'fixture-link-service-pie')
        items=[]
        for name in sorted(cls.builder.SERVICE_NAMES):
            path=cls.normal/'services'/name/'program.elf';path.parent.mkdir(parents=True);shutil.copyfile(program,path)
            items.append((name,ELF,path.read_bytes()))
        (esp/'SERVICES.BIN').write_bytes(pack(items))
        for source,target,defines in (
            ('boot/image.asm','image.obj',()),
            ('boot/efi_main.asm','efi_main.obj',('-DSERVICE_BUNDLE=1','-DDESKTOP_MODE=1')),
            ('boot/service_bundle.asm','service_bundle.obj',()),
            ('boot/display_mode.asm','display_mode.obj',()),
            ('boot/trace_clock.asm','loader-trace/trace_clock.obj',()),
            ('boot/trace_loader_panic.asm','loader-trace/trace_loader_panic.obj',())):
            cls.assemble(ROOT/source,cls.normal/target,'win64',defines)
        defined=set();undefined=set()
        for name in cls.builder.LOADER_OBJECTS:
            if name=='loader-trace/trace_loader.obj':continue
            d,u=coff_symbols(cls.normal/name);defined|=d;undefined|=u
        trace=cls.normal/'fixture-trace-providers.asm'
        trace.write_text('bits 64\nsection .text\n'+''.join('global '+n+'\n'+n+': xor eax,eax\nret\n' for n in sorted(undefined-defined)),encoding='ascii')
        cls.assemble(trace,cls.normal/'loader-trace/trace_loader.obj','win64')
        cls.execute([cls.tools['lld-link'],'/subsystem:efi_application','/machine:x64','/entry:efi_main','/nodefaultlib','/timestamp:0','/fixed:no','/map:'+str(cls.normal/'efi_main.map'),'/out:'+str(esp/'EFI/BOOT/BOOTX64.EFI'),*(cls.normal/n for n in cls.builder.LOADER_OBJECTS)],'fixture-link-normal-efi')
        _,profile=usb_profile(cls.normal)
        required={'kernel/services_run.asm','boot/efi_main.asm','boot/image.asm','kernel/linker.ld'}
        required.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'include').glob('*.inc'))
        metadata=dict(runtime_level=7,kernel_mode='release',test=False,graphics_case=None,smp_case=None,compiler_job=False,source_unchanged=True,
            source_sha256={n:sha(ROOT/n) for n in sorted(required)},usb_only_profile=profile,
            artifacts={str(p.resolve()):sha(p) for p in (cls.normal/'kernel.elf',cls.normal/'kernel.bin',esp/'DONGOS.IMG',esp/'SERVICES.BIN',esp/'EFI/BOOT/BOOTX64.EFI')})
        save(cls.normal/'build-inputs.json',metadata)
        cls.log.write_text('\n'.join('+ '+subprocess.list2cmdline(c) for c in cls.commands)+'\n',encoding='utf-8')
        verify_build(esp)
        cls.fixture_sha=cls.builder._snapshot(cls.normal)
        save(cls.out/'fixture-identity.json',dict(synthetic_unexecuted_kernel_providers=True,synthetic_minimal_service_pies=True,
            full_os_or_hid_test=False,real_production_services_run_and_loader_assembly=True,real_elf_and_efi_link=True,
            abi_declarations_compiled_from_production=True,normal_inputs=cls.fixture_sha,production_inputs=cls.before,commands=cls.records))

    def test_actual_pipeline_selector_bindings_and_rejections(self):
        b=self.builder;output=self.out/'diagnostic'
        esp=b.build_diagnostic(self.normal,self.log,output);metadata=b.verify_diagnostic(esp)
        self.assertFalse(metadata['user_smp']);self.assertFalse(metadata['ordinary_normal_build']);self.assertTrue(metadata['diagnostic_only'])
        self.assertEqual(5,len(metadata['executed']));self.assertTrue(all(r['returncode']==0 for r in metadata['executed']))
        normal_undefined=elf_symbols(self.normal/'services_run.o')[1];diagnostic_undefined=elf_symbols(output/'services_run.o')[1]
        for name in ('user_smp_boot_begin','user_smp_normal_policy','dong_smp_report'):
            self.assertIn(name,normal_undefined);self.assertNotIn(name,diagnostic_undefined)
        self.assertIn('user_run',diagnostic_undefined)
        self.assertEqual(self.fixture_sha,b._snapshot(self.normal))
        image=(esp/'DONGOS.IMG').read_bytes();digest=hashlib.sha256(image).digest()
        self.assertEqual(unpack_image(image,digest),(output/'kernel.bin').read_bytes())
        for name in ('image.obj','esp/EFI/BOOT/BOOTX64.EFI'):self.assertIn(digest,(output/name).read_bytes())
        definitions=[line for line in manifest_text(image).splitlines() if line.startswith('%define ')]
        for name in ('image.lst','efi_main.lst'):
            listing=(output/name).read_text(encoding='utf-8')
            self.assertTrue(all(len(re.findall(r'(?m)^\s*\d+\s+<1> '+re.escape(line)+r'\s*$',listing))==1 for line in definitions))
        with self.assertRaises(FileNotFoundError):verify_build(esp)
        controls=[];manifest=output/'bsp-diagnostic.json';original_manifest=manifest.read_bytes()
        for name in ('services_run.o','esp/DONGOS.IMG','image_manifest.inc','esp/SERVICES.BIN','esp/EFI/BOOT/BOOTX64.EFI','dong_layout.json','services/xhci/program.elf'):
            path=output/name;original=path.read_bytes()
            try:
                changed=bytearray(original);changed[len(changed)//2]^=1;path.write_bytes(changed)
                with self.assertRaises(ValueError):b.verify_diagnostic(esp)
                controls.append(dict(name='artifact-'+name,rejected=True))
            finally:path.write_bytes(original)
        # These controls update the manifest's file hash deliberately: derived
        # selectors/banner/consumer/service invariants must reject independently.
        for name,replacement in (
            ('services_run.o',(self.normal/'services_run.o').read_bytes()),
            ('image.obj',(self.normal/'image.obj').read_bytes()),
            ('efi_main.lst',(self.normal/'efi_main.lst').read_bytes()),
            ('private/efi_main.asm',(ROOT/'boot/efi_main.asm').read_bytes()),
            ('services/xhci/program.elf',b'not-the-original-service'),
            ('esp/SERVICES.BIN',b'not-the-original-bundle')):
            path=output/name;original=path.read_bytes()
            try:
                path.write_bytes(replacement);bad=json.loads(original_manifest);bad['artifacts'][name]=sha(path);save(manifest,bad)
                with self.assertRaises(ValueError):b.verify_diagnostic(esp)
                controls.append(dict(name='rehashed-derived-'+name,rejected=True))
            finally:path.write_bytes(original);manifest.write_bytes(original_manifest)
        for key,value in (('user_smp',True),('ordinary_normal_build',True),('only_replaced_kernel_object','entry.o')):
            bad=json.loads(original_manifest);bad[key]=value;save(manifest,bad)
            try:
                with self.assertRaises(ValueError):b.verify_diagnostic(esp)
                controls.append(dict(name='profile-'+key,rejected=True))
            finally:manifest.write_bytes(original_manifest)
        # Existing/overlapping output must never damage a completed input.
        for path in (self.normal,self.normal/'child',output,self.out):
            with self.assertRaises(ValueError):b.build_diagnostic(self.normal,self.log,path)
            controls.append(dict(name='output-'+str(path.relative_to(self.out)),rejected=True))
        normal_metadata=self.normal/'build-inputs.json';normal_before=normal_metadata.read_bytes()
        bad=json.loads(normal_before);bad['test']=True;save(normal_metadata,bad)
        try:
            with self.assertRaises(ValueError):b.build_diagnostic(self.normal,self.log,self.out/'bad-test-profile')
            controls.append(dict(name='normal-test-profile',rejected=True))
        finally:normal_metadata.write_bytes(normal_before)
        # A selected command with a foreign executable is data, never execution.
        poisoned=self.out/'poisoned.log';marker=self.out/'must-not-exist'
        original_line=next(line for line in self.log.read_text(encoding='utf-8').splitlines() if 'services_run.o' in line and ' -o ' in line)
        command=b.argv_from_log(original_line[2:]);command[0]=str(Path(sys.executable).resolve())
        poisoned.write_text(self.log.read_text(encoding='utf-8').replace(original_line,'+ '+subprocess.list2cmdline(command)),encoding='utf-8')
        with self.assertRaises(ValueError):b.build_diagnostic(self.normal,poisoned,self.out/'bad-command')
        self.assertFalse(marker.exists());controls.append(dict(name='foreign-selected-command',rejected=True))
        # Even an extra malicious-looking command is never replayed. The plan
        # contains only five commands regenerated from trusted templates.
        extra=self.out/'extra-command.log';foreign=[sys.executable,'-c',f"from pathlib import Path;Path({str(marker)!r}).write_text('bad')"]
        extra.write_text(self.log.read_text(encoding='utf-8')+'+ '+subprocess.list2cmdline(foreign)+'\n',encoding='utf-8')
        plan=b.command_plan(self.normal,extra,self.out/'unused-extra-output')
        self.assertEqual(5,len(plan['commands']));self.assertFalse(any(c[0]==sys.executable for c in plan['commands'].values()));self.assertFalse(marker.exists())
        controls.append(dict(name='extra-log-command-not-replayed',rejected=True))
        self.assertEqual(self.fixture_sha,b._snapshot(self.normal));self.assertEqual(self.before,{n:sha(ROOT/n) for n in self.before})
        b.verify_diagnostic(esp)
        save(self.out/'validation-summary.json',dict(passed=True,skips=0,real_assembly_and_link=True,production_sources_unchanged=True,
            normal_inputs_unchanged=True,full_os_or_vm_executed=False,physical_devices_accessed=False,
            expected_selector_undefined_symbols_removed=['user_smp_boot_begin','user_smp_normal_policy','dong_smp_report'],
            actual_diagnostic_commands=metadata['executed'],controls=controls,fixture_identity_sha256=sha(self.out/'fixture-identity.json')))
        print('BSP_DIAGNOSTIC_EVIDENCE',self.out)

if __name__=='__main__':unittest.main()

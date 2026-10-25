"""Native Microsoft-ABI execution of the real EFI GOP collection/diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tools.gen_offsets import generate
from tools.mkimage import manifest_text, pack_image

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'boot/efi_main.asm'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def bridge(source,desktop,bad=False):
    first=source.index('\ncollect_graphics:')
    last=source.index('\ndraw_boot_logo:',first)
    body=source[first:last]
    if bad:
        needle='        jnz     .failed                  ; Explicit P1 limit, never truncates MMIO.'
        if body.count(needle)!=1:raise AssertionError('unique actual final low-4G guard')
        body=body.replace(needle,'        ; actual bad source omits the final low-4G rejection',1)
    definitions=[]
    labels=['graphics','graphics_status','graphics_reason']+re.findall(r'^(msg_gop_\w+):',source,re.M)
    for label in labels:
        matches=re.findall(r'^'+label+r':[^\n]*',source,re.M)
        if len(matches)!=1:raise AssertionError('unique production data label '+label)
        definitions+=matches
    guid=source[source.index('\ngraphics_guid:'):source.index('\nacpi2_guid:')]
    out=['bits 64','default rel','%include "uefi.inc"','%include "bootinfo.inc"']
    if desktop:out+=['%define DESKTOP_MODE 1']
    out+=['section .text','global probe_collect,probe_diag,probe_locate_entry',
          'global graphics_reason,graphics_status,probe_nv_bad,probe_callback_rsp_mod',
          'extern probe_locate,probe_desktop,probe_write,probe_hex',body]
    for name,target in [('probe_locate_entry','probe_locate'),('desktop_graphics_mode','probe_desktop'),
                        ('diagnostic_write','probe_write'),('diagnostic_hex','probe_hex')]:
        out+=[name+':','mov rax,rsp','and eax,15','mov [rel probe_callback_rsp_mod],rax']
        for offset in (8,16,24,32):out+=[f'mov qword [rsp+{offset}],0x5a5a5a5a']
        out+=['sub rsp,40','call '+target,'add rsp,40']
        for register in ('rcx','rdx','r8','r9','r10','r11'):out+=[f'mov {register},0x123456789abcdef0']
        for i in range(6):out+=[f'pxor xmm{i},xmm{i}']
        out+=['ret']
    registers=('rbx','rbp','rdi','rsi','r12','r13','r14','r15')
    for name,function in [('probe_collect','collect_graphics'),('probe_diag','graphics_diagnostic')]:
        out+=[name+':']+['push '+r for r in registers]
        out+=['sub rsp,248','mov [rsp+32],rcx','mov [rsp+40],rdx']
        for i in range(10):out+=[f'movdqu [rsp+{48+i*16}],xmm{i+6}',f'movdqu xmm{i+6},[rel probe_canary]']
        out += [f'mov {r},0x1122334455667788' for r in registers]
        if name=='probe_collect':out+=['mov r12,[rsp+32]','mov r13,[rsp+40]']
        else:out+=['mov rax,[rsp+32]','mov [rel graphics],rax']
        out+=['call '+function,'mov [rsp+208],rax','xor r10d,r10d']
        for r in registers:
            expected='[rsp+32]' if name=='probe_collect' and r=='r12' else '[rsp+40]' if name=='probe_collect' and r=='r13' else 'rax'
            if expected=='rax':out+=['mov rax,0x1122334455667788']
            out+=[f'cmp {r},{expected}','je $+6','or r10d,1']
        for i in range(10):
            out+=[f'movdqa xmm0,xmm{i+6}','pcmpeqb xmm0,[rel probe_canary]',
                  'pmovmskb eax,xmm0','cmp eax,65535','je $+6','or r10d,2']
        out+=['mov [rel probe_nv_bad],r10']
        for i in range(10):out+=[f'movdqu xmm{i+6},[rsp+{48+i*16}]']
        out+=['mov rax,[rsp+208]','add rsp,248']+['pop '+r for r in reversed(registers)]+['ret']
    out+=['section .data','align 8',*definitions,'align 8',guid,'align 8','probe_nv_bad:dq 0','probe_callback_rsp_mod:dq 0',
          'section .rodata','align 16','probe_canary:dq 0x123456789abcdef0,0xfedcba9876543210',
          '%ifidn __OUTPUT_FORMAT__,elf64','section .note.GNU-stack noalloc noexec nowrite','%endif']
    return '\n'.join(out)+'\n'


FIRMWARE_SYMBOLS=('loaded_image_guid','filesystem_guid','file_info_guid','graphics_guid','acpi2_guid','image_path')
FIRMWARE_GUIDS={
    'loaded_image_guid':'5b1b31a1-9562-11d2-8e3f-00a0c969723b',
    'filesystem_guid':'964e5b22-6459-11d2-8e39-00a0c969723b',
    'file_info_guid':'09576e92-6d3f-11d2-8e39-00a0c969723b',
    'graphics_guid':'9042a9de-23dc-4a38-96fb-7aded080516a',
    'acpi2_guid':'8868e871-e4f1-11d3-bc22-0080c73c8881'}


def coff_firmware_symbols(path):
    """Decode actual AMD64 COFF symbols/sections, including auxiliary records."""
    raw=Path(path).read_bytes()
    if len(raw)<20:raise ValueError('short COFF header')
    machine,count,_,table,symbols,optional,_=struct.unpack_from('<HHIIIHH',raw)
    if machine!=0x8664 or table+symbols*18+4>len(raw):raise ValueError('invalid AMD64 COFF symbol table')
    strings_at=table+symbols*18;strings_size=struct.unpack_from('<I',raw,strings_at)[0]
    if strings_size<4 or strings_at+strings_size>len(raw):raise ValueError('invalid COFF strings')
    sections={}
    for index in range(count):
        at=20+optional+index*40
        if at+40>len(raw):raise ValueError('short COFF section')
        name,_,_,size,data,_,_,_,_,flags=struct.unpack_from('<8sIIIIIIHHI',raw,at)
        exponent=(flags>>20)&15
        sections[index+1]=dict(name=name.rstrip(b'\0').decode('ascii'),size=size,data=data,
                               alignment=1<<(exponent-1) if 1<=exponent<=14 else 0)
    result={};index=0
    while index<symbols:
        at=table+index*18;name,value,section,_,_,aux=struct.unpack_from('<8sIhHBB',raw,at)
        if name[:4]==bytes(4):
            offset=struct.unpack_from('<I',name,4)[0]
            if offset<4 or offset>=strings_size:raise ValueError('bad COFF symbol name offset')
            end=raw.find(b'\0',strings_at+offset,strings_at+strings_size)
            if end<0:raise ValueError('unterminated COFF symbol name')
            decoded=raw[strings_at+offset:end].decode('ascii')
        else:decoded=name.rstrip(b'\0').decode('ascii')
        if decoded in FIRMWARE_SYMBOLS:
            if decoded in result or section not in sections:raise ValueError('duplicate/undefined firmware symbol')
            item=sections[section];length=24 if decoded=='image_path' else 16
            if value+length>item['size'] or item['data']+value+length>len(raw):raise ValueError('firmware symbol outside section')
            result[decoded]=dict(offset=value,section=item['name'],section_alignment=item['alignment'],
                                 bytes=raw[item['data']+value:item['data']+value+length].hex())
        index+=1+aux
    if index!=symbols or set(result)!=set(FIRMWARE_SYMBOLS):raise ValueError('incomplete firmware symbols')
    return result


def firmware_alignment_errors(symbols):
    errors=[]
    for name,item in symbols.items():
        alignment=2 if name=='image_path' else 8
        if item['offset']%alignment or item['section_alignment']<alignment:
            errors.append(name+' violates '+str(alignment)+'-byte firmware alignment')
    return errors


class LoaderGraphicsTests(unittest.TestCase):
    def test_actual_efi_coff_firmware_guid_and_char16_alignment(self):
        nasm=tool('nasm','NASM');self.assertTrue(nasm,'native NASM required; zero skips')
        paths=[ENTRY,ROOT/'include/uefi.inc',ROOT/'include/bootinfo.inc',ROOT/'include/boot_trace.inc',
               ROOT/'boot/loader_console.asm',ROOT/'boot/loader_handoff.asm',ROOT/'lang/examples/boot/abi.dg',
               ROOT/'tools/gen_offsets.py',ROOT/'tools/mkimage.py',Path(__file__)]
        fingerprint=lambda:{p.relative_to(ROOT).as_posix():sha(p) for p in paths}
        before=fingerprint();state=ROOT/'build/test/loader-graphics'/('coff-'+uuid.uuid4().hex[:12]);state.mkdir(parents=True)
        save(state/'source-before.json',before);results=[]
        try:
            layout=compile_file(ROOT/'lang/examples/boot/abi.dg',roots=[ROOT/'lang/examples']).layout_manifest
            save(state/'boot-layout.json',layout)
            (state/'bootinfo_layout.inc').write_text(generate(layout,'boot.abi.BootInfo'),encoding='ascii')
            # A real, minimal image manifest satisfies assembly only. No EFI
            # entry, firmware callback, VM or image payload is executed here.
            (state/'image_manifest.inc').write_text(manifest_text(pack_image(b'\x90\xc3')),encoding='ascii')
            source=ENTRY.read_text(encoding='utf-8')
            bad=source
            for alignment,label in ((8,'loaded_image_guid'),(2,'image_path')):
                pattern=r'\n[ \t]*align '+str(alignment)+r'[^\n]*\n(?='+label+r':)'
                self.assertEqual(len(re.findall(pattern,bad)),1,'unique actual alignment guard')
                bad=re.sub(pattern,'\n; actual bad source removes firmware alignment\n',bad,count=1)
            for bundle in (0,1):
                for desktop in (0,1):
                    for mutated,body in ((False,source),(True,bad)):
                        label=f'efi-service{bundle}-desktop{desktop}-'+('omit-alignment' if mutated else 'normal')
                        asm=state/(label+'.asm');asm.write_bytes(body.encode());obj=state/(label+'.obj')
                        command=[nasm,*nasm_flags(nasm),'-f','win64','-DSERVICE_BUNDLE='+str(bundle),
                                 *(['-DDESKTOP_MODE=1'] if desktop else []),'-I',str(state)+os.sep,
                                 '-I',str(ROOT/'include')+os.sep,'-I',str(ROOT)+os.sep,'-o',str(obj),str(asm)]
                        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
                        save(state/(label+'-assemble.json'),dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
                        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                        symbols=coff_firmware_symbols(obj);errors=firmware_alignment_errors(symbols)
                        save(state/(label+'-symbols.json'),dict(symbols=symbols,alignment_errors=errors))
                        self.assertEqual(symbols['image_path']['bytes'],('\\DONGOS.IMG'.encode('utf-16le')+b'\0\0').hex())
                        for name,guid in FIRMWARE_GUIDS.items():
                            self.assertEqual(symbols[name]['bytes'],uuid.UUID(guid).bytes_le.hex())
                        if mutated:
                            self.assertTrue(errors,'real bad source assembled but must fail symbol oracle')
                            self.assertTrue(any(e.startswith('image_path ') for e in errors))
                            self.assertTrue(any(e.startswith('graphics_guid ') for e in errors))
                        else:self.assertEqual(errors,[])
                        results.append(dict(service_bundle=bundle,desktop_mode=desktop,mutated=mutated,
                                            object_sha256=sha(obj),symbols=symbols,alignment_errors=errors))
            self.assertEqual(before,fingerprint(),'EFI sources changed during COFF inspection')
        finally:
            save(state/'source-after.json',fingerprint());save(state/'result.json',dict(source_stable=before==fingerprint(),
                results=results,actual_whole_efi_coff_assembled=True,efi_executed=False,vm_executed=False,physical_devices_accessed=False))
        print('LOADER_GRAPHICS_COFF_EVIDENCE '+str(state))

    def test_real_gop_collector_diagnostics_bounds_abi_and_bad_guard(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native NASM/GCC required; zero skips')
        paths=[ENTRY,ROOT/'include/uefi.inc',ROOT/'include/bootinfo.inc',ROOT/'lang/examples/boot/abi.dg',
               ROOT/'tools/gen_offsets.py',ROOT/'lang/tests/test_dongc.py',Path(__file__),ROOT/'tests/loader_graphics_probe.c']
        fingerprint=lambda:{p.relative_to(ROOT).as_posix():sha(p) for p in paths}
        before=fingerprint();state=ROOT/'build/test/loader-graphics'/('run-'+uuid.uuid4().hex[:12]);state.mkdir(parents=True)
        save(state/'source-before.json',before);commands=[]
        tools_before={name:dict(path=str(Path(path).resolve()),sha256=sha(path))
                      for name,path in [('python',sys.executable),('nasm',nasm),('cc',cc)]}
        save(state/'tools.json',tools_before)
        def run(argv,label,expected=0):
            argv=list(map(str,argv));r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=60)
            receipt=dict(argv=argv,cwd=str(ROOT),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
            save(state/(label+'.json'),receipt);commands.append(receipt)
            self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
        try:
            layout=compile_file(ROOT/'lang/examples/boot/abi.dg',roots=[ROOT/'lang/examples']).layout_manifest
            save(state/'boot-layout.json',layout)
            (state/'bootinfo_layout.inc').write_text(generate(layout,'boot.abi.BootInfo'),encoding='ascii')
            source=ENTRY.read_text(encoding='utf-8');host='win64' if os.name=='nt' else 'elf64'
            for desktop in (0,1):
                for bad in (False,True):
                    name=f'desktop{desktop}-'+('omit-low4g' if bad else 'normal')
                    asm=state/(name+'.asm');asm.write_text(bridge(source,desktop,bad),encoding='ascii');objects={}
                    for fmt in ('elf64','win64'):
                        obj=state/(name+'-'+fmt+'.o')
                        run([nasm,*nasm_flags(nasm),'-f',fmt,'-I',str(state)+os.sep,'-I',str(ROOT/'include')+os.sep,'-o',obj,asm],name+'-'+fmt)
                        objects[fmt]=obj
                    for optimization in ('0','2'):
                        exe=state/(name+'-O'+optimization+('.exe' if os.name=='nt' else ''))
                        run([cc,'-std=c11','-Wall','-Wextra','-Werror','-O'+optimization,'-maccumulate-outgoing-args',
                             '-D__USE_MINGW_ANSI_STDIO=1','-DEXPECT_DESKTOP='+str(desktop),
                             *([] if os.name=='nt' else ['-no-pie']),ROOT/'tests/loader_graphics_probe.c',objects[host],'-o',exe],name+'-link-'+optimization)
                        result=run([exe],name+'-native-'+optimization,1 if bad else 0)
                        self.assertIn('returned normally',result.stdout+result.stderr)
                        self.assertIn('loader graphics oracle' if bad else 'loader graphics oracle passed',result.stdout+result.stderr)
            self.assertEqual(before,fingerprint(),'sources changed during native execution')
        finally:
            save(state/'source-after.json',fingerprint());save(state/'commands.json',commands)
            save(state/'result.json',dict(source_stable=before==fingerprint(),source_body='actual collect_graphics through graphics_diagnostic',
                desktop_modes=[0,1],native_optimizations=['O0','O2'],assembled_formats=['elf64','win64'],
                mutation='omit actual final low-4G rejection',vm_executed=False,physical_devices_accessed=False))
        print('LOADER_GRAPHICS_EVIDENCE '+str(state))


if __name__=='__main__':unittest.main(verbosity=2)

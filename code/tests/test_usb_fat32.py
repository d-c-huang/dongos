"""Native real FAT32 audit on a sparse 8-GB-scale independent sector model."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tools.usb_only_profile import generate, verify

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


class UsbFat32Tests(unittest.TestCase):
    def test_actual_large_volume_audit_defaults_bounds_and_bad_bitmap(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native NASM/GCC required; zero skips')
        inputs=[ROOT/p for p in ('services/fs/fat32.dg','services/fs/errors.dg','services/fs/path.dg',
                'services/fs/lfn.dg','services/lib/hardware_profile.dg','tests/fat32_probe.dg',
                'tests/test_usb_fat32.py','tests/usb_fat32_probe.c','tools/usb_only_profile.py')]
        snapshot=lambda:{p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
        before=snapshot()
        out=ROOT/'build/test/usb-fat32'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        save(out/'source-before.json',before)
        results=[]
        def run(command,d,label,expected=0):
            command=list(map(str,command))
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
            save(d/(label+'.json'),dict(command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
            self.assertEqual(expected,result.returncode,result.stdout+result.stderr)
            return result
        try:
            for variant in ('default','usb','wrong-mark-index'):
                for mode in ('debug','release'):
                    d=out/(variant+'-'+mode);source_root=d/'input';services=source_root/'services'
                    for path in inputs:
                        if path.is_relative_to(ROOT/'services'):
                            destination=services/path.relative_to(ROOT/'services')
                            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
                    if variant!='default':
                        services,metadata=generate(d/'generated',source_root=source_root)
                        verify(d/'generated',metadata,source_root=source_root);save(d/'profile.json',metadata)
                    if variant=='wrong-mark-index':
                        path=services/'fs/fat32.dg';text=path.read_text(encoding='utf-8')
                        needle='let at=(cluster/8) as usize;'
                        self.assertEqual(text.count(needle),1)
                        path.write_text(text.replace(needle,'let at=(cluster/16) as usize;',1),encoding='utf-8')
                        save(d/'mutation.json',dict(actual_source='fs/fat32.dg',change='mark high clusters in wrong bitmap byte',expected='native ordinary clean volume is rejected'))
                    compiled=compile_file(ROOT/'tests/fat32_probe.dg',roots=[ROOT/'tests',services],mode=mode)
                    types={t['full_name']:t for t in compiled.layout_manifest['types']}
                    self.assertEqual(types['fs.fat32.Volume']['size'],120)
                    self.assertEqual(types['fs.fat32.Device']['size'],48)
                    scratch=types['fs.fat32.Scratch']
                    seen=next(f for f in scratch['fields'] if f['name']=='seen')
                    self.assertEqual(scratch['size'],39656 if variant=='default' else 2104040)
                    self.assertEqual(seen['offset'],1067)
                    frames=[int(n) for n in re.findall(r'sub rsp, ([0-9]+)',compiled.assembly)]
                    self.assertLess(max(frames),8192,'Scratch must be borrowed, never a 2-MiB stack copy')
                    save(d/'layout.json',dict(scratch=scratch,volume=types['fs.fat32.Volume'],device=types['fs.fat32.Device'],max_frame=max(frames)))
                    asm=d/'probe.asm';asm.write_text(compiled.assembly,encoding='utf-8')
                    objects={}
                    for fmt in ('elf64','win64'):
                        obj=d/(fmt+'.o');run([nasm,'-f',fmt,*nasm_flags(nasm),'-o',obj,asm],d,'assemble-'+fmt);objects[fmt]=obj
                    exe=d/('probe.exe' if os.name=='nt' else 'probe')
                    run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',
                         '-DFAT32_SCRATCH_BYTES='+str(scratch['size']),'-DFAT32_SEEN_OFFSET='+str(seen['offset']),
                         *([] if os.name=='nt' else ['-no-pie']),ROOT/'tests/usb_fat32_probe.c',
                         objects['win64' if os.name=='nt' else 'elf64'],'-o',exe],d,'link')
                    result=run([exe,'default' if variant=='default' else 'usb'],d,'native',1 if variant=='wrong-mark-index' else 0)
                    self.assertIn('USB_FAT_ASSERT' if variant=='wrong-mark-index' else 'USB_FAT_NATIVE passed',result.stdout+result.stderr)
                    self.assertIn('returned normally',result.stdout+result.stderr)
                    if variant!='wrong-mark-index':
                        # A normal 512-byte local file exercises the optional read-only
                        # stream backend. The cap must reject before any absent sector.
                        count=(32768 if variant=='default' else 2097152)*8-1
                        fat_sectors=(count+2+127)//128
                        vbr=bytearray(512)
                        def put(at,value,width):vbr[at:at+width]=value.to_bytes(width,'little')
                        put(11,512,2);vbr[13]=8;put(14,32,2);vbr[16]=2;vbr[21]=0xf8
                        put(32,32+2*fat_sectors+count*8,4);put(36,fat_sectors,4)
                        put(44,65536,4);put(48,1,2);put(50,6,2);put(510,0xaa55,2)
                        image=d/'local-readonly-cap.vbr';image.write_bytes(vbr);image_hash=sha(image)
                        readonly=run([exe,'--readonly-volume',image,scratch['size']],d,'native-readonly-local-file')
                        self.assertIn('mount_error=0x0000000005040003',readonly.stdout)
                        self.assertIn('reads=2 writes=0 flushes=0 bad_io=0',readonly.stdout)
                        self.assertIn('canaries=1 stream_mode=rb',readonly.stdout)
                        self.assertEqual(sha(image),image_hash,'read-only stream changed its local input')
                    results.append(dict(variant=variant,mode=mode,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
            self.assertEqual(before,snapshot(),'production source changed during native test')
        finally:
            save(out/'source-after.json',snapshot())
            save(out/'result.json',dict(source_stable=before==snapshot(),results=results,actual_sparse_callbacks=True,
                                       large_cluster_count=2000000,root_cluster=1500000,vm_executed=False,physical_disk_accessed=False))
        print('USB_FAT32_EVIDENCE '+str(out))


if __name__=='__main__':unittest.main(verbosity=2)

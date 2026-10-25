"""Execute real mount_cache on independent high-cluster sparse callbacks."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tools.usb_only_profile import generate, verify

ROOT=Path(__file__).resolve().parents[1]
EXPORTS='''
export("mc_begin") unsafe fn probe_begin(s:*State,d:*const fat.Device,out:*fat.Device)u64{unsafe{match begin(s,d,out){ok=>{return 0;},err(e)=>{return e;},}}}
export("mc_finish") unsafe fn probe_finish(s:*State)void{unsafe{finish(s);}return;}
export("mc_profile") fn probe_profile()u64{if hardware_profile.USB_ONLY{return 1;}return 0;}
export("mc_audit_bytes") fn probe_audit_bytes()u64{return hardware_profile.FAT_AUDIT_BYTES as u64;}
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


class UsbMountCacheTests(unittest.TestCase):
    def test_actual_large_geometry_hits_errors_finish_and_old_limit_mutant(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native NASM/GCC required; zero skips')
        inputs=[ROOT/p for p in ('services/fs/mount_cache.dg','services/fs/fat32.dg','services/fs/errors.dg',
            'services/fs/path.dg','services/fs/lfn.dg','services/lib/hardware_profile.dg',
            'tests/test_usb_mount_cache.py','tests/usb_mount_cache_probe.c','tools/usb_only_profile.py')]
        snapshot=lambda:{p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
        before=snapshot();out=ROOT/'build/test/usb-mount-cache'/('run-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
        save(out/'source-before.json',before);results=[]
        def run(command,d,label,expected=0):
            command=list(map(str,command));r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
            save(d/(label+'.json'),dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            self.assertEqual(expected,r.returncode,r.stdout+r.stderr);return r
        try:
            for variant in ('default','usb','usb-old-limit'):
                for mode in ('debug','release'):
                    d=out/(variant+'-'+mode);source_root=d/'input';services=source_root/'services'
                    for path in inputs:
                        if path.is_relative_to(ROOT/'services'):
                            target=services/path.relative_to(ROOT/'services');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
                    if variant!='default':
                        services,metadata=generate(d/'generated',source_root=source_root)
                        verify(d/'generated',metadata,source_root=source_root);save(d/'profile.json',metadata)
                    target=services/'fs/mount_cache.dg';body=target.read_bytes();text=body.decode()
                    if variant=='usb-old-limit':
                        needle='clusters+2>(hardware_profile.FAT_AUDIT_BYTES as u64)*8'
                        self.assertEqual(text.count(needle),1)
                        text=text.replace(needle,'clusters+2>262144',1)
                    target.write_bytes((text+EXPORTS).encode())
                    if variant!='usb-old-limit':self.assertEqual(target.read_bytes()[:len(body)],body)
                    save(d/'staging.json',dict(source_sha256=hashlib.sha256(body).hexdigest(),exports_only=variant!='usb-old-limit',
                        mutation='restore old hard-coded bitmap eligibility' if variant=='usb-old-limit' else None))
                    compiled=compile_file(target,roots=[services],mode=mode)
                    types={t['full_name']:t for t in compiled.layout_manifest['types']}
                    self.assertEqual(types['fs.mount_cache.State']['size'],32888)
                    self.assertEqual(types['fs.mount_cache.Line']['size'],16408)
                    self.assertEqual(types['fs.fat32.Device']['size'],48)
                    frames=[int(n) for n in re.findall(r'sub rsp, ([0-9]+)',compiled.assembly)]
                    self.assertLess(max(frames),8192)
                    save(d/'layout.json',dict(state=types['fs.mount_cache.State'],line=types['fs.mount_cache.Line'],max_frame=max(frames)))
                    asm=d/'probe.asm';asm.write_text(compiled.assembly,encoding='utf-8');objects={}
                    for fmt in ('elf64','win64'):
                        obj=d/(fmt+'.o');run([nasm,'-f',fmt,*nasm_flags(nasm),'-o',obj,asm],d,'assemble-'+fmt);objects[fmt]=obj
                    exe=d/('probe.exe' if os.name=='nt' else 'probe')
                    run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',
                        '-DMOUNT_CACHE_BYTES='+str(types['fs.mount_cache.State']['size']),
                        *([] if os.name=='nt' else ['-no-pie']),ROOT/'tests/usb_mount_cache_probe.c',
                        objects['win64' if os.name=='nt' else 'elf64'],'-o',exe],d,'link')
                    r=run([exe,'default' if variant=='default' else 'usb'],d,'native',1 if variant=='usb-old-limit' else 0)
                    self.assertIn('USB_CACHE_ASSERT' if variant=='usb-old-limit' else 'USB_CACHE_NATIVE passed',r.stdout+r.stderr)
                    self.assertIn('returned normally',r.stdout+r.stderr)
                    self.assertNotIn('unexpected panic',r.stderr)
                    results.append(dict(variant=variant,mode=mode,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            self.assertEqual(before,snapshot(),'production sources changed during native run')
        finally:
            save(out/'source-after.json',snapshot());save(out/'result.json',dict(source_stable=before==snapshot(),results=results,
                actual_cache_body=True,high_cluster_count=1899872,actual_physical_disk=False,vm_executed=False))
        print('USB_MOUNT_CACHE_EVIDENCE '+str(out))


if __name__=='__main__':unittest.main(verbosity=2)

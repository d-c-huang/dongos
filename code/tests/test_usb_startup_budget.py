"""Actual complete production catalog initialization, two trusted profiles."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool

ROOT=Path(__file__).resolve().parents[1]


class UsbStartupBudgetTests(unittest.TestCase):
    def test_full_catalog_profiles_bounds_abi_and_original_budget_bad_source(self):
        names=('kernel/user/processes.dg','services/lib/process_abi.dg',
               'services/lib/hardware_profile.dg','tests/process_catalog_probe.dg',
               'tests/usb_startup_budget_probe.c','tests/test_usb_startup_budget.py',
               'lang/tests/test_dongc.py')
        frozen=lambda:{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
        before=frozen()
        state=ROOT/'build/test/usb-startup-budget'/('run-'+uuid.uuid4().hex[:12])
        state.mkdir(parents=True)
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC')
        self.assertTrue(nasm and cc,'native tools required; zero skips')
        tools={role:dict(path=str(Path(path).resolve()),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
               for role,path in [('python',sys.executable),('nasm',nasm),('cc',cc)]}
        records=[]
        def run(argv,d,label,expected=0):
            argv=list(map(str,argv))
            result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=60)
            (d/(label+'.json')).write_text(json.dumps(dict(argv=argv,returncode=result.returncode,
                 stdout=result.stdout,stderr=result.stderr),indent=2)+'\n',encoding='utf-8')
            self.assertEqual(expected,result.returncode,result.stdout+result.stderr)
            return result
        try:
            for variant,profile in [('default',False),('usb-only',True),('usb-wrong-ten-seconds',True)]:
                for mode in ('debug','release'):
                    directory=state/(variant+'-'+mode)
                    source=directory/'source'
                    for original in names[:3]:
                        target=source/original
                        target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes((ROOT/original).read_bytes())
                    policy=source/'services/lib/hardware_profile.dg'
                    text=policy.read_text(encoding='utf-8')
                    self.assertEqual(text.count('pub const USB_ONLY:bool=false;'),1)
                    if profile:
                        policy.write_text(text.replace('pub const USB_ONLY:bool=false;',
                            'pub const USB_ONLY:bool=true;',1),encoding='utf-8')
                    if variant=='usb-wrong-ten-seconds':
                        path=source/'kernel/user/processes.dg'
                        text=path.read_text(encoding='utf-8')
                        needle='if hardware_profile.USB_ONLY {(*c).configs[1].timeout_ticks=hz*60;}'
                        self.assertEqual(text.count(needle),1)
                        path.write_text(text.replace(needle,needle.replace('hz*60','hz*10'),1),encoding='utf-8')
                    compiled=compile_file(ROOT/names[3],roots=[ROOT/'tests',source/'kernel',source/'services'],mode=mode)
                    types={item['full_name']:item for item in compiled.layout_manifest['types']}
                    for name,size in [('lib.process_abi.Config',128),('lib.process_abi.Snapshot',64),
                                      ('lib.process_abi.Event',64),('user.processes.Catalog',10776)]:
                        self.assertEqual(types[name]['size'],size)
                    asm=directory/'probe.asm';asm.write_text(compiled.assembly,encoding='utf-8')
                    for fmt in ('elf64','win64'):
                        run([nasm,'-f',fmt,*nasm_flags(nasm),'-o',directory/(fmt+'.o'),asm],directory,'assemble-'+fmt)
                    executable=directory/('probe.exe' if os.name=='nt' else 'probe')
                    run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-D__USE_MINGW_ANSI_STDIO=1',
                         '-DUSB_PROFILE='+str(int(profile)),*([] if os.name=='nt' else ['-no-pie']),
                         ROOT/names[4],directory/('win64.o' if os.name=='nt' else 'elf64.o'),'-o',executable],directory,'link')
                    result=run([executable],directory,'native',1 if variant=='usb-wrong-ten-seconds' else 0)
                    self.assertIn('startup budget oracle failed' if variant=='usb-wrong-ten-seconds'
                                  else 'USB_STARTUP_BUDGET_PASS',result.stdout+result.stderr)
                    self.assertIn('returned normally',result.stdout+result.stderr)
                    records.append(dict(variant=variant,profile=profile,mode=mode,
                                        returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
            self.assertEqual(before,frozen(),'source changed during native execution')
        finally:
            (state/'validation-summary.json').write_text(json.dumps(dict(
                passed=len(records)==6 and all(r['returncode']==(1 if r['variant']=='usb-wrong-ten-seconds' else 0) for r in records),
                source_unchanged=before==frozen(),source_sha256=before,tools=tools,
                actual_catalog_initialize=True,hardware_io=False,records=records),indent=2)+'\n',encoding='utf-8')
        print('USB_STARTUP_BUDGET_EVIDENCE',state)


if __name__=='__main__':
    unittest.main(verbosity=2)

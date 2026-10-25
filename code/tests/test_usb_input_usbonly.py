"""Execute current input main for default PS2 and explicit USB-only profiles."""
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path

from lang.dongc import compile_file
from lang.dongc.modules import Resolver
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_input import command
from tests.test_fat32 import stack_bound
from tests.test_usb_input_entry import SUFFIX

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / 'services'
SOURCE = SOURCE_ROOT / 'drivers/input_service.dg'
FLAGS_SUFFIX = '''
export("input_profile_flags") fn probe_profile_flags()u64{unsafe{
 return (PS2_ACTIVE as u64)|((TABLET as u64)<<1)|((INTERRUPTS as u64)<<2);
}}
'''


class UsbOnlyInputTests(unittest.TestCase):
    def test_actual_main_retains_ps2_and_requires_trusted_ready(self):
        # Freeze only the compiler's actual input closure; parallel FS changes
        # are not inputs to the input service or this independent native oracle.
        module = Resolver([SOURCE_ROOT]).load(SOURCE)
        sources = [Path(name) for name in module.source_files]
        paths = sorted(set(sources + [
            ROOT / 'tests/input_service_probe.c',
            ROOT / 'tests/usb_input_usbonly_probe.c',
            ROOT / 'tests/test_usb_input_entry.py',
            ROOT / 'tests/test_input.py',
            ROOT / 'tests/test_fat32.py',
            Path(__file__),
        ]))
        frozen = lambda: {p.relative_to(ROOT).as_posix():
                          hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        before = frozen()
        out = ROOT / 'build/test/usb-input-usbonly' / ('run-' + uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        evidence = []
        # Preserve all pre-existing default-profile bad sources. Both normal
        # profiles execute every authentication failure scenario; USB_ONLY
        # additionally executes bad sources that wrongly touch old hardware.
        variants = {
            'zero-readiness-accepted': ('if value!=0{', 'if value==0{return true;}if value!=0{', 'usb1', (0,)),
            'error-as-ready': ('if value>>32!=0x5548_5244||incarnation==0||incarnation>0x0fff_ffff{return error.Transport;}', '', 'usb3', (0,)),
            'untagged-ready': ('value>>32!=0x5548_5244||', 'false||', 'usb6', (0,)),
            'zero-incarnation-ready': ('||incarnation==0', '', 'usb9', (0,)),
            'oversized-incarnation-ready': ('||incarnation>0x0fff_ffff', '', 'usb2', (0,)),
            'late-i8042-drain': ('if PS2_ACTIVE{let initial_drained=', 'if true{let initial_drained=', 'usb0', (0,)),
            'binds-ps2-irq': ('if PS2_ACTIVE{try prepare_irq(boot);}', 'try prepare_irq(boot);', 'usb0', (0,)),
            'waits-past-bound': ('attempt<1024', 'attempt<1025', 'usb1', (0,)),
            'departure-error-as-epoch': ('if value>>32!=0x5548_4450||through==0||through>0x0fff_ffff{return error.Transport;}', '', 'usb11', (0,)),
            'departure-untagged': ('value>>32!=0x5548_4450||', 'false||', 'usb12', (0,)),
            'departure-zero-incarnation': ('||through==0', '', 'usb14', (0,)),
            'departure-oversized-incarnation': ('||through>0x0fff_ffff', '', 'usb15', (0,)),
            'profile-starts-ps2': ('PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;', 'let forbidden=start((*boot).console);PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;', 'usb0', (1,)),
            'profile-probes-tablet': ('PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;', 'PS2_ACTIVE=false;TABLET=try tablet.setup();INTERRUPTS=false;', 'usb0', (1,)),
            'profile-binds-irq': ('PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;', 'PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;try prepare_irq(boot);', 'usb0', (1,)),
            'profile-skips-readiness': ('if !(try usb_ready(boot)){return error.Transport;}', '', 'usb0', (1,)),
            'profile-keeps-ps2-active': ('PS2_ACTIVE=false;TABLET=false;INTERRUPTS=false;', 'PS2_ACTIVE=true;TABLET=false;INTERRUPTS=false;', 'usb0', (1,)),
        }
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'native NASM and C compiler required; zero skips')
        try:
            for variant in ('normal', *variants):
                profiles = (0, 1) if variant == 'normal' else variants[variant][3]
                for profile in profiles:
                    for mode in ('debug', 'release'):
                        directory = out / (variant + '-profile' + str(profile) + '-' + mode)
                        stage = directory / 'source'
                        for original in sources:
                            target = stage / original.relative_to(SOURCE_ROOT)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(original.read_bytes())
                        source_path = stage / 'drivers/input_service.dg'
                        source = source_path.read_text(encoding='utf-8')
                        if variant != 'normal':
                            old, new, _, _ = variants[variant]
                            self.assertGreaterEqual(source.count(old), 1, variant)
                            source = source.replace(old, new, 1)
                        source_path.write_text(source + SUFFIX + FLAGS_SUFFIX, encoding='utf-8')
                        policy = stage / 'lib/hardware_profile.dg'
                        policy_source = policy.read_text(encoding='utf-8')
                        self.assertEqual(policy_source.count('pub const USB_ONLY:bool=false;'), 1)
                        if profile:
                            policy.write_text(policy_source.replace('pub const USB_ONLY:bool=false;',
                                                                    'pub const USB_ONLY:bool=true;', 1),
                                              encoding='utf-8')
                        compiled = compile_file(source_path, roots=[stage], mode=mode)
                        bound = stack_bound(compiled.assembly)
                        self.assertLessEqual(bound, 12288)
                        asm = directory / 'probe.asm'
                        asm.write_text(compiled.assembly, encoding='utf-8')
                        for fmt in ('elf64', 'win64'):
                            command([nasm, '-f', fmt, *nasm_flags(nasm), '-o',
                                     directory / (fmt + '.o'), asm], directory, 'assemble-' + fmt)
                        executable = directory / ('probe.exe' if os.name == 'nt' else 'probe')
                        command([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                                 '-D__USE_MINGW_ANSI_STDIO=1',
                                 '-DUSB_HARDWARE_PROFILE=' + str(profile),
                                 *(['-mno-sse'] if os.name == 'nt' else ['-no-pie', '-D_DEFAULT_SOURCE']),
                                 ROOT / 'tests/usb_input_usbonly_probe.c',
                                 directory / ('win64.o' if os.name == 'nt' else 'elf64.o'),
                                 '-o', executable], directory, 'link')
                        if variant == 'normal':
                            scenarios = (() if profile else tuple(str(n) for n in range(8)))
                            scenarios += tuple('usb' + str(n) for n in range(18))
                        else:
                            scenarios = (variants[variant][2],)
                        for scenario in scenarios:
                            run = command([executable, scenario], directory, 'native-' + scenario,
                                          success=False)
                            self.assertEqual(0 if variant == 'normal' else 1, run.returncode,
                                             run.stdout + run.stderr)
                            marker = ('passed;' if variant == 'normal' and not scenario.startswith('usb')
                                      else 'USB_ONLY_INPUT_NATIVE_PASS' if variant == 'normal'
                                      else 'input service check failed')
                            self.assertIn(marker, run.stdout + run.stderr)
                            evidence.append(dict(variant=variant, profile=profile, mode=mode,
                                                 scenario=scenario, stack=bound,
                                                 stdout=run.stdout, stderr=run.stderr))
            self.assertEqual(before, frozen())
            (out / 'validation-summary.json').write_text(json.dumps(
                dict(passed=True, source_unchanged=True, source_sha256=before,
                     actual_input_main=True, profiles=['default', 'usb-only'],
                     hardware_io=False, evidence=evidence), indent=2) + '\n', encoding='utf-8')
        finally:
            (out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
            (out / 'source-after.json').write_text(json.dumps(frozen(), indent=2) + '\n', encoding='utf-8')
            (out / 'evidence-so-far.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
        print('USB_ONLY_INPUT_EVIDENCE', out)


if __name__ == '__main__':
    unittest.main(verbosity=2)

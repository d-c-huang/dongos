"""Shared USB policy: real role ledger plus extracted early hardware guards.

No physical disks, OS or VM are accessed. The privilege-dependent remainder
of devices.grant/admit is replaced only after the actual first policy guard
with a counted hardware callback; full grant paths are verified by the VM gate.
"""
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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = (b'// Default desktop/storage policy. Explicit USB builds override this module.\n'
                   b'module lib.hardware_profile;\n'
                   b'pub const USB_ONLY:bool=false;\n'
                   b'pub const FAT_AUDIT_BYTES:usize=32768;\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def first_guard(source, function):
    start = source.index('pub unsafe fn ' + function + '(')
    unsafe = re.search(r'\bunsafe\s*\{', source[start:])
    if unsafe is None:
        raise AssertionError('missing production unsafe body')
    body = source[start + unsafe.end():]
    line = next(line.strip() for line in body.splitlines() if line.strip())
    # Mutant source may omit this exact first statement; that genuinely removes
    # its instructions from the compiled fragment and the native oracle fails.
    return line if line.startswith('if hardware_profile.USB_ONLY') else ''


def guard_module(source):
    claim = first_guard(source, 'grant')
    admit = first_guard(source, 'admit')
    return '''module usb_only_claim_guard;
import lib.hardware_profile as hardware_profile;
pub error Denied=0x050a_0002;
pub unsafe extern "sysv64" ("usb_policy_hardware") fn hardware(kind:u64,id:u64,ecam:u64)u64;
pub unsafe fn claim(id:usize,ecam:u64)!void {unsafe {
''' + claim + '''
if hardware(0,id as u64,ecam)!=0{return error.Denied;}
}return;}
pub unsafe fn admit(role:u64,ecam:u64)!void {unsafe {
''' + admit + '''
if hardware(1,role,ecam)!=0{return error.Denied;}
}return;}
'''


class UsbOnlyProfileTests(unittest.TestCase):
    def test_default_definition_and_guards_precede_every_privileged_action(self):
        self.assertEqual((ROOT/'services/lib/hardware_profile.dg').read_bytes(), DEFAULT_PROFILE)
        source = (ROOT/'kernel/user/devices.dg').read_text(encoding='utf-8')
        self.assertEqual(first_guard(source, 'admit'), 'if hardware_profile.USB_ONLY&&role==1{return error.Denied;}')
        self.assertEqual(first_guard(source, 'grant'), 'if hardware_profile.USB_ONLY&&id==2{return error.Denied;}')
        # Guard-first means no ECAM write, BAR sizing, owner or attempted-state
        # publication may precede rejection, including the xHCI dispatch.
        grant = source.split('pub unsafe fn grant(', 1)[1].split('pub fn granted_bars', 1)[0]
        self.assertLess(grant.index('if hardware_profile.USB_ONLY'), grant.index('if id==ADMITTED_XHCI'))
        self.assertLess(grant.index('if hardware_profile.USB_ONLY'), grant.index('try read32'))

    def test_real_native_default_usb_ledger_and_actual_bad_guards(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'native NASM and GCC required; zero skips')
        paths = [ROOT/n for n in ('services/lib/hardware_profile.dg', 'services/lib/device_abi.dg',
                 'services/drivers/device_policy.dg', 'kernel/user/devices.dg',
                 'kernel/user/device_manager.dg', 'tests/usb_only_policy_probe.dg',
                 'tests/usb_only_policy_probe.c', 'tests/test_usb_only_profile.py',
                 'tools/usb_only_profile.py')]
        snapshot = lambda: {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
        before = snapshot()
        out = ROOT/'build/test/usb-only-profile'/('run-'+uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        save(out/'source-before.json', before)
        # Compile the exact definition emitted by the real profile generator,
        # rather than a second handwritten true-profile template.
        from tools.usb_only_profile import generate, verify
        profile_input = out/'profile-input'
        (profile_input/'services/lib').mkdir(parents=True)
        (profile_input/'services/lib/hardware_profile.dg').write_bytes(DEFAULT_PROFILE)
        generated, generated_metadata = generate(out/'profile-generated', source_root=profile_input)
        verify(out/'profile-generated', generated_metadata, source_root=profile_input)
        usb_profile = (Path(generated)/'lib/hardware_profile.dg').read_bytes()
        save(out/'generated-profile.json', generated_metadata)
        commands, results = [], []
        policy = (ROOT/'services/drivers/device_policy.dg').read_text(encoding='utf-8')
        ledger = (ROOT/'kernel/user/device_manager.dg').read_text(encoding='utf-8')
        devices = (ROOT/'kernel/user/devices.dg').read_text(encoding='utf-8')
        cases = [('default', False), ('usb', True), ('omit-policy', True),
                 ('omit-ledger-policy', True), ('omit-admit', True), ('omit-grant', True)]

        def run(argv, directory, label, expected=0):
            argv = list(map(str, argv))
            done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=90)
            value = dict(argv=argv, returncode=done.returncode, stdout=done.stdout, stderr=done.stderr)
            save(directory/(label+'.json'), value)
            commands.append(value)
            self.assertEqual(expected, done.returncode, done.stdout+done.stderr)
            return done

        try:
            for case, usb in cases:
                for mode in ('debug', 'release'):
                    directory = out/(case+'-'+mode)
                    services, kernel = directory/'services', directory/'kernel'
                    (services/'lib').mkdir(parents=True)
                    (services/'drivers').mkdir()
                    (kernel/'user').mkdir(parents=True)
                    shutil.copyfile(ROOT/'services/lib/device_abi.dg', services/'lib/device_abi.dg')
                    (services/'lib/hardware_profile.dg').write_bytes(usb_profile if usb else DEFAULT_PROFILE)
                    changed_policy, changed_ledger, changed_devices = policy, ledger, devices
                    mutation = None
                    if case == 'omit-policy':
                        needle = 'if hardware_profile.USB_ONLY {return 0;}'
                        self.assertEqual(policy.count(needle), 1)
                        changed_policy = policy.replace(needle, '// actual bad source omits USB-only rank restriction', 1)
                        mutation = 'removed production role restriction'
                    elif case == 'omit-ledger-policy':
                        needle = 'if rank(old,role)==0 {return error.abi.Denied;}'
                        self.assertEqual(ledger.count(needle), 1)
                        changed_ledger = ledger.replace(needle, '// actual bad source permits zero-rank binding', 1)
                        mutation = 'removed production kernel ledger check'
                    elif case in ('omit-admit', 'omit-grant'):
                        function = case.removeprefix('omit-')
                        needle = first_guard(devices, function)
                        self.assertEqual(devices.count(needle), 1)
                        changed_devices = devices.replace(needle, '', 1)
                        mutation = 'removed first production ' + function + ' guard'
                    (services/'drivers/device_policy.dg').write_text(changed_policy, encoding='utf-8')
                    (kernel/'user/device_manager.dg').write_text(changed_ledger, encoding='utf-8')
                    (directory/'devices-input.dg').write_text(changed_devices, encoding='utf-8')
                    (directory/'usb_only_claim_guard.dg').write_text(guard_module(changed_devices), encoding='utf-8')
                    save(directory/'scope.json', dict(profile=usb, mutation=mutation,
                         full_production_modules=['drivers.device_policy', 'user.device_manager'],
                         actual_early_guard_fragments=['user.devices.grant', 'user.devices.admit'],
                         privileged_remainder='counted native hardware callbacks; no actual I/O'))
                    compiled = compile_file(ROOT/'tests/usb_only_policy_probe.dg',
                        roots=[ROOT/'tests', directory, kernel, services, ROOT/'lang/std'], mode=mode)
                    layouts = {t['full_name']: t for t in compiled.layout_manifest['types']}
                    self.assertEqual(layouts['user.device_manager.Table']['size'], 4560)
                    assembly = directory/'probe.asm'
                    assembly.write_text(compiled.assembly, encoding='utf-8')
                    objects = {}
                    for fmt in ('elf64', 'win64'):
                        obj = directory/(fmt+'.o')
                        run([nasm, '-f', fmt, *nasm_flags(nasm), '-o', obj, assembly], directory, 'assemble-'+fmt)
                        objects[fmt] = obj
                    binary = directory/('probe.exe' if os.name=='nt' else 'probe')
                    run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                         '-D__USE_MINGW_ANSI_STDIO=1', *([] if os.name=='nt' else ['-no-pie']),
                         ROOT/'tests/usb_only_policy_probe.c', objects['win64' if os.name=='nt' else 'elf64'],
                         '-o', binary], directory, 'link')
                    bad = case.startswith('omit-')
                    executed = run([binary, 'usb' if usb else 'default'], directory, 'native', 1 if bad else 0)
                    self.assertIn('USB_ONLY_ASSERT' if bad else 'USB_ONLY_NATIVE passed', executed.stdout+executed.stderr)
                    self.assertIn('returned normally', executed.stdout+executed.stderr)
                    results.append(dict(case=case, mode=mode, returncode=executed.returncode,
                                        stdout=executed.stdout, stderr=executed.stderr))
            self.assertEqual(before, snapshot(), 'production inputs changed')
        finally:
            save(out/'source-after.json', snapshot())
            save(out/'commands.json', commands)
            save(out/'result.json', dict(source_stable=before==snapshot(), results=results,
                                        vm_executed=False, physical_devices_accessed=False))
        print('USB_ONLY_NATIVE_EVIDENCE '+str(out))

    def test_generated_snapshot_binds_every_service_and_rejects_tampering(self):
        from tools.usb_only_profile import generate, verify
        out = ROOT/'build/test/usb-only-profile'/('snapshot-'+uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        # A private input tree keeps concurrent unrelated development outside
        # this generator test; the complete frozen service set is still bound.
        source_root = out/'input'
        for path in list((ROOT/'services').rglob('*.dg')):
            copied = source_root/'services'/path.relative_to(ROOT/'services')
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(path.read_bytes())
        output = out/'generated'
        services, metadata = generate(output, source_root=source_root)
        services = Path(services)
        verify(output, metadata, source_root=source_root)
        self.assertTrue(metadata['usb_only'])
        self.assertEqual(metadata['version'], 1)
        self.assertEqual(metadata['source'], 'usb-only-services/lib/hardware_profile.dg')
        generated = (services/'lib/hardware_profile.dg').read_bytes()
        self.assertIn(b'pub const USB_ONLY:bool=true;', generated)
        self.assertIn(b'pub const FAT_AUDIT_BYTES:usize=2097152;', generated)
        source_files = {str(p.relative_to(source_root/'services')) for p in (source_root/'services').rglob('*.dg')}
        staged_files = {str(p.relative_to(services)) for p in services.rglob('*.dg')}
        self.assertEqual(source_files, staged_files)
        for name in source_files-{'lib\\hardware_profile.dg', 'lib/hardware_profile.dg'}:
            self.assertEqual((source_root/'services'/name).read_bytes(), (services/name).read_bytes())
        path = services/'lib/hardware_profile.dg'
        path.write_bytes(generated.replace(b'USB_ONLY:bool=true', b'USB_ONLY:bool=false'))
        with self.assertRaises(ValueError): verify(output, metadata, source_root=source_root)
        path.write_bytes(generated)
        extra = services/'lib/unlisted.dg'
        extra.write_text('module lib.unlisted;\n', encoding='utf-8')
        with self.assertRaises(ValueError): verify(output, metadata, source_root=source_root)
        extra.unlink()
        changed = dict(metadata, sha256='0'*64)
        with self.assertRaises(ValueError): verify(output, changed, source_root=source_root)
        original = (source_root/'services/drivers/device_policy.dg').read_bytes()
        (source_root/'services/drivers/device_policy.dg').write_bytes(original+b'\n// changed after generation\n')
        with self.assertRaises(ValueError): verify(output, metadata, source_root=source_root)
        (source_root/'services/drivers/device_policy.dg').write_bytes(original)
        verify(output, metadata, source_root=source_root)


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Actual pure Dong USB partition parser and address translation, no hardware."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'services/drivers/usb_partition.dg'
PROBE = ROOT / 'tests/usb_partition_probe.dg'
C_PROBE = ROOT / 'tests/usb_partition_probe.c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class UsbPartitionTests(unittest.TestCase):
    def test_actual_bpb_mbr_bounds_translation_and_real_bad_sources(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'native NASM/GCC required; zero skips')
        paths = [MODULE, PROBE, C_PROBE, Path(__file__), ROOT / 'lang/tests/test_dongc.py']
        frozen = lambda: {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
        before = frozen()
        out = ROOT / 'build/test/usb-partition' / ('run-' + uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        def save(path, value):
            path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        save(out / 'source-before.json', before)
        save(out / 'tools.json', {role: {'path': str(Path(path).resolve()), 'sha256': sha(path)}
             for role, path in [('python', sys.executable), ('nasm', nasm), ('cc', cc)]})
        original = MODULE.read_text(encoding='utf-8')
        mutations = {
            'partition-overrun': ('||capacity>disk_sectors-base', '||false'),
            'multiple-partitions': ('if found!=1 {return error.Invalid;}', 'if found==0 {return error.Invalid;}'),
            'unsupported-type': ('if kind!=0x0b&&kind!=0x0c&&kind!=0xef {return error.Unsupported;}', ''),
            'forged-view-overrun': ('||v.capacity>v.disk_capacity-v.base', '||false'),
            'request-overrun': ('||count>v.capacity-lba', '||false'),
            'early-publish': ('let p=sector.ptr;', '*out=EMPTY;let p=sector.ptr;'),
            'disguised-mbr': ('if partition_shape {return error.Invalid;}', ''),
        }
        variants = {'normal': original}
        for name, (needle, replacement) in mutations.items():
            self.assertEqual(original.count(needle), 1, name)
            variants[name] = original.replace(needle, replacement, 1)
        receipts = []
        def command(args, state, name, expected=0):
            args = list(map(str, args))
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=60)
            record = dict(argv=args, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            save(state / (name + '.json'), record)
            receipts.append(record)
            self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
            return result
        try:
            flags = nasm_flags(nasm)
            for variant, text in variants.items():
                for mode in ('debug', 'release'):
                    state = out / (variant + '-' + mode)
                    stage = state / 'services/drivers'
                    stage.mkdir(parents=True)
                    (stage / 'usb_partition.dg').write_text(text, encoding='utf-8')
                    compiled = compile_file(PROBE, roots=[ROOT / 'tests', state / 'services', ROOT / 'lang/std'], mode=mode)
                    layout = {item['full_name']: item for item in compiled.layout_manifest['types']}
                    view = layout['drivers.usb_partition.View']
                    self.assertEqual((view['size'], view['alignment']), (24, 8))
                    self.assertEqual([(f['name'], f['offset']) for f in view['fields']],
                                     [('base', 0), ('capacity', 8), ('disk_capacity', 16)])
                    save(state / 'layout.json', compiled.layout_manifest)
                    assembly = state / 'probe.asm'
                    assembly.write_text(compiled.assembly, encoding='utf-8')
                    objects = {}
                    for fmt in ('elf64', 'win64'):
                        obj = state / (fmt + '.o')
                        command([nasm, '-f', fmt, *flags, '-o', obj, assembly], state, 'assemble-' + fmt)
                        objects[fmt] = obj
                    for optimization in ('0', '2'):
                        executable = state / ('probe-O' + optimization + ('.exe' if os.name == 'nt' else ''))
                        host_flags = ['-mno-sse'] if os.name == 'nt' else ['-no-pie']
                        command([cc, '-std=c11', '-O' + optimization, '-Wall', '-Wextra', '-Werror',
                                 '-D__USE_MINGW_ANSI_STDIO=1', *host_flags, C_PROBE,
                                 objects['win64' if os.name == 'nt' else 'elf64'], '-o', executable],
                                state, 'link-O' + optimization)
                        result = command([executable], state, 'native-O' + optimization,
                                         0 if variant == 'normal' else 1)
                        self.assertIn('USB partition native checks passed' if variant == 'normal'
                                      else 'USB_PARTITION_ASSERT', result.stdout + result.stderr)
                        self.assertIn('returned normally', result.stdout + result.stderr)
            self.assertEqual(before, frozen(), 'partition test source changed')
        finally:
            after = frozen()
            save(out / 'source-after.json', after)
            save(out / 'commands.json', receipts)
            save(out / 'result.json', dict(source_stable=before == after, variants=list(variants),
                 compiler_modes=['debug', 'release'], native_optimizations=['O0', 'O2'],
                 assembled_formats=['elf64', 'win64'], vm_executed=False, hardware_io=False))
        print('USB_PARTITION_EVIDENCE ' + str(out))


if __name__ == '__main__':
    unittest.main(verbosity=2)

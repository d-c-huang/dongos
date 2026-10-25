"""Native ELF fixtures for the CPU observer; no kernel or VM is executed."""
from pathlib import Path
import hashlib
import inspect
import json
import struct
import subprocess
import unittest
import uuid

from lang.tests.test_dongc import nasm_flags
from tests.run_cpu_qemu import REQUIRED_SYMBOLS, read_elf_symbols
from tools.build import find_tool


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('tests/run_cpu_qemu.py', 'tests/test_cpu_elf_symbols.py',
          'lang/tests/test_dongc.py', 'tools/build.py', 'tools/elf_symbols.py')


def fingerprints():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INPUTS}


def symbol_entries(data):
    """Inspect the real linked table independently to target exact mutations."""
    offset = struct.unpack_from('<Q', data, 40)[0]
    stride, count = struct.unpack_from('<HH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * stride) for i in range(count)]
    entries = []
    for number, section in enumerate(sections):
        if section[1] != 2:
            continue
        strings_section = sections[section[6]]
        strings = data[strings_section[4]:strings_section[4] + strings_section[5]]
        for at in range(section[4], section[4] + section[5], section[9]):
            name, info, _, index, value, _ = struct.unpack_from('<IBBHQQ', data, at)
            if name:
                text = strings[name:strings.index(0, name)].decode('utf-8')
                entries.append(dict(name=text, name_offset=name, info=info, index=index,
                                    value=value, offset=at, section=number))
    return entries, sections, offset, stride


class CpuElfSymbolsTests(unittest.TestCase):
    def test_real_two_translation_units_and_strict_negative_fixtures(self):
        before = fingerprints()
        state = ROOT / 'build/test/p8-symbol' / ('run-' + uuid.uuid4().hex[:12])
        state.mkdir(parents=True)
        nasm = find_tool('nasm', 'NASM')
        linker = find_tool('ld.lld', 'LD_LLD')
        evidence = dict(sources_before=before, commands=[], results=[])

        def command(arguments, name):
            result = subprocess.run([str(x) for x in arguments], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
            record = dict(command=[str(x) for x in arguments], returncode=result.returncode,
                          stdout=result.stdout, stderr=result.stderr)
            (state / (name + '.json')).write_text(json.dumps(record, indent=2))
            evidence['commands'].append(record)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        # Each NASM invocation resets %% macro-label numbering. The linker must
        # retain the repeated private local names at distinct final addresses.
        common = ('bits 64\n%macro RECORD 0\n%%recorded:\n    nop\n%endmacro\n'
                  'section .text\nRECORD\n')
        required = ''.join('global ' + name + '\n' + name + ': nop\n' for name in sorted(REQUIRED_SYMBOLS))
        left = state / 'left.asm'
        right = state / 'right.asm'
        duplicate = state / 'right-ordinary-duplicate.asm'
        left.write_text(common + 'ordinary_left: nop\n' + required)
        right.write_text(common + 'ordinary_right: nop\n')
        duplicate.write_text(common + 'ordinary_left: nop\n')
        for source in (left, right, duplicate):
            command([nasm, '-f', 'elf64', *nasm_flags(nasm), source, '-o', source.with_suffix('.o')], source.stem)
        fixture = state / 'private-locals.elf'
        ordinary_fixture = state / 'ordinary-locals.elf'
        for path, second in ((fixture, right), (ordinary_fixture, duplicate)):
            command([linker, '-m', 'elf_x86_64', '-e', 'cpu_test_expected_rip',
                     left.with_suffix('.o'), second.with_suffix('.o'), '-o', path], path.stem)
        data = fixture.read_bytes()
        entries, sections, shoff, shstride = symbol_entries(data)
        private = [entry for entry in entries if entry['name'].startswith('..@')]
        self.assertEqual(2, len(private))
        self.assertEqual(private[0]['name'], private[1]['name'])
        self.assertNotEqual(private[0]['value'], private[1]['value'])
        self.assertEqual([0, 0], [entry['info'] for entry in private])
        symbols = read_elf_symbols(fixture)
        self.assertTrue(REQUIRED_SYMBOLS <= symbols.keys())
        for entry in entries:
            if entry['name'] in REQUIRED_SYMBOLS:
                self.assertEqual(entry['value'], symbols[entry['name']])
        self.assertFalse(any(name.startswith('..@') for name in symbols))
        self.assertIn('ordinary_left', symbols)
        self.assertIn('ordinary_right', symbols)
        evidence['results'].append(dict(case='real-private-locals', accepted=True,
                                        fixture_sha256=hashlib.sha256(data).hexdigest(), private_entries=private))

        def rejected(name, contents, message):
            path = state / (name + '.elf')
            path.write_bytes(contents)
            with self.subTest(case=name), self.assertRaisesRegex(ValueError, message):
                read_elf_symbols(path)
            evidence['results'].append(dict(case=name, accepted=False,
                                            fixture_sha256=hashlib.sha256(contents).hexdigest()))

        rejected('real-ordinary-locals', ordinary_fixture.read_bytes(), 'ambiguous ELF symbol.*ordinary_left')
        ordinary_data = bytearray(ordinary_fixture.read_bytes())
        ordinary_entries = [entry for entry in symbol_entries(ordinary_data)[0] if entry['name'] == 'ordinary_left']
        self.assertEqual(2, len(ordinary_entries))
        for binding in (1, 2):
            changed = bytearray(ordinary_data)
            for entry in ordinary_entries:
                changed[entry['offset'] + 4] = binding << 4
            rejected('ordinary-binding-' + str(binding), changed, 'ambiguous ELF symbol.*ordinary_left')
        # Bindings/types are changed at exact real symbol records. The name
        # prefix alone must never suppress a global, weak, or typed local.
        for name, info in (('global-private-prefix', 0x10), ('weak-private-prefix', 0x20),
                           ('function-local-private-prefix', 0x02), ('object-local-private-prefix', 0x01)):
            changed = bytearray(data)
            for entry in private:
                changed[entry['offset'] + 4] = info
            rejected(name, changed, 'ambiguous ELF symbol')

        required_entry = next(entry for entry in entries if entry['name'] == 'cpu_test_expected_rip')
        changed = bytearray(data)
        for entry in private:
            struct.pack_into('<I', changed, entry['offset'], required_entry['name_offset'])
        rejected('ambiguous-required-symbol', changed, 'ambiguous ELF symbol.*cpu_test_expected_rip')
        changed = bytearray(data)
        struct.pack_into('<H', changed, required_entry['offset'] + 6, 0)
        rejected('missing-required-symbol', changed, 'missing CPU ELF symbols.*cpu_test_expected_rip')

        # Existing same-value behavior is retained for nonprivate symbols.
        changed = bytearray(data)
        for entry in private:
            changed[entry['offset'] + 4] = 0x10
            struct.pack_into('<Q', changed, entry['offset'] + 8, private[0]['value'])
        same = state / 'same-value-global.elf'
        same.write_bytes(changed)
        self.assertEqual(private[0]['value'], read_elf_symbols(same)[private[0]['name']])
        evidence['results'].append(dict(case='same-value-global', accepted=True))

        for length in (0, 63, len(data) - 1):
            rejected('truncated-' + str(length), data[:length], 'truncated|invalid ELF')
        symbol_section = next(entry['section'] for entry in private)
        changed = bytearray(data)
        struct.pack_into('<Q', changed, shoff + symbol_section * shstride + 24, len(data) + 1)
        rejected('symbol-table-outside-file', changed, 'truncated or invalid ELF table')
        changed = bytearray(data)
        struct.pack_into('<I', changed, shoff + symbol_section * shstride + 40, len(sections))
        rejected('invalid-string-table-link', changed, 'invalid ELF symbol/string table')
        changed = bytearray(data)
        struct.pack_into('<I', changed, private[0]['offset'], 0xffffffff)
        rejected('private-name-outside-string-table', changed, 'invalid ELF symbol name')

        # Execute the real previous parser body against the very same linked
        # fixture: the regression test must reproduce the original failure.
        source = inspect.getsource(read_elf_symbols)
        needle = '            if text.startswith("..@") and info == 0:\n                continue\n'
        self.assertEqual(1, source.count(needle))
        old_source = source.replace(needle, '')
        (state / 'old-observer-control.py').write_text(old_source)
        namespace = dict(Path=Path, struct=struct, REQUIRED_SYMBOLS=REQUIRED_SYMBOLS)
        exec(compile(old_source, str(state / 'old-observer-control.py'), 'exec'), namespace)
        with self.assertRaisesRegex(ValueError, 'ambiguous ELF symbol.*recorded'):
            namespace['read_elf_symbols'](fixture)
        evidence['results'].append(dict(case='actual-old-observer-control', accepted=False))
        evidence['sources_after'] = fingerprints()
        (state / 'summary.json').write_text(json.dumps(evidence, indent=2))
        self.assertEqual(before, evidence['sources_after'], 'source changed during ELF fixture verification')
        print('CPU_ELF_SYMBOL_EVIDENCE', state)

"""Native execution of the actual bounded EFI console helper; never a VM."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
import uuid

from lang.tests.test_dongc import nasm_flags, tool

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'boot/loader_console.asm'
ENTRY = ROOT / 'boot/efi_main.asm'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def bridge(entry, *, mirror_shadow_alias=False):
    # Retain the actual nonprivileged diagnostic mirror instruction body.
    start = entry.index('\ndiagnostic_write:')
    end = entry.index('\n; Direct 16550', start)
    mirror = entry[start:end].replace('diagnostic_write:', 'probe_diagnostic_write:', 1)
    if mirror_shadow_alias:
        needle = 'lea     rdx, [rsp + 32]'
        if mirror.count(needle) != 1:
            raise AssertionError('unique wrapper shadow mutation anchor')
        mirror = mirror.replace(needle, 'lea     rdx, [rsp]', 1)
    mirror = mirror.replace('call    loader_console_write', 'call    probe_mirror_console_write', 1)
    out = ['bits 64', 'default rel', 'section .text',
           'global probe_invoke,probe_output_string,probe_diagnostic_write',
           'extern loader_console_write,loader_console_probe_output',
           'extern probe_callback_rsp_mod,probe_serial_calls,probe_serial_pointer', mirror,
           'probe_mirror_console_write:']
    # This shim uses the space a legitimate MS ABI callee is free to overwrite.
    # The extracted production wrapper must keep its ASCII input above it.
    for offset in (8, 16, 24, 32):
        out += [f'mov qword [rsp+{offset}],0x5a5a5a5a']
    out += ['jmp loader_console_write',
           'serial_write:', 'inc qword [rel probe_serial_calls]',
           'mov [rel probe_serial_pointer],rcx', 'ret',
           'probe_output_string:', 'mov rax,rsp', 'and eax,15',
           'mov [rel probe_callback_rsp_mod],rax']
    # A real firmware callee owns these 32 bytes. A helper incorrectly putting
    # UTF16 into its shadow area will corrupt its observable callback input.
    for offset in (8, 16, 24, 32):
        out += [f'mov qword [rsp+{offset}],0x5a5a5a5a']
    out += ['sub rsp,40', 'call loader_console_probe_output', 'add rsp,40']
    for register in ('rcx', 'rdx', 'r8', 'r9', 'r10', 'r11'):
        out += [f'mov {register},0x123456789abcdef0']
    out += ['ret', 'probe_invoke:']
    registers = ('rbx', 'rbp', 'rdi', 'rsi', 'r12', 'r13', 'r14', 'r15')
    out += ['push ' + register for register in registers]
    out += ['sub rsp,248', 'mov [rsp+32],rcx', 'mov [rsp+40],rdx']
    for index in range(10):
        out += [f'movdqu [rsp+{48+index*16}],xmm{index+6}',
                f'movdqu xmm{index+6},[rel probe_canary]']
    out += [f'mov {register},0x1122334455667788' for register in registers]
    out += ['mov rcx,[rsp+40]', 'call [rsp+32]', 'xor r10d,r10d']
    for register in registers:
        out += ['mov rax,0x1122334455667788', f'cmp {register},rax',
                'je $+6', 'or r10d,1']
    for index in range(10):
        out += [f'movdqa xmm0,xmm{index+6}', 'pcmpeqb xmm0,[rel probe_canary]',
                'pmovmskb eax,xmm0', 'cmp eax,65535', 'je $+6', 'or r10d,2']
    for index in range(10):
        out += [f'movdqu xmm{index+6},[rsp+{48+index*16}]']
    out += ['mov rax,r10', 'add rsp,248']
    out += ['pop ' + register for register in reversed(registers)]
    out += ['ret', 'section .rodata', 'align 16',
            'probe_canary: dq 0x123456789abcdef0,0xfedcba9876543210',
            '%ifidn __OUTPUT_FORMAT__,elf64', 'section .note.GNU-stack noalloc noexec nowrite', '%endif']
    return '\n'.join(out) + '\n'


class LoaderConsoleTests(unittest.TestCase):
    def test_real_console_native_abi_bounds_guard_seal_and_bad_sources(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'native NASM and GCC are required; zero skips')
        paths = [MODULE, ENTRY, ROOT / 'include/uefi.inc', Path(__file__),
                 ROOT / 'tests/loader_console_probe.c', ROOT / 'lang/tests/test_dongc.py']
        fingerprint = lambda: {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
        before = fingerprint()
        tools_before = {role: {'path': str(Path(path).resolve()), 'sha256': sha(path)}
                        for role, path in [('python', sys.executable), ('nasm', nasm), ('cc', cc)]}
        state = ROOT / 'build/test/loader-console' / ('run-' + uuid.uuid4().hex[:12])
        state.mkdir(parents=True)
        save(state / 'source-before.json', before)
        save(state / 'tools-before.json', tools_before)
        commands = []

        def run(argv, label, expected=0):
            argv = list(map(str, argv))
            completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
            receipt = dict(argv=argv, cwd=str(ROOT), returncode=completed.returncode,
                           stdout=completed.stdout, stderr=completed.stderr)
            save(state / (label + '.json'), receipt)
            commands.append(receipt)
            self.assertEqual(expected, completed.returncode, completed.stdout + completed.stderr)
            return completed

        original = MODULE.read_text(encoding='utf-8')
        cases = {'normal': original}
        needle = 'mov     qword [rel loader_console_table], 0'
        self.assertEqual(original.count(needle), 1)
        cases['omit-seal'] = original.replace(needle, '; real bad source omits seal', 1)
        needle = 'lea     rdx, [rsp + 32]'
        self.assertEqual(original.count(needle), 1)
        cases['shadow-alias'] = original.replace(needle, 'lea     rdx, [rsp]', 1)
        cases['mirror-shadow-alias'] = original
        try:
            run([cc, '--version'], 'cc-version')
            flags = nasm_flags(nasm)
            host_format = 'win64' if os.name == 'nt' else 'elf64'
            for name, source in cases.items():
                probe = state / (name + '-bridge.asm')
                probe.write_text(bridge(ENTRY.read_text(encoding='utf-8'),
                    mirror_shadow_alias=name == 'mirror-shadow-alias'), encoding='ascii')
                staged = state / (name + '.asm')
                staged.write_text(source, encoding='utf-8')
                objects = {}
                for fmt in ('elf64', 'win64'):
                    obj = state / (name + '-' + fmt + '.o')
                    run([nasm, *flags, '-f', fmt, '-I', str(ROOT / 'include') + os.sep,
                         '-o', obj, staged], name + '-' + fmt)
                    objects[fmt] = obj
                for optimization in ('0', '2'):
                    bridge_obj = state / ('bridge-' + optimization + '.o')
                    run([nasm, *flags, '-f', host_format, '-o', bridge_obj, probe],
                        name + '-bridge-' + optimization)
                    exe = state / (name + '-O' + optimization + ('.exe' if os.name == 'nt' else ''))
                    run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O' + optimization,
                         '-D__USE_MINGW_ANSI_STDIO=1', '-maccumulate-outgoing-args',
                         ROOT / 'tests/loader_console_probe.c', objects[host_format], bridge_obj,
                         '-o', exe], name + '-link-' + optimization)
                    result = run([exe], name + '-run-' + optimization, 0 if name == 'normal' else 1)
                    self.assertIn('returned normally', result.stdout + result.stderr)
                    if name == 'normal':
                        self.assertIn('loader console oracle passed', result.stdout)
            self.assertEqual(before, fingerprint(), 'test source changed during native execution')
        finally:
            save(state / 'commands.json', commands)
            save(state / 'source-after.json', fingerprint())
            save(state / 'result.json', dict(source_stable=before == fingerprint(),
                 cases=list(cases), native_optimizations=['O0', 'O2'],
                 assembled_formats=['elf64', 'win64'], vm_executed=False))

    def test_loader_stages_console_before_uart_and_sealed_before_final_map(self):
        source = ENTRY.read_text(encoding='utf-8')
        body = source.split('\nefi_main:', 1)[1].split('\n; rcx pages,', 1)[0]
        self.assertLess(body.index('call    loader_console_initialize'), body.index('call    serial_init'))
        self.assertLess(body.index('call    loader_console_write'), body.index('call    serial_init'))
        seal = body.index('call    loader_console_seal')
        self.assertLess(seal, body.index('.map_retry:'))
        self.assertLess(seal, body.index('EFI_BOOT_SERVICES.GetMemoryMap'))
        self.assertNotIn('loader_console_initialize', body[seal:])
        fatal = source.split('\nfatal:', 1)[1].split('\n; RCX ASCII', 1)[0]
        self.assertIn('call    diagnostic_write', fatal)
        mirror = source.split('\ndiagnostic_write:', 1)[1].split('\n; Direct 16550', 1)[0]
        self.assertLess(mirror.index('call    loader_console_write'), mirror.index('call    serial_write'))
        self.assertRegex(mirror, r'mov\s+rcx,\s*\[rsp\s*\+\s*192\]')
        self.assertRegex(mirror, r'lea\s+rdx,\s*\[rsp\s*\+\s*32\]')
        self.assertIn('0x203a4e4545524353', mirror)
        self.assertRegex(mirror, r'cmp\s+r8d,\s*119')
        self.assertEqual(source.count('%include "boot/loader_console.asm"'), 1)
        for stage in ('S00', 'S01', 'S02', 'S03', 'S04', 'S05', 'S90'):
            self.assertIn(stage, source)


if __name__ == '__main__':
    unittest.main()

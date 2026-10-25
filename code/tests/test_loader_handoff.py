"""Execute safe production handoff preparation; never execute privileged blob."""
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
from lang.dongc import compile_file
from tools.gen_offsets import generate

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'boot/loader_handoff.asm'
ENTRY = ROOT / 'boot/efi_main.asm'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def abi_bridge():
    registers = ('rbx', 'rbp', 'rdi', 'rsi', 'r12', 'r13', 'r14', 'r15')
    out = ['bits 64', 'default rel', 'section .text', 'global handoff_probe_invoke',
           'handoff_probe_invoke:']
    out += ['push ' + register for register in registers]
    out += ['sub rsp,280', 'mov [rsp+32],rcx', 'mov [rsp+40],rdx',
            'mov [rsp+48],r8', 'mov [rsp+56],r9']
    for index in range(10):
        out += [f'movdqu [rsp+{80+index*16}],xmm{index+6}',
                f'movdqu xmm{index+6},[rel handoff_probe_canary]']
    out += [f'mov {register},0x1122334455667788' for register in registers]
    out += ['mov rcx,[rsp+40]', 'mov rdx,[rsp+48]', 'mov r8,[rsp+56]',
            'call [rsp+32]', 'mov [rsp+64],rax', 'xor r10d,r10d']
    for register in registers:
        out += ['mov rax,0x1122334455667788', f'cmp {register},rax',
                'je $+6', 'or r10d,1']
    for index in range(10):
        out += [f'movdqa xmm0,xmm{index+6}', 'pcmpeqb xmm0,[rel handoff_probe_canary]',
                'pmovmskb eax,xmm0', 'cmp eax,65535', 'je $+6', 'or r10d,2']
    for index in range(10):
        out += [f'movdqu xmm{index+6},[rsp+{80+index*16}]']
    out += ['mov rax,[rsp+64]', 'shl r10,32', 'or rax,r10', 'add rsp,280']
    out += ['pop ' + register for register in reversed(registers)]
    out += ['ret', 'section .rodata', 'align 16',
            'handoff_probe_canary: dq 0x123456789abcdef0,0xfedcba9876543210',
            '%ifidn __OUTPUT_FORMAT__,elf64', 'section .note.GNU-stack noalloc noexec nowrite', '%endif']
    return '\n'.join(out) + '\n'


class LoaderHandoffTests(unittest.TestCase):
    def test_actual_range_prepare_copy_bounds_abi_and_bad_sources(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'native NASM and GCC required; zero skips')
        paths = [MODULE, ENTRY, ROOT / 'include/bootinfo.inc', ROOT / 'include/uefi.inc',
                 Path(__file__), ROOT / 'tests/loader_handoff_probe.c',
                 ROOT / 'lang/tests/test_dongc.py', ROOT / 'tools/gen_offsets.py',
                 ROOT / 'lang/examples/boot/abi.dg']
        frozen = lambda: {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
        before = frozen()
        state = ROOT / 'build/test/loader-handoff' / ('run-' + uuid.uuid4().hex[:12])
        state.mkdir(parents=True)
        save(state / 'source-before.json', before)
        save(state / 'tools.json', {role: {'path': str(Path(path).resolve()), 'sha256': sha(path)}
             for role, path in [('python', sys.executable), ('nasm', nasm), ('cc', cc)]})
        commands = []

        def run(argv, label, expected=0):
            argv = list(map(str, argv))
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
            receipt = dict(argv=argv, cwd=str(ROOT), returncode=p.returncode,
                           stdout=p.stdout, stderr=p.stderr)
            commands.append(receipt)
            save(state / (label + '.json'), receipt)
            self.assertEqual(expected, p.returncode, p.stdout + p.stderr)
            return p

        source = MODULE.read_text(encoding='utf-8')
        cases = {'normal': source}
        mutations = {
            'omit-image-entry-upper-bound': ('        cmp     r8, r9\n        jae     .done',
                 '        cmp     r8, r9\n        ; real bad source omits upper-bound rejection'),
            'omit-capacity-check': ('        cmp     rdx, 4096\n        jb      .done',
                 '        cmp     rdx, 4096\n        ; real bad source omits capacity rejection'),
            'omit-kernel-target-patch': ('        mov     [r10 + loader_handoff_target - loader_handoff_template], r8',
                 '        ; real bad source omits kernel entry patch'),
            'escaped-return-rip-reference': ('        lea     rax, [rel .returned]',
                 '        lea     rax, [rel loader_image_range]'),
        }
        for name, (old, new) in mutations.items():
            self.assertIn(old, source, 'actual bad-source anchor: ' + name)
            cases[name] = source.replace(old, new, 1)
        try:
            flags = nasm_flags(nasm)
            run([cc, '--version'], 'cc-version')
            compiled = compile_file(ROOT / 'lang/examples/boot/abi.dg',
                roots=[ROOT / 'lang/examples'], mode='debug')
            (state / 'bootinfo_layout.inc').write_text(
                generate(compiled.layout_manifest, 'boot.abi.BootInfo'), encoding='ascii')
            save(state / 'layout.json', compiled.layout_manifest)
            wrapper = state / 'abi.asm'
            wrapper.write_text(abi_bridge(), encoding='ascii')
            host = 'win64' if os.name == 'nt' else 'elf64'
            wrapper_object = state / 'abi.o'
            run([nasm, *flags, '-f', host, '-o', wrapper_object, wrapper], 'abi-object')
            for name, content in cases.items():
                staged = state / (name + '.asm')
                staged.write_text(content, encoding='utf-8')
                objects = {}
                for fmt in ('elf64', 'win64'):
                    obj = state / (name + '-' + fmt + '.o')
                    run([nasm, *flags, '-f', fmt, '-I', str(ROOT / 'include') + os.sep,
                         '-I', str(state) + os.sep,
                         '-o', obj, staged], name + '-' + fmt)
                    objects[fmt] = obj
                for optimization in ('0', '2'):
                    exe = state / (name + '-O' + optimization + ('.exe' if os.name == 'nt' else ''))
                    run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O' + optimization,
                         '-D__USE_MINGW_ANSI_STDIO=1', '-maccumulate-outgoing-args',
                         ROOT / 'tests/loader_handoff_probe.c', objects[host], wrapper_object,
                         '-o', exe], name + '-link-' + optimization)
                    result = run([exe], name + '-run-' + optimization, 0 if name == 'normal' else 1)
                    self.assertIn('returned normally', result.stdout + result.stderr)
                    if name == 'normal':
                        self.assertIn('loader handoff oracle passed', result.stdout)
            self.assertEqual(before, frozen(), 'source changed during native test')
        finally:
            save(state / 'commands.json', commands)
            save(state / 'source-after.json', frozen())
            save(state / 'result.json', dict(source_stable=before == frozen(),
                 cases=list(cases), native_optimizations=['O0', 'O2'],
                 assembled_formats=['elf64', 'win64'], privileged_blob_executed=False))

    def test_entry_prepares_low_handoff_before_seal_and_jumps_before_cr3(self):
        source = ENTRY.read_text(encoding='utf-8')
        entry = source.split('\nefi_main:', 1)[1].split('\n; rcx pages,', 1)[0]
        self.assertIn('loader_image_range', entry)
        self.assertIn('loader_handoff_prepare', entry)
        self.assertLess(entry.index('loader_handoff_prepare'), entry.index('loader_console_seal'))
        handoff = entry.split('.firmware_exited:', 1)[1]
        self.assertRegex(handoff, r'jmp\s+(?:qword\s+)?\[\s*(?:rel\s+)?handoff_physical\s*\]')
        self.assertNotRegex(handoff, r'(?mi)^\s*mov\s+cr3\s*,')
        self.assertNotRegex(handoff, r'(?mi)^\s*(?:lgdt|lidt|retfq)\b')
        self.assertEqual(source.count('%include "boot/loader_handoff.asm"'), 1)
        range_check = entry.split('; Firmware may load the PE high;', 1)[1].split('EFI_BOOT_SERVICES.SetWatchdogTimer', 1)[0]
        self.assertNotRegex(range_check, r'(?mi)^\s*shr\s+\w+,\s*32')
        before_prepare = entry[:entry.index('call    loader_handoff_prepare')]
        self.assertRegex(before_prepare, r'mov\s+edx,\s*EfiLoaderCode\s*\n\s*call\s+allocate_low')
        transition = MODULE.read_text(encoding='utf-8').split('\nloader_handoff_template:', 1)[1]
        self.assertNotRegex(transition, r'(?mi)^\s*(?:call|extern)\b')
        entering_kernel = transition.split('\n.returned:', 1)[0]
        self.assertNotRegex(entering_kernel, r'(?mi)^\s*(?:mov|lea|pop|xor|add|sub|and|or|inc|dec)\s+(?:r13|[er]si|[er]dx|[er]cx)\s*[,\n]')


if __name__ == '__main__':
    unittest.main()

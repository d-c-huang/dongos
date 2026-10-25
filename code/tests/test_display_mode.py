"""Run the production Win64 GOP helper against ownership-aware fake firmware."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import unittest
import uuid
from lang.tests.test_dongc import tool, nasm_flags

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('boot/display_mode.asm', 'include/uefi.inc', 'tests/display_mode_probe.c', 'tests/test_display_mode.py')


def fingerprints():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INPUTS}


def abi_wrapper():
    # The callback thunks overwrite all shadow slots and check entry alignment.
    # The caller checks every Win64 nonvolatile GPR and XMM6..15 after the call.
    lines = ['section .text', 'global probe_abi', 'global query_thunk', 'global set_thunk', 'global free_thunk',
             'extern query_c', 'extern set_c', 'extern free_c', 'extern callback_alignment_errors', 'probe_abi:']
    saved = ('rbx', 'rbp', 'rdi', 'rsi', 'r12', 'r13', 'r14', 'r15')
    lines += ['    push ' + reg for reg in saved]
    lines += ['    sub rsp,232', '    mov [rsp+32],rcx', '    mov [rsp+40],rdx', '    mov [rsp+56],rsp']
    for number in range(6, 16):
        lines += [f'    movdqu [rsp+{64+(number-6)*16}],xmm{number}', f'    pcmpeqd xmm{number},xmm{number}']
    for number, reg in enumerate(saved, 1):
        lines += [f'    mov {reg},0x112233440000000{number:x}']
    lines += ['    mov rcx,[rsp+32]', '    mov rdx,[rsp+40]', '    call desktop_graphics_mode',
              '    mov [rsp+48],rax', '    cmp rsp,[rsp+56]', '    jne .abi_bad']
    for number, reg in enumerate(saved, 1):
        lines += [f'    mov rax,0x112233440000000{number:x}', f'    cmp {reg},rax', '    jne .abi_bad']
    for number in range(6, 16):
        lines += ['    pcmpeqd xmm0,xmm0', f'    pcmpeqd xmm0,xmm{number}', '    pmovmskb eax,xmm0',
                  '    cmp eax,65535', '    jne .abi_bad']
    lines += ['    jmp .restore', '.abi_bad:', '    or qword [rsp+48],2', '.restore:']
    for number in range(6, 16):
        lines += [f'    movdqu xmm{number},[rsp+{64+(number-6)*16}]']
    lines += ['    mov rax,[rsp+48]', '    add rsp,232']
    lines += ['    pop ' + reg for reg in reversed(saved)]
    lines += ['    ret']
    for name in ('query', 'set', 'free'):
        lines += [f'{name}_thunk:', '    mov rax,rsp', '    and eax,15', '    cmp eax,8', '    je .aligned',
                  '    inc dword [rel callback_alignment_errors]', '.aligned:', '    mov rax,0xa55aa55aa55aa55a']
        lines += [f'    mov [rsp+{offset}],rax' for offset in (8, 16, 24, 32)]
        lines += [f'    jmp {name}_c']
    return '\n'.join(lines) + '\n'


class DisplayModeTests(unittest.TestCase):
    def test_rank_fallback_actual_validation_cleanup_and_abi(self):
        state = ROOT / 'build/test/p8-gop' / ('run-' + uuid.uuid4().hex[:12])
        state.mkdir(parents=True)
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm)
        self.assertTrue(cc)
        before = fingerprints()
        raw = (ROOT / 'boot/display_mode.asm').read_text()
        variants = {'normal': raw}
        mutations = {
            'bad-free': ('    call [r12+EFI_BOOT_SERVICES.FreePool]\n',
                         '    xor eax,eax ; actual missing FreePool\n'),
            'bad-post-set': ('    call .valid_current\n    test eax,eax\n    jz .rank\n',
                             '    mov eax,1 ; actual skipped post-Set verification\n'),
            'bad-ranking': ('    mov rsi,[rdi+r14*8]\n',
                            '    mov esi,0x7fffffff ; actual first valid mode wins\n'),
        }
        for name, (needle, replacement) in mutations.items():
            self.assertEqual(1, raw.count(needle), name)
            variants[name] = raw.replace(needle, replacement)
        summary = {'sources_before': before, 'variants': {}}
        for name, body in variants.items():
            directory = state / name
            directory.mkdir()
            source = directory / 'helper-with-abi-probe.asm'
            source.write_text(body + '\n' + abi_wrapper())
            for fmt in ('win64', 'elf64'):
                obj = directory / ('gop-' + fmt + '.o')
                command = [nasm, '-f', fmt, *nasm_flags(nasm), '-I' + str(ROOT / 'include') + os.sep,
                           '-o', str(obj), str(source)]
                self.execute(command, directory / ('assembly-' + fmt + '.json'))
            obj = directory / ('gop-win64.o' if os.name == 'nt' else 'gop-elf64.o')
            exe = directory / ('probe.exe' if os.name == 'nt' else 'probe')
            command = [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
                       *([] if os.name == 'nt' else ['-no-pie']), str(ROOT / 'tests/display_mode_probe.c'),
                       str(obj), '-o', str(exe)]
            self.execute(command, directory / 'link.json')
            result = self.execute([str(exe)], directory / 'actual.json', check=False)
            summary['variants'][name] = {'returncode': result.returncode,
                                         'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
                                         'stdout': result.stdout, 'stderr': result.stderr}
            self.assertEqual(0 if name == 'normal' else 1, result.returncode, result.stdout + result.stderr)
            self.assertIn('actual mode/cleanup/ABI cases' if name == 'normal' else 'GOP oracle failed',
                          result.stdout if name == 'normal' else result.stderr)
        summary['sources_after'] = fingerprints()
        (state / 'summary.json').write_text(json.dumps(summary, indent=2))
        self.assertEqual(before, summary['sources_after'], 'GOP source changed during native verification')

    def execute(self, command, log, check=True):
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        log.write_text(json.dumps({'command': command, 'returncode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr}, indent=2))
        if check:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

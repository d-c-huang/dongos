"""Execute current configuration guards; lower only hardware effect boundaries."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_xhci_kernel import dependencies

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('raw64', 'record_configuration_denied', 'mmio_range', 'configuration_address', 'window', 'read32')
FIELDS = ('version', 'valid', 'reason', 'error_code', 'physical', 'bytes', 'ecam', 'descriptor_index',
          'kind', 'base', 'pages', 'attributes', 'mcfg_first', 'mcfg_end', 'framebuffer_base', 'framebuffer_bytes')


def sha(data): return hashlib.sha256(data).hexdigest()


def function(source, name):
    match = re.search(r'(?m)^(?:pub\s+)?unsafe\s+fn\s+' + name + r'\s*\(', source)
    if not match: raise AssertionError('actual function missing: ' + name)
    start = source.index('{', match.start()); depth = 1; end = start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}'); end += 1
    return source[match.start():end]


def declarations(source):
    start = source.index('pub struct ConfigurationConflict ')
    end = source.index('unsafe fn record_configuration_denied(', start)
    data = source[start:end]
    if data.count('pub var PCI_CONFLICT') != 1: raise AssertionError('one actual diagnostic storage required')
    return data


STUBS = {
    'boot.memory_startup': '''module boot.memory_startup;
import boot.runtime_view as runtime;import mm.paging as paging;
pub extern "sysv64" ("ecam_host_view") fn runtime_pointer()*const runtime.View;
pub extern "sysv64" ("ecam_host_space") fn space_pointer()*paging.Space;
''',
    'boot.device_memory': '''module boot.device_memory;
pub extern "sysv64" ("ecam_host_invalidate") fn runtime_invalidate(address:u64)void;
''',
    'mm.paging': '''module mm.paging;
pub const WRITE:u64=1;pub const UNCACHED:u64=8;
pub struct Space{pub words:[8]u64}
pub error Injected=0x0203_0999;
unsafe extern "sysv64" ("ecam_host_map") fn effect(s:*Space,v:u64,p:u64,flags:u64,replace:u64)u64;
pub unsafe fn map_live(s:*Space,v:u64,p:u64,flags:u64)!void{unsafe{if effect(s,v,p,flags,0)!=0{return error.Injected;}}return;}
pub unsafe fn replace_live(s:*Space,v:u64,p:u64,flags:u64)!void{unsafe{if effect(s,v,p,flags,1)!=0{return error.Injected;}}return;}
''',
}

BRIDGE = '''
// Native fixture controls inaccessible state; no production caller uses these.
export("ecam_reset") fn reset(base:u64,first:u64,last:u64,limit:u64)void{unsafe{
 REGION_BASE=base;REGION_FIRST=first;REGION_LAST=last;PHYSICAL_LIMIT=limit;CURRENT_PAGE=0;
 PCI_CONFLICT=EMPTY_CONFIGURATION_CONFLICT;
}return;}
export("ecam_guard") fn guard(pa:u64,bytes:u64,ecam:u64)u64{unsafe{match mmio_range(pa,bytes,ecam==1){ok=>{return 0;},err(e)=>{return e;},}}}
export("ecam_address") fn address(pa:u64,bytes:u64)u64{unsafe{match configuration_address(pa,bytes){ok=>{return 0;},err(e)=>{return e;},}}}
export("ecam_read") fn read(pa:u64,out:*u32)u64{unsafe{match read32(pa){ok(v)=>{*out=v;return 0;},err(e)=>{return e;},}}}
export("ecam_current") fn current()u64{unsafe{return CURRENT_PAGE;}}
export("ecam_context") fn context()*const ConfigurationConflict{unsafe{return &PCI_CONFLICT;}}
'''


def harness(source):
    bodies = {name: function(source, name) for name in NAMES}
    needle = 'return volatile_load(pointer as *const u32);'
    if bodies['read32'].count(needle) != 1: raise AssertionError('one physical volatile load boundary required')
    actual_read = bodies['read32'].replace(needle, 'return ecam_native_load(pointer);', 1)
    const = re.search(r'(?m)^const WINDOW:\s*u64\s*=\s*([^;]+);', source)
    if const is None: raise AssertionError('actual configuration WINDOW missing')
    prefix = '''module ecam_mmio_probe;
import boot.memory_startup as startup;import mm.paging as paging;import boot.device_memory as devices;
pub error Invalid=0x050a_0001;pub error Denied=0x050a_0002;
var REGION_BASE:u64=0;var REGION_FIRST:u64=0;var REGION_LAST:u64=0;var PHYSICAL_LIMIT:u64=0;var CURRENT_PAGE:u64=0;
unsafe extern "sysv64" ("ecam_host_load") fn ecam_native_load(pointer:u64)u32;
'''
    text = prefix + 'const WINDOW:u64=' + const[1] + ';\n' + declarations(source)
    text += '\n'.join(actual_read if name == 'read32' else bodies[name] for name in NAMES) + '\n' + BRIDGE
    for name in NAMES[:-1]:
        if text.count(bodies[name]) != 1: raise AssertionError('actual body not verbatim: ' + name)
    return text, bodies


def mutate(source, variant):
    runtime = 'let runtime_ecam=ecam && kind==11 && physical>=cfg_first && physical+bytes<=cfg_end;'
    changes = {
        'old-reject-runtime-ecam': (runtime, 'let runtime_ecam=false;'),
        'allow-runtime-bar': (runtime, 'let runtime_ecam=kind==11;'),
        'allow-runtime-reserved': (runtime, 'let runtime_ecam=ecam && (kind==11 || kind==0) && physical>=cfg_first && physical+bytes<=cfg_end;'),
        'omit-runtime-mcfg-bounds': (runtime, 'let runtime_ecam=ecam && kind==11;'),
        'allow-ram': ('kind != 11 && !reserved_ecam && !reserved_pci', 'kind != 11 && kind != 7 && !reserved_ecam && !reserved_pci'),
        'omit-framebuffer-conflict': ('if physical < fb+fb_bytes && fb < physical+bytes {', 'if false {'),
        'truncate-context-attributes': ('attributes:attributes,mcfg_first:', 'attributes:(attributes as u32) as u64,mcfg_first:'),
        'overwrite-first-context': ('if PCI_CONFLICT.valid!=0{return;}', ''),
        'omit-valid-publication': ('compiler_fence();PCI_CONFLICT.valid=1;', 'compiler_fence();'),
    }
    if variant == 'map-before-guard':
        original = function(source, 'window')
        if original.count('try mmio_range(page,4096,true);') != 1: raise AssertionError('actual guard anchor changed')
        bad = original.replace('try mmio_range(page,4096,true);', '', 1)
        bad = bad.replace('devices.runtime_invalidate(WINDOW);', 'try mmio_range(page,4096,true);\n            devices.runtime_invalidate(WINDOW);', 1)
        return source.replace(original, bad, 1)
    needle, replacement = changes[variant]
    if source.count(needle) != 1: raise AssertionError('unique actual bad-body anchor required: ' + variant)
    return source.replace(needle, replacement, 1)


class EcamMmioTests(unittest.TestCase):
    def test_actual_configuration_guards_context_and_bad_bodies(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'ECAM native oracle requires NASM and GCC; no skips')
        out = ROOT / 'build/test/ecam-mmio' / ('run-' + uuid.uuid4().hex[:12]); out.mkdir(parents=True)
        inputs = {ROOT / 'kernel/user/devices.dg', ROOT / 'tests/ecam_mmio_probe.c', Path(__file__).resolve()}
        for base in ('kernel', 'lang/std', 'lang/examples'):
            inputs.update((ROOT / base).rglob('*.dg'))
        inputs.update((ROOT / 'lang/dongc').rglob('*.py'))
        before = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in inputs}
        original = (ROOT / 'kernel/user/devices.dg').read_text(encoding='utf-8')
        results = []
        variants = ('normal', 'old-reject-runtime-ecam', 'allow-runtime-bar', 'allow-runtime-reserved',
                    'omit-runtime-mcfg-bounds', 'allow-ram', 'omit-framebuffer-conflict', 'map-before-guard',
                    'truncate-context-attributes', 'overwrite-first-context', 'omit-valid-publication')

        def execute(command, where, label):
            command = list(map(str, command)); run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
            (where / (label + '.json')).write_text(json.dumps(dict(command=command, returncode=run.returncode,
                stdout=run.stdout, stderr=run.stderr), indent=2) + '\n', encoding='utf-8')
            return run

        for variant in variants:
            for mode in ('debug', 'release'):
                where = out / variant / mode; where.mkdir(parents=True); stage = where / 'source'
                dependencies(stage, ['boot.memory_startup', 'boot.device_memory', 'mm.paging'], STUBS)
                source = original if variant == 'normal' else mutate(original, variant)
                text, bodies = harness(source); bridge = stage / 'ecam_mmio_probe.dg'; bridge.write_text(text, encoding='utf-8')
                (where / 'extraction.json').write_text(json.dumps(dict(production_path='kernel/user/devices.dg',
                    production_sha256=sha(original.encode()), actual_body_sha256={n: sha(b.encode()) for n, b in bodies.items()},
                    actual_policy_and_read_chain=True, volatile_load_only_lowered_in_read32=True,
                    stubs=STUBS, fixture_bridge=BRIDGE, actual_hardware_io=False, actual_page_tables=False), indent=2) + '\n', encoding='utf-8')
                compiled = compile_file(bridge, roots=[stage], mode=mode)
                types = {t['full_name']: t for t in compiled.layout_manifest['types']}
                self.assertEqual(160, types['boot.runtime_view.View']['size']); self.assertEqual(48, types['boot.runtime_view.Display']['size'])
                conflict = types['ecam_mmio_probe.ConfigurationConflict']
                self.assertEqual((128, 8), (conflict['size'], conflict['alignment']))
                self.assertEqual([(n, i * 8, 'u64') for i, n in enumerate(FIELDS)], [(f['name'], f['offset'], f['type']) for f in conflict['fields']])
                (where / 'layout.json').write_text(json.dumps(compiled.layout_manifest, indent=2) + '\n', encoding='utf-8')
                asm = where / 'probe.asm'; asm.write_text(compiled.assembly, encoding='utf-8')
                self.assertNotRegex(compiled.assembly.lower(), r'\b(?:invlpg|rdmsr|wrmsr|cr[0348])\b')
                obj = where / 'probe.o'
                for fmt in ('elf64', 'win64'):
                    dest = obj if fmt == ('win64' if os.name == 'nt' else 'elf64') else where / (fmt + '.o')
                    run = execute([nasm, '-f', fmt, *nasm_flags(nasm), '-o', dest, asm], where, 'assemble-' + fmt)
                    self.assertEqual(0, run.returncode, run.stdout + run.stderr)
                for optimization in (('-O0', '-O2') if variant == 'normal' else ('-O2',)):
                    binary = where / ('probe' + optimization + ('.exe' if os.name == 'nt' else ''))
                    run = execute([cc, '-std=c11', optimization, '-Wall', '-Wextra', '-Werror',
                        '-D__USE_MINGW_ANSI_STDIO=1', *(['-mno-sse'] if os.name == 'nt' else ['-no-pie']),
                        ROOT / 'tests/ecam_mmio_probe.c', obj, '-o', binary], where, 'link' + optimization)
                    self.assertEqual(0, run.returncode, run.stdout + run.stderr)
                    run = execute([binary], where, 'native' + optimization)
                    if variant == 'normal':
                        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
                        self.assertIn('ECAM_MMIO_NATIVE_OK', run.stdout)
                    else:
                        self.assertEqual(1, run.returncode, run.stdout + run.stderr)
                        self.assertIn('ECAM_NATIVE_ASSERT', run.stderr)
                        self.assertNotRegex(run.stderr.lower(), r'panic|segmentation|access violation')
                    results.append(dict(variant=variant, mode=mode, optimization=optimization,
                        returncode=run.returncode, stdout=run.stdout, stderr=run.stderr, assembly_sha256=sha(asm.read_bytes())))
        after = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in inputs}
        self.assertEqual(before, after, 'actual policy/probe/compiler changed during execution')
        (out / 'validation-summary.json').write_text(json.dumps(dict(passed=True, skips=0, source_stable=True,
            source_sha256=after, actual_policy_and_read_chain=True, actual_hardware_io=False,
            actual_page_tables=False, results=results), indent=2) + '\n', encoding='utf-8')
        print('ECAM_MMIO_EVIDENCE', out)


if __name__ == '__main__': unittest.main(verbosity=2)

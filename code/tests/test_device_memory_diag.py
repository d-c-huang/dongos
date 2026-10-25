"""Execute real device prepare/policy with counted external paging fixtures.

The two production modules are copied byte-for-byte; only three dependencies
are typed host adapters. No hardware, page tables, VM, or privileged op runs.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import unittest
import uuid

from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags, tool
from tests.test_input import command

ROOT = Path(__file__).resolve().parents[1]

BRIDGE = '''module device_memory_diag_probe;
import boot.device_memory as device;
import boot.device_policy as policy;
import boot.preflight as preflight;
export("dm_prepare") fn prepare(s:*const preflight.State,v:*policy.Views)u64{unsafe{
 match device.prepare(s,v){ok=>{return 0;},err(code)=>{return code;},}
}}
export("dm_prepare_diag") fn diagnostic(s:*const preflight.State,v:*policy.Views,c:*policy.Conflict)u64{unsafe{
 match device.prepare_diagnostic(s,v,c){ok=>{return 0;},err(code)=>{return code;},}
}}
export("dm_plan") fn plan()*const policy.Plan{return device.plan_pointer();}
'''
FIXTURE_EXPORTS = '''
// Host fixture only: reset inaccessible production state between independent
// cases, and read private failure atomicity. Never called by production code.
export("dm_reset") fn fixture_reset()void{unsafe{ATTEMPTED=false;READY=false;PLAN=policy.EMPTY_PLAN;}return;}
export("dm_storage") fn fixture_storage()*const policy.Plan{unsafe{return &PLAN;}}
export("dm_state") fn fixture_state()u64{unsafe{var n:u64=0;if ATTEMPTED{n=1;}if READY{n+=2;}return n;}}
'''
STUBS = {
    'boot/memory_startup.dg': '''module boot.memory_startup;
import boot.runtime_view as runtime;import boot.memory_resources as resources;import mm.paging as paging;
pub extern "sysv64" ("dm_host_view") fn runtime_pointer()*const runtime.View;
pub extern "sysv64" ("dm_host_space") fn space_pointer()*paging.Space;
pub extern "sysv64" ("dm_host_manifest") fn manifest_pointer()*const resources.Resource;
''',
    'boot/acpi_startup.dg': '''module boot.acpi_startup;import firmware.acpi as acpi;
pub extern "sysv64" ("dm_host_inventory") fn inventory_pointer()*const acpi.Inventory;
''',
    'mm/paging.dg': '''module mm.paging;
pub const WRITE:u64=1;pub const UNCACHED:u64=8;
pub align(4096) struct Table{pub entries:[512]u64}
pub struct Space{initialized:bool,pool:*Table,pool_count:usize,pool_physical:u64,metadata:*u8,address_mask:u64,nx_supported:bool,used_total:usize}
pub struct Mapping{pub physical:u64,pub flags:u64}
pub error NotMapped=0x0203_0002;pub error Injected=0x0203_0999;
unsafe extern "sysv64" ("dm_host_query") fn host_query(s:*const Space,v:u64,out:*Mapping)u64;
unsafe extern "sysv64" ("dm_host_map") fn host_map(s:*Space,v:u64,p:u64,flags:u64)u64;
pub unsafe fn query(s:*const Space,v:u64,out:*Mapping)!void{unsafe{
 let code=host_query(s,v,out);if code==0{return;}if code==0x0203_0002{return error.NotMapped;}return error.Injected;
}}
pub unsafe fn map_live(s:*Space,v:u64,p:u64,flags:u64)!void{unsafe{
 if host_map(s,v,p,flags)!=0{return error.Injected;}
}return;}
''',
}


def digest(data): return hashlib.sha256(data).hexdigest()


class DeviceMemoryDiagnosticTests(unittest.TestCase):
    def test_actual_prepare_atomic_conflict_and_native_bad_guard(self):
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'NASM and SysV-capable GCC are mandatory; no skip')
        out = ROOT / 'build/test/device-memory-diag' / ('run-' + uuid.uuid4().hex[:12]); out.mkdir(parents=True)
        sources = [ROOT / 'kernel/boot/device_memory.dg', ROOT / 'kernel/boot/device_policy.dg']
        original = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sources}
        tracked = set(sources) | {Path(__file__), ROOT / 'tests/device_memory_diag_probe.c'}
        for base in (ROOT / 'kernel', ROOT / 'lang/examples', ROOT / 'lang/std'):
            tracked.update(base.rglob('*.dg'))
        tracked.update((ROOT / 'lang/dongc').glob('*.py'))
        before = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in tracked}
        results = []
        for variant in ('normal', 'swallowed-policy-error', 'reject-runtime-apic', 'reject-runtime-ioapic', 'reject-runtime-timers', 'reject-runtime-pm', 'allow-reserved', 'allow-ram'):
            for mode in ('debug', 'release'):
                where = out / variant / mode; where.mkdir(parents=True)
                stage = where / 'source'; (stage / 'boot').mkdir(parents=True)
                # Resolver roots must be unique. Preserve the normal kernel
                # tree in this isolated root, then replace only adapter modules.
                for path in (ROOT / 'kernel').rglob('*.dg'):
                    target = stage / path.relative_to(ROOT / 'kernel')
                    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
                actual = original['kernel/boot/device_memory.dg']
                if variant == 'swallowed-policy-error':
                    pattern = rb'try\s+policy\.plan_diagnostic\(([^;]+)\);'
                    matches = list(re.finditer(pattern, actual))
                    self.assertEqual(1, len(matches), 'one actual shared policy error-propagation guard required')
                    actual = re.sub(pattern, lambda m: b'match policy.plan_diagnostic(' + m[1] + b') {ok=>{},err(code)=>{}}', actual, count=1)
                (stage / 'boot/device_memory.dg').write_bytes(actual + FIXTURE_EXPORTS.encode())
                actual_policy = original['kernel/boot/device_policy.dg']
                guard = b'if kind != 11 {'
                runtime = b'(u64_at(raw.ptr,offset + 32) & 0x8000_0000_0000_0000) != 0'
                mutation = {
                    'reject-runtime-apic': b'if kind != 11 || ' + runtime + b' {',
                    'reject-runtime-ioapic': b'if kind != 11 || (' + runtime + b' && slot != 0) {',
                    'reject-runtime-timers': b'if kind != 11 || (' + runtime + b' && slot > 8) {',
                    'reject-runtime-pm': b'if kind != 11 || (' + runtime + b' && slot > 9) {',
                    'allow-reserved': b'if kind != 11 && kind != 0 {',
                    'allow-ram': b'if kind != 11 && kind != 7 {',
                }.get(variant)
                if mutation is not None:
                    self.assertEqual(1, actual_policy.count(guard))
                    actual_policy = actual_policy.replace(guard, mutation, 1)
                (stage / 'boot/device_policy.dg').write_bytes(actual_policy)
                if variant == 'normal':
                    self.assertEqual(original['kernel/boot/device_memory.dg'], (stage / 'boot/device_memory.dg').read_bytes()[:-len(FIXTURE_EXPORTS.encode())])
                for name, text in STUBS.items():
                    path = stage / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')
                bridge = stage / 'device_memory_diag_probe.dg'; bridge.write_text(BRIDGE, encoding='utf-8')
                compiled = compile_file(bridge, roots=[stage, ROOT / 'lang/examples', ROOT / 'lang/std'], mode=mode)
                # Include every actual transitive source and compiler in stability evidence.
                for name in compiled.sources:
                    path = Path(name).resolve()
                    if path.is_file() and path.is_relative_to(ROOT) and not path.is_relative_to(out):
                        key = path.relative_to(ROOT).as_posix()
                        if key not in before: before[key] = digest(path.read_bytes())
                for path in (ROOT / 'lang/dongc').glob('*.py'):
                    before.setdefault(path.relative_to(ROOT).as_posix(), digest(path.read_bytes()))
                layouts = {t['full_name']: t for t in compiled.layout_manifest['types']}
                self.assertEqual({n: layouts[n]['size'] for n in ('boot.device_policy.Views', 'boot.device_policy.Plan',
                    'boot.device_policy.Conflict', 'boot.preflight.State', 'boot.runtime_view.View', 'firmware.acpi.Inventory', 'mm.paging.Space')},
                    {'boot.device_policy.Views': 88, 'boot.device_policy.Plan': 184, 'boot.device_policy.Conflict': 88,
                     'boot.preflight.State': 48, 'boot.runtime_view.View': 160, 'firmware.acpi.Inventory': 2456, 'mm.paging.Space': 64})
                self.assertEqual(list(range(0, 88, 8)), [f['offset'] for f in layouts['boot.device_policy.Conflict']['fields']])
                (where / 'layout.json').write_text(json.dumps(compiled.layout_manifest, indent=2) + '\n', encoding='utf-8')
                macros = {'INV_BYTES': layouts['firmware.acpi.Inventory']['size']}
                for prefix, typ, fields in (
                    ('INV', 'firmware.acpi.Inventory', ('lapic_address', 'ioapic_count', 'ioapics', 'hpet', 'hpet_gas', 'pm_timer_gas')),
                    ('VIEW', 'boot.runtime_view.View', ('raw_map', 'raw_size', 'descriptor_size', 'root_physical'))):
                    for field in fields: macros[prefix + '_' + field.upper()] = next(f['offset'] for f in layouts[typ]['fields'] if f['name'] == field)
                (where / 'native_layout.h').write_text('\n'.join('#define ' + k + ' ' + str(v) for k, v in macros.items()) + '\n', encoding='utf-8')
                assembly = where / 'probe.asm'; assembly.write_text(compiled.assembly, encoding='utf-8')
                self.assertNotRegex(compiled.assembly.lower(), r'\b(?:invlpg|rdmsr|wrmsr|cr[0348]|ymm[0-9]+)\b')
                native = 'win64' if os.name == 'nt' else 'elf64'; obj = where / 'probe.o'
                for fmt in ('elf64', 'win64'):
                    command([nasm, '-f', fmt, *nasm_flags(nasm), '-o', obj if fmt == native else where / (fmt + '.o'), assembly], where, 'assemble-' + fmt)
                binary = where / ('probe.exe' if os.name == 'nt' else 'probe')
                command([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-D__USE_MINGW_ANSI_STDIO=1',
                    *(['-mno-sse'] if os.name == 'nt' else ['-no-pie']), '-I', where,
                    ROOT / 'tests/device_memory_diag_probe.c', obj, '-o', binary], where, 'link')
                execution = command([binary], where, 'native', success=False)
                if variant == 'normal':
                    self.assertEqual(0, execution.returncode, execution.stdout + execution.stderr)
                    self.assertIn('DEVICE_MEMORY_DIAG_NATIVE_OK', execution.stdout)
                else:
                    self.assertEqual(1, execution.returncode, execution.stdout + execution.stderr)
                    if variant.startswith('reject-runtime-'):
                        expected_slots = {'reject-runtime-apic':'0x001', 'reject-runtime-ioapic':'0x002',
                                          'reject-runtime-timers':'0x200', 'reject-runtime-pm':'0x400'}[variant]
                        self.assertIn('DM_RUNTIME_PLATFORM status=0x03030002 attributes=0x8000000000000000 legacy=0 slots='+expected_slots, execution.stdout)
                        self.assertIn('status==0', execution.stderr)
                    else:
                        self.assertIn('DM_OBS conflict_status=0x00000000', execution.stdout)
                        self.assertIn('status==RAM_CONFLICT', execution.stderr)
                    self.assertIn('DM_NATIVE_ASSERT', execution.stderr)
                    self.assertNotRegex(execution.stderr.lower(), r'panic|segmentation|access violation')
                results.append(dict(variant=variant, mode=mode, actual_dong_prepare_and_policy=True,
                    returncode=execution.returncode, stdout=execution.stdout, stderr=execution.stderr,
                    assembly_sha256=digest(assembly.read_bytes()), source_stage=str(stage), actual_hardware_io=False))
        after = {name: digest((ROOT / name).read_bytes()) for name in before}
        self.assertEqual(before, after, 'actual source/compiler changed during native verification')
        (out / 'validation-summary.json').write_text(json.dumps(dict(passed=True, sources_unchanged=True,
            source_sha256=after, production_modules_verbatim=list(original), stub_boundaries=STUBS,
            fixture_exports=FIXTURE_EXPORTS, actual_hardware_io=False, actual_page_tables=False, results=results), indent=2) + '\n', encoding='utf-8')
        print('DEVICE_MEMORY_DIAG_EVIDENCE', out)


if __name__ == '__main__': unittest.main(verbosity=2)

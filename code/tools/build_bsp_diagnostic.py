"""Build an explicit BSP-user diagnostic from an unchanged USB-only desktop.

This does not change normal build defaults or CPU topology. Only the existing
P6_USER_SMP selector in services_run.o is disabled. The EFI banner identifies
the diagnostic. No physical media or VM is opened by this tool.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'tools/build.py').is_file())
sys.path.insert(0, str(ROOT))
from tools.build import ROOT, find_tool
from tools.build_usb import verify_build
from tools.elf_image import materialize
from tools.make_usb_image import _no_links, _reject_special
from tools.mkimage import manifest_text, pack_image, unpack_image
from tools.service_bundle import ELF, inspect as inspect_bundle

VERSION = 1
PROFILE = 'bsp-user-isolation'
BANNER_BEFORE = b'DongOS USB DIAG R4 S00 EFI entry'
BANNER_AFTER = b'DongOS BSP DIAG R1 USER SMP OFF'
KERNEL_OBJECTS = ('entry.o', 'dong_probe.o', 'abi_probe.o', 'cpu.o', 'panic.o',
    'x86_64.o', 'memory_runtime.o', 'stack_bridge.o', 'power_io.o',
    'memory_mutation.o', 'cpu_hardening.o', 'runtime.o', 'hardware.o',
    'context.o', 'user/context.o', 'services_run.o', 'bootstrap.o',
    'smp_runtime.o', 'large_memory.o', 'alias_memory.o', 'shared_barrier.o',
    'parallel.o', 'parallel_probe.o', 'parallel_live.o', 'user_entry.o',
    'user_arch.o', 'user_bridge_arch.o', 'user_legacy.o', 'user_boot.o',
    'runtime_large_reader.o', 'runtime_exec_reader.o', 'runtime_cache_reader.o',
    'kernel-trace/trace_clock.o')
LOADER_OBJECTS = ('image.obj', 'efi_main.obj', 'service_bundle.obj',
    'display_mode.obj', 'loader-trace/trace_loader.obj',
    'loader-trace/trace_clock.obj', 'loader-trace/trace_loader_panic.obj')
SERVICE_NAMES = frozenset(('block', 'compositor', 'devmgr', 'echo', 'editor',
    'fault', 'files', 'fs', 'fs-reader', 'init', 'input', 'ipc-peer',
    'settings', 'shell', 'terminal', 'waiter', 'xhci'))
ARTIFACT_NAMES = ('services_run.o', 'kernel.elf', 'kernel.bin', 'image.obj',
    'efi_main.obj', 'image.lst', 'efi_main.lst', 'image_manifest.inc', 'private/efi_main.asm',
    'esp/DONGOS.IMG', 'esp/SERVICES.BIN', 'esp/EFI/BOOT/BOOTX64.EFI')


def check(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(path, *, directory=False):
    value = _reject_special(path)
    _no_links(value, directory=directory)
    return value.resolve()


def _new_output(output, normal):
    value = _reject_special(output)
    check(value.is_relative_to(ROOT/'build') and value != ROOT/'build',
          'diagnostic output must be a new directory under this workspace build/')
    check(not value.exists() and not value.is_symlink(), 'diagnostic output already exists')
    check(not value.is_relative_to(normal) and not normal.is_relative_to(value),
          'diagnostic output overlaps the normal build')
    ancestor = value.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    _no_links(ancestor, directory=True)
    return value


def _snapshot(folder):
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.is_dir():
            _no_links(path, directory=True)
        else:
            _no_links(path)
            result[path.relative_to(folder).as_posix()] = sha(path)
    return result


def _normal_checked(normal):
    normal = _ordinary(normal, directory=True)
    check(normal.is_relative_to(ROOT/'build'), 'normal build must be under this workspace build/')
    metadata = json.loads(_ordinary(normal/'build-inputs.json').read_text(encoding='utf-8'))
    required = dict(runtime_level=7, kernel_mode='release', test=False,
                    graphics_case=None, smp_case=None, compiler_job=False,
                    source_unchanged=True)
    check(all(metadata.get(k) == v and type(metadata.get(k)) is type(v)
              for k, v in required.items()), 'completed normal release runtime7 profile required')
    check(metadata.get('usb_only_profile', {}).get('usb_only') is True,
          'explicit normal USB-only authority required')
    sources = metadata.get('source_sha256')
    check(isinstance(sources, dict), 'normal source identities missing')
    required_sources = {'kernel/services_run.asm', 'boot/efi_main.asm',
                        'boot/image.asm', 'kernel/linker.ld'}
    required_sources.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'include').glob('*.inc'))
    check(required_sources <= sources.keys(), 'normal build omitted a required source identity')
    for name in sources:
        check(isinstance(name, str) and not Path(name).is_absolute()
              and (ROOT/name).resolve().is_relative_to(ROOT), 'normal source escaped workspace')
        _ordinary(ROOT/name)
    recorded_artifacts = metadata.get('artifacts')
    check(isinstance(recorded_artifacts, dict), 'normal artifact identities missing')
    artifact_paths = {((Path(name) if Path(name).is_absolute() else normal/name).resolve())
                      for name in recorded_artifacts}
    check({normal/name for name in ('kernel.elf', 'kernel.bin', 'esp/DONGOS.IMG',
          'esp/SERVICES.BIN', 'esp/EFI/BOOT/BOOTX64.EFI')} <= artifact_paths,
          'normal payload identity missing')
    for name in recorded_artifacts:
        path = Path(name) if Path(name).is_absolute() else normal/name
        check(path.resolve().is_relative_to(normal), 'normal artifact escaped build')
        _ordinary(path)
    verify_build(normal/'esp')
    check(materialize((normal/'kernel.elf').read_bytes()) == (normal/'kernel.bin').read_bytes(),
          'normal ELF/raw mismatch')
    check(unpack_image((normal/'esp/DONGOS.IMG').read_bytes(),
                       hashlib.sha256((normal/'esp/DONGOS.IMG').read_bytes()).digest())
          == (normal/'kernel.bin').read_bytes(), 'normal image/raw mismatch')
    bundle = inspect_bundle((normal/'esp/SERVICES.BIN').read_bytes())
    entries = [entry for entry in bundle['entries'] if entry['kind'] == ELF]
    check(len(entries) == 17 and {entry['name'] for entry in entries} == SERVICE_NAMES,
          'all seventeen original services required')
    for entry in entries:
        check(sha(_ordinary(normal/'services'/entry['name']/'program.elf')) == entry['sha256'],
              'normal service ELF differs from bundle: '+entry['name'])
    return normal, metadata, bundle


def argv_from_log(line):
    """Parse data written by subprocess.list2cmdline; never invoke a shell."""
    if os.name != 'nt':
        return shlex.split(line)
    count = ctypes.c_int()
    parse = ctypes.windll.shell32.CommandLineToArgvW
    parse.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int))
    parse.restype = ctypes.POINTER(ctypes.c_wchar_p)
    values = parse(line, ctypes.byref(count))
    check(bool(values), 'cannot decode completed build command')
    try:
        return [values[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes, free.restype = (ctypes.c_void_p,), ctypes.c_void_p
        free(ctypes.cast(values, ctypes.c_void_p))


def _nasm(tool, fmt, includes, output, source, defines, warnings):
    command = [tool, '-f', fmt, '-Wall', '-Werror']
    for directory in includes:
        command += ['-I', str(directory)+os.sep]
    command += ['-l', str(output.with_suffix('.lst')), '-o', str(output)]
    return command+list(warnings)+list(defines)+[str(source)]


def command_plan(normal, log, output):
    """Accept only exact known normal commands, then generate our own recipe."""
    normal, log, output = Path(normal).resolve(), _ordinary(log), Path(output).absolute()
    commands = [argv_from_log(line[2:]) for line in log.read_text(encoding='utf-8').splitlines()
                if line.startswith('+ ')]
    def one(predicate):
        found = [c for c in commands if predicate(c)]
        check(len(found) == 1, 'unique expected normal command required')
        return found[0]
    def emits(c, path):
        return '-o' in c and c[c.index('-o')+1] == str(path)
    tools = {name: str(Path(find_tool(name, variable)).resolve()) for name, variable in
             (('nasm', 'NASM'), ('ld.lld', 'LD_LLD'), ('lld-link', 'LLD_LINK'))}
    services = one(lambda c: emits(c, normal/'services_run.o'))
    warnings = tuple(v for v in services if v in ('-w-reloc-rel-dword', '-w-reloc-abs-qword'))
    check(len(set(warnings)) == len(warnings), 'duplicate normal NASM warning flag')
    normal_nasm = {
        'services_run': _nasm(tools['nasm'], 'elf64', (ROOT/'include', normal), normal/'services_run.o',
                             ROOT/'kernel/services_run.asm', ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=1'), warnings),
        'image': _nasm(tools['nasm'], 'win64', (ROOT/'include', normal), normal/'image.obj',
                      ROOT/'boot/image.asm', (), warnings),
        'efi_main': _nasm(tools['nasm'], 'win64', (ROOT/'include', normal), normal/'efi_main.obj',
                         ROOT/'boot/efi_main.asm', ('-DSERVICE_BUNDLE=1', '-DDESKTOP_MODE=1'), warnings)}
    for name, expected in normal_nasm.items():
        actual = one(lambda c, expected=expected: emits(c, Path(expected[expected.index('-o')+1])))
        check(actual == expected, 'normal NASM recipe differs: '+name)
    kernel = [tools['ld.lld'], '-nostdlib', '--gc-sections', '-z', 'max-page-size=0x1000',
              '-T', str(ROOT/'kernel/linker.ld'), '-o', str(normal/'kernel.elf'),
              *(str(normal/name) for name in KERNEL_OBJECTS)]
    check(one(lambda c: emits(c, normal/'kernel.elf')) == kernel, 'normal kernel object recipe differs')
    loader = [tools['lld-link'], '/subsystem:efi_application', '/machine:x64', '/entry:efi_main',
              '/nodefaultlib', '/timestamp:0', '/fixed:no', '/map:'+str(normal/'efi_main.map'),
              '/out:'+str(normal/'esp/EFI/BOOT/BOOTX64.EFI'),
              *(str(normal/name) for name in LOADER_OBJECTS)]
    check(one(lambda c: '/out:'+str(normal/'esp/EFI/BOOT/BOOTX64.EFI') in c) == loader,
          'normal loader object recipe differs')
    for name in (*KERNEL_OBJECTS, *LOADER_OBJECTS):
        _ordinary(normal/name)
    new_services = _nasm(tools['nasm'], 'elf64', (ROOT/'include', normal), output/'services_run.o',
                         ROOT/'kernel/services_run.asm', ('-DRUNTIME_LEVEL=7', '-DP6_USER_SMP=0'), warnings)
    new_kernel = [*kernel[:kernel.index('-o')+1], str(output/'kernel.elf'),
                  *(str(output/name) if name == 'services_run.o' else str(normal/name) for name in KERNEL_OBJECTS)]
    new_image = _nasm(tools['nasm'], 'win64', (ROOT/'include', output, normal), output/'image.obj',
                      ROOT/'boot/image.asm', (), warnings)
    new_efi = _nasm(tools['nasm'], 'win64', (ROOT/'include', output, normal), output/'efi_main.obj',
                    output/'private/efi_main.asm', ('-DSERVICE_BUNDLE=1', '-DDESKTOP_MODE=1'), warnings)
    new_loader = [*loader[:7], '/map:'+str(output/'efi_main.map'),
                  '/out:'+str(output/'esp/EFI/BOOT/BOOTX64.EFI'),
                  *(str(output/name) if name in ('image.obj', 'efi_main.obj') else str(normal/name)
                    for name in LOADER_OBJECTS)]
    return dict(normal_commands=dict(services_run=normal_nasm['services_run'], kernel=kernel,
                image=normal_nasm['image'], efi_main=normal_nasm['efi_main'], loader=loader),
                commands=dict(services_run=new_services, kernel=new_kernel, image=new_image,
                              efi_main=new_efi, loader=new_loader),
                tool_sha256={value: sha(value) for value in tools.values()})


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def build_diagnostic(normal_source, normal_build_log, output):
    normal, metadata, bundle = _normal_checked(normal_source)
    log = _ordinary(normal_build_log)
    output = _new_output(output, normal)
    plan = command_plan(normal, log, output)
    before = _snapshot(normal)
    source_before = {name: sha(ROOT/name) for name in metadata['source_sha256']}
    output.mkdir(parents=True)
    (output/'esp/EFI/BOOT').mkdir(parents=True)
    (output/'private').mkdir()
    original = (ROOT/'boot/efi_main.asm').read_bytes()
    check(original.count(BANNER_BEFORE) == 1 and BANNER_AFTER not in original, 'one original diagnostic banner required')
    (output/'private/efi_main.asm').write_bytes(original.replace(BANNER_BEFORE, BANNER_AFTER))
    shutil.copyfile(normal/'esp/SERVICES.BIN', output/'esp/SERVICES.BIN')
    for name in SERVICE_NAMES:
        folder = output/'services'/name
        folder.mkdir(parents=True)
        for filename in ('program.elf', 'build.json'):
            if (normal/'services'/name/filename).is_file():
                shutil.copyfile(normal/'services'/name/filename, folder/filename)
    shutil.copyfile(normal/'dong_layout.json', output/'dong_layout.json')
    executed = []
    def execute(label):
        command = plan['commands'][label]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=180,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        record = dict(label=label, command=command, returncode=result.returncode,
                      stdout=result.stdout, stderr=result.stderr)
        executed.append(record)
        _write_json(output/(label+'-command.json'), record)
        check(result.returncode == 0, 'diagnostic '+label+' failed: '+result.stderr[-1600:])
    execute('services_run')
    check(sha(output/'services_run.o') != sha(normal/'services_run.o'), 'BSP selector did not change services_run.o')
    execute('kernel')
    raw = materialize((output/'kernel.elf').read_bytes())
    check(raw != (normal/'kernel.bin').read_bytes(), 'diagnostic kernel must differ from normal')
    (output/'kernel.bin').write_bytes(raw)
    image = pack_image(raw)
    (output/'esp/DONGOS.IMG').write_bytes(image)
    (output/'image_manifest.inc').write_text(manifest_text(image), encoding='utf-8')
    for label in ('image', 'efi_main', 'loader'):
        execute(label)
    check(_snapshot(normal) == before and all(sha(ROOT/name) == digest for name, digest in source_before.items()),
          'normal input changed during diagnostic build')
    artifacts = {name: sha(output/name) for name in ARTIFACT_NAMES}
    artifacts['dong_layout.json'] = sha(output/'dong_layout.json')
    for path in (output/'services').rglob('*'):
        if path.is_file():
            artifacts[path.relative_to(output).as_posix()] = sha(path)
    result = dict(version=VERSION, profile=PROFILE, diagnostic_only=True,
        ordinary_normal_build=False, user_smp=False, platform_cpu_topology_unchanged=True,
        no_memory_map_or_fault_injection=True, normal_source=str(normal),
        normal_build_log=str(log), normal_build_log_sha256=sha(log),
        normal_manifest_sha256=sha(normal/'build-inputs.json'),
        normal_inputs_sha256=before, source_sha256=source_before,
        builder_sha256=sha(__file__), recipe=plan, executed=executed,
        only_replaced_kernel_object='services_run.o',
        banner_before=BANNER_BEFORE.decode(), banner_after=BANNER_AFTER.decode(),
        original_services_bundle=bundle, artifacts=artifacts)
    _write_json(output/'bsp-diagnostic.json', result)
    verify_diagnostic(output/'esp')
    return output/'esp'


def verify_diagnostic(esp):
    esp = _ordinary(esp, directory=True)
    output = esp.parent
    check(esp.name == 'esp' and output.is_relative_to(ROOT/'build'), 'diagnostic ESP path differs')
    check(not (output/'build-inputs.json').exists(), 'diagnostic must not masquerade as a normal build')
    result = json.loads(_ordinary(output/'bsp-diagnostic.json').read_text(encoding='utf-8'))
    expected = dict(version=VERSION, profile=PROFILE, diagnostic_only=True,
        ordinary_normal_build=False, user_smp=False, platform_cpu_topology_unchanged=True,
        no_memory_map_or_fault_injection=True, only_replaced_kernel_object='services_run.o',
        banner_before=BANNER_BEFORE.decode(), banner_after=BANNER_AFTER.decode())
    check(all(result.get(k) == v and type(result.get(k)) is type(v) for k, v in expected.items()),
          'explicit BSP diagnostic profile differs')
    check(result.get('builder_sha256') == sha(__file__), 'diagnostic builder changed')
    normal, metadata, bundle = _normal_checked(result['normal_source'])
    log = _ordinary(result['normal_build_log'])
    check(sha(log) == result['normal_build_log_sha256'] and sha(normal/'build-inputs.json') == result['normal_manifest_sha256'],
          'normal manifest/log identity changed')
    check(_snapshot(normal) == result['normal_inputs_sha256'], 'normal build inputs changed')
    check({name: sha(ROOT/name) for name in metadata['source_sha256']} == result['source_sha256'],
          'normal production sources changed')
    plan = command_plan(normal, log, output)
    check(plan == result['recipe'], 'diagnostic recipe differs')
    check([r['label'] for r in result['executed']] == ['services_run', 'kernel', 'image', 'efi_main', 'loader'],
          'diagnostic execution sequence differs')
    check(all(record['returncode'] == 0 and record['command'] == plan['commands'][record['label']]
              for record in result['executed']), 'diagnostic execution recipe failed or changed')
    check(set(ARTIFACT_NAMES) <= result['artifacts'].keys(), 'diagnostic artifact identity missing')
    for name, digest in result['artifacts'].items():
        check(not Path(name).is_absolute() and (output/name).resolve().is_relative_to(output), 'diagnostic artifact escaped output')
        check(sha(_ordinary(output/name)) == digest, 'diagnostic artifact changed: '+name)
    original = (ROOT/'boot/efi_main.asm').read_bytes()
    check(original.count(BANNER_BEFORE) == 1 and (output/'private/efi_main.asm').read_bytes()
          == original.replace(BANNER_BEFORE, BANNER_AFTER), 'private EFI changed beyond banner')
    check(bundle == result['original_services_bundle'] and (esp/'SERVICES.BIN').read_bytes() == (normal/'esp/SERVICES.BIN').read_bytes(),
          'original services bundle changed')
    for name in SERVICE_NAMES:
        check((output/'services'/name/'program.elf').read_bytes() == (normal/'services'/name/'program.elf').read_bytes(),
              'original service ELF changed: '+name)
    check((output/'dong_layout.json').read_bytes() == (normal/'dong_layout.json').read_bytes(), 'original Dong layouts changed')
    raw = materialize((output/'kernel.elf').read_bytes())
    image = (esp/'DONGOS.IMG').read_bytes()
    check(raw == (output/'kernel.bin').read_bytes() and raw != (normal/'kernel.bin').read_bytes(), 'diagnostic ELF/raw identity differs')
    check(unpack_image(image, hashlib.sha256(image).digest()) == raw
          and (output/'image_manifest.inc').read_text(encoding='utf-8') == manifest_text(image), 'diagnostic image/manifest binding differs')
    digest = hashlib.sha256(image).digest()
    # image.asm embeds the complete digest. efi_main.asm consumes the sizes and
    # entry offset, but does not emit the unused digest macro as object data.
    check(digest in (output/'image.obj').read_bytes()
          and digest in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(), 'EFI verifier must bind the diagnostic image digest')
    definitions = [line for line in manifest_text(image).splitlines() if line.startswith('%define ')]
    for name in ('image.lst', 'efi_main.lst'):
        listing = (output/name).read_text(encoding='utf-8')
        check(all(len(re.findall(r'(?m)^\s*\d+\s+<1> '+re.escape(line)+r'\s*$', listing)) == 1
                  for line in definitions), 'both actual NASM listings must consume the diagnostic manifest: '+name)
    check(BANNER_AFTER+b'\r\n\0' in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes()
          and BANNER_BEFORE+b'\r\n\0' not in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(), 'diagnostic EFI banner missing')
    check(sha(output/'services_run.o') != sha(normal/'services_run.o'), 'BSP object equals normal SMP selector')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal-source', type=Path, required=True)
    parser.add_argument('--normal-build-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    esp = build_diagnostic(args.normal_source, args.normal_build_log, args.output)
    print('BSP_USER_DIAGNOSTIC_BUILD_PASS', esp, flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit('BSP diagnostic: '+str(error))

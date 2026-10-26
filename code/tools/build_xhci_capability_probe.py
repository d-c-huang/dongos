"""Build an explicit read-only xHCI first-page capability stop.

The private kernel overlay gains only a guarded, supervisor RO/UC/NX reader.
No register or PCI writes, controller takeover, DMA, ownership or user entry
are performed by this diagnostic. Normal build policy and inputs are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'tools/build.py').is_file())
sys.path.insert(0, str(ROOT))
from tools.build import ROOT
from tools import build_bsp_diagnostic as prior
from tools import build_usb_preflight as inventory
from tools.elf_image import materialize
from tools.mkimage import manifest_text, pack_image, unpack_image

VERSION = 1
PROFILE = 'xhci-capability-probe'
STAGE = 24
REPORT_SIZE = 256
FIELDS = ('version', 'done', 'error_code', 'flags', 'bar_physical', 'pci_command',
    'cap0', 'hcs1', 'hcs2', 'hcc1', 'db_off', 'rt_off', 'hcc2', 'operational',
    'pagesize', 'usbcmd', 'usbsts', 'extended_first', 'extended_count',
    'legacy_offset', 'legacy_support', 'legacy_control', 'protocols2',
    'protocols3', 'unsupported_first', 'scratchpads', 'context_bytes', 'ac64',
    'reject_mask', 'inventory_error', 'read_count', 'reserved')
ROWS = (('READ ERROR', 'error_code'), ('BAR PHYS', 'bar_physical'),
    ('PCI COMMAND', 'pci_command'), ('CAP0', 'cap0'), ('HCSPARAM1', 'hcs1'),
    ('HCSPARAM2', 'hcs2'), ('HCCPARAM1', 'hcc1'), ('PAGESIZE', 'pagesize'),
    ('USBSTS', 'usbsts'), ('XECP FIRST', 'extended_first'),
    ('LEGACY SUP', 'legacy_support'), ('LEGACY CTL', 'legacy_control'),
    ('OTHER CAP', 'unsupported_first'), ('REJECT MASK', 'reject_mask'),
    ('FLAGS', 'flags'))
TITLE = 'DONGOS XHCI CAPS'
BANNER = b'DongOS XHCI CAPS R1'
COMPLETION_MARKER = 'DONGOS_XHCI_CAPS_DONE'
MODULE = 'boot.xhci_capability_probe'
MODULE_PATH = 'boot/xhci_capability_probe.dg'
RUN_EXPORT = 'dong_xhci_caps_run'
POINTER_EXPORT = 'dong_xhci_caps_pointer'
REPLACED_OBJECTS = inventory.REPLACED_OBJECTS
COMMAND_ORDER = inventory.COMMAND_ORDER
RECEIPT = 'xhci-capability-probe.json'
check, sha = prior.check, prior.sha

# This exact body is also compiled by the native guard/map/load oracle. It is
# appended solely to the private overlay; the production module is not edited.
APPEND_SOURCE = '''
// XHCI_CAPABILITY_PRIVATE_READER_BEGIN: no hardware writes or user authority.
var USB_CAPABILITY_PAGE:u64=0;
pub unsafe fn usb_capability_read32(physical:u64,offset:u64)!u32 {unsafe{
 if (physical&4095)!=0||offset>4092||(offset&3)!=0{return error.Invalid;}
 try mmio_range(physical,4096,false);
 if USB_CAPABILITY_PAGE!=physical||CURRENT_PAGE!=physical{
  if CURRENT_PAGE==0{
   try paging.map_live(startup.space_pointer(),WINDOW,physical,paging.UNCACHED);
  }else{
   try paging.replace_live(startup.space_pointer(),WINDOW,physical,paging.UNCACHED);
  }
  devices.runtime_invalidate(WINDOW);
  CURRENT_PAGE=physical;USB_CAPABILITY_PAGE=physical;
 }
 return volatile_load((WINDOW+offset) as *const u32);
}}
// XHCI_CAPABILITY_PRIVATE_READER_END
'''


def patch_entry(text):
    """Reuse the established outer Gate/geometry and substitute only payload."""
    result = inventory.patch_entry(text)
    check(result.count(inventory.POINTER_EXPORT) == 2, 'two fixed getter references required')
    result = result.replace(inventory.POINTER_EXPORT, POINTER_EXPORT)
    for index, ((old_label, old_field), (label, field)) in enumerate(zip(inventory.ROWS, ROWS)):
        old_value = '[rel boot_progress_cpus]' if old_field == 'boot_progress_cpus' else '[rbx + '+str(inventory.FIELDS.index(old_field)*8)+']'
        new_value = '[rbx + '+str(FIELDS.index(field)*8)+']'
        before = '    BOOT_USB_PREFLIGHT_LINE usb_preflight_label_'+str(index)+','+str(120+index*24)+','+old_value
        after = '    BOOT_USB_PREFLIGHT_LINE usb_preflight_label_'+str(index)+','+str(120+index*24)+','+new_value
        result = inventory._replace(result, before+'\n', after+'\n')
        result = inventory._replace(result, 'usb_preflight_label_'+str(index)+': db "'+old_label+'",0\n',
                                     'usb_preflight_label_'+str(index)+': db "'+label+'",0\n')
    result = inventory._replace(result, 'usb_preflight_title: db "'+inventory.TITLE+'",0\n',
                                 'usb_preflight_title: db "'+TITLE+'",0\n')
    return result.replace('usb_preflight_', 'xhci_capability_').replace('BOOT_USB_PREFLIGHT_LINE',
        'BOOT_XHCI_CAPS_LINE').replace('USB_PREFLIGHT_RENDER_', 'XHCI_CAPS_RENDER_')


def patch_services_run(text):
    result = inventory.patch_services_run(text)
    check(result.count(inventory.RUN_EXPORT) == 2, 'two private run references required')
    result = result.replace(inventory.RUN_EXPORT, RUN_EXPORT)
    check(result.count(inventory.COMPLETION_MARKER) == 1, 'one private stop marker required')
    return result.replace(inventory.COMPLETION_MARKER, COMPLETION_MARKER).replace(
        'usb_preflight_', 'xhci_capability_').replace('USB_PREFLIGHT_STOP_', 'XHCI_CAPS_STOP_')


def patch_probe(raw):
    imported = b'import boot.xhci_capability_probe;'
    check(imported not in raw, 'normal graph already imports the capability probe')
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    return raw+(b'' if raw.endswith(b'\n') else newline)+imported+newline


def append_devices(raw):
    check(b'USB_CAPABILITY_PAGE' not in raw and b'usb_capability_read32' not in raw,
          'normal device module already contains the private capability reader')
    return raw+APPEND_SOURCE.encode('utf-8')


def command_plan(normal, log, output):
    # The inventory builder already checks the exact original compiler, three
    # object assemblies and both EFI manifest consumers before generating argv.
    return inventory.command_plan(normal, log, output)


def _private_sources(output):
    for original, filename, patch in (('kernel/entry.asm', 'entry.asm', patch_entry),
                                    ('kernel/services_run.asm', 'services_run.asm', patch_services_run)):
        (output/'private'/filename).write_bytes(patch((ROOT/original).read_bytes().decode('utf-8')).encode('utf-8'))
    source = (ROOT/'boot/efi_main.asm').read_bytes()
    check(source.count(prior.BANNER_BEFORE) == 1 and BANNER not in source, 'one original EFI banner required')
    (output/'private/efi_main.asm').write_bytes(source.replace(prior.BANNER_BEFORE, BANNER))


def _sources(metadata):
    result = {name: sha(ROOT/name) for name in metadata['source_sha256']}
    for name in ('kernel/'+inventory.MODULE_PATH, 'kernel/'+MODULE_PATH,
                 'tools/build_bsp_diagnostic.py', 'tools/build_usb_preflight.py'):
        result[name] = sha(prior._ordinary(ROOT/name))
    return result


def _verify_overlay(normal, output):
    expected = prior._snapshot(normal/'kernel-profile-src')
    check(inventory.MODULE_PATH not in expected and MODULE_PATH not in expected,
          'normal graph already contains diagnostic modules')
    expected[inventory.MODULE_PATH] = sha(ROOT/'kernel'/inventory.MODULE_PATH)
    expected[MODULE_PATH] = sha(ROOT/'kernel'/MODULE_PATH)
    expected['smp_probe.dg'] = hashlib.sha256(patch_probe((normal/'kernel-profile-src/smp_probe.dg').read_bytes())).hexdigest()
    expected['user/devices.dg'] = hashlib.sha256(append_devices((normal/'kernel-profile-src/user/devices.dg').read_bytes())).hexdigest()
    actual = prior._snapshot(output/'kernel-profile-src')
    check(actual == expected, 'private overlay differs beyond two modules/import/guarded reader append')
    return actual


def _verify_report_layout(output):
    layout = json.loads((output/'dong_layout.json').read_text(encoding='utf-8'))
    reports = [t for t in layout['types'] if t['full_name'] == MODULE+'.Report']
    check(len(reports) == 1, 'one actual xHCI capability Report layout required')
    report = reports[0]
    check(report['size'] == REPORT_SIZE and report['alignment'] == 8
          and [(f['name'], f['offset'], f['size']) for f in report['fields']]
          == [(name, index*8, 8) for index,name in enumerate(FIELDS)], 'actual capability Report layout differs')
    inventory._verify_report_layout(output)
    return report


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def _expected_profile():
    return dict(version=VERSION, profile=PROFILE, intentional_stop=True,
        ordinary_normal_build=False, read_only_first_page=True, no_register_writes=True,
        no_cpl3_entry=True, no_device_ownership_or_dma=True, platform_cpu_topology_unchanged=True,
        stage=STAGE, fields=list(FIELDS), rows=[list(row) for row in ROWS], title=TITLE,
        banner=BANNER.decode(), completion_marker=COMPLETION_MARKER,
        replaced_kernel_objects=list(REPLACED_OBJECTS), append_source_sha256=hashlib.sha256(APPEND_SOURCE.encode()).hexdigest())


def build_probe(normal_source, normal_build_log, output):
    normal, metadata, bundle = prior._normal_checked(normal_source)
    log = prior._ordinary(normal_build_log)
    output = prior._new_output(output, normal)
    source_before = _sources(metadata)
    before = prior._snapshot(normal)
    plan = command_plan(normal, log, output)
    output.mkdir(parents=True)
    (output/'private').mkdir()
    (output/'esp/EFI/BOOT').mkdir(parents=True)
    shutil.copytree(normal/'kernel-profile-src', output/'kernel-profile-src')
    for path in (inventory.MODULE_PATH, MODULE_PATH):
        shutil.copyfile(ROOT/'kernel'/path, output/'kernel-profile-src'/path)
    probe = output/'kernel-profile-src/smp_probe.dg'
    probe.write_bytes(patch_probe(probe.read_bytes()))
    devices = output/'kernel-profile-src/user/devices.dg'
    devices.write_bytes(append_devices(devices.read_bytes()))
    overlay = _verify_overlay(normal, output)
    _private_sources(output)
    shutil.copyfile(normal/'esp/SERVICES.BIN', output/'esp/SERVICES.BIN')
    for name in prior.SERVICE_NAMES:
        folder = output/'services'/name
        folder.mkdir(parents=True)
        shutil.copyfile(normal/'services'/name/'program.elf', folder/'program.elf')
    executed = []
    def execute(label):
        command = plan['commands'][label]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=240, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        record = dict(label=label, command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        executed.append(record)
        _write_json(output/(label+'-command.json'), record)
        check(result.returncode == 0, 'xHCI capability '+label+' failed: '+result.stderr[-1800:])
    for label in COMMAND_ORDER[:5]:
        execute(label)
    report = _verify_report_layout(output)
    raw = materialize((output/'kernel.elf').read_bytes())
    check(raw != (normal/'kernel.bin').read_bytes(), 'capability probe kernel must differ from normal')
    (output/'kernel.bin').write_bytes(raw)
    image = pack_image(raw)
    (output/'esp/DONGOS.IMG').write_bytes(image)
    (output/'image_manifest.inc').write_text(manifest_text(image), encoding='utf-8')
    for label in COMMAND_ORDER[5:]:
        execute(label)
    check(prior._snapshot(normal) == before and _sources(metadata) == source_before,
          'normal or diagnostic sources changed during build')
    receipt = dict(_expected_profile(), normal_source=str(normal), normal_build_log=str(log),
        normal_build_log_sha256=sha(log), normal_manifest_sha256=sha(normal/'build-inputs.json'),
        normal_inputs_sha256=before, source_sha256=source_before, builder_sha256=sha(__file__),
        recipe=plan, executed=executed, kernel_overlay_sha256=overlay, report_layout=report,
        original_services_bundle=bundle, artifacts=prior._snapshot(output))
    _write_json(output/RECEIPT, receipt)
    verify_probe(output/'esp')
    return output/'esp'


def verify_probe(esp):
    esp = prior._ordinary(esp, directory=True)
    output = esp.parent
    check(esp.name == 'esp' and output.is_relative_to(ROOT/'build'), 'capability probe ESP path differs')
    check(not (output/'build-inputs.json').exists(), 'intentional stop must not masquerade as normal build')
    receipt = json.loads(prior._ordinary(output/RECEIPT).read_text(encoding='utf-8'))
    check(all(receipt.get(k) == value and type(receipt.get(k)) is type(value)
              for k,value in _expected_profile().items()), 'capability probe profile/reader body differs')
    check(receipt['builder_sha256'] == sha(__file__), 'capability probe builder changed')
    normal, metadata, bundle = prior._normal_checked(receipt['normal_source'])
    log = prior._ordinary(receipt['normal_build_log'])
    check(sha(log) == receipt['normal_build_log_sha256'] and sha(normal/'build-inputs.json') == receipt['normal_manifest_sha256'],
          'original normal log/manifest identity changed')
    check(prior._snapshot(normal) == receipt['normal_inputs_sha256'], 'original normal tree changed')
    check(_sources(metadata) == receipt['source_sha256'], 'production/diagnostic/helper sources changed')
    check(command_plan(normal, log, output) == receipt['recipe'], 'capability probe command recipe changed')
    check([r['label'] for r in receipt['executed']] == list(COMMAND_ORDER)
          and all(r['returncode'] == 0 and r['command'] == receipt['recipe']['commands'][r['label']]
                  for r in receipt['executed']), 'capability probe execution sequence/command differs')
    check(_verify_overlay(normal, output) == receipt['kernel_overlay_sha256'], 'capability probe overlay identities changed')
    for original,target,patch in (('kernel/entry.asm','entry.asm',patch_entry),('kernel/services_run.asm','services_run.asm',patch_services_run)):
        check((output/'private'/target).read_bytes() == patch((ROOT/original).read_bytes().decode('utf-8')).encode('utf-8'),
              'private source patch differs: '+target)
    original = (ROOT/'boot/efi_main.asm').read_bytes()
    check(original.count(prior.BANNER_BEFORE) == 1 and (output/'private/efi_main.asm').read_bytes()
          == original.replace(prior.BANNER_BEFORE, BANNER), 'private firmware differs beyond banner')
    check(_verify_report_layout(output) == receipt['report_layout'], 'capability Report compiler layout changed')
    check(bundle == receipt['original_services_bundle'] and (esp/'SERVICES.BIN').read_bytes() == (normal/'esp/SERVICES.BIN').read_bytes(),
          'original services bundle changed')
    for name in prior.SERVICE_NAMES:
        check((output/'services'/name/'program.elf').read_bytes() == (normal/'services'/name/'program.elf').read_bytes(),
              'original service ELF changed: '+name)
    actual = prior._snapshot(output)
    actual.pop(RECEIPT, None)
    check(actual == receipt['artifacts'], 'capability probe artifact inventory/hash changed')
    raw = materialize((output/'kernel.elf').read_bytes())
    image = (esp/'DONGOS.IMG').read_bytes()
    check(raw == (output/'kernel.bin').read_bytes() and raw != (normal/'kernel.bin').read_bytes()
          and unpack_image(image, hashlib.sha256(image).digest()) == raw
          and (output/'image_manifest.inc').read_text(encoding='utf-8') == manifest_text(image),
          'capability probe kernel/image/manifest binding differs')
    digest = hashlib.sha256(image).digest()
    check(digest in (output/'image.obj').read_bytes() and digest in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(),
          'EFI verifier lost the capability probe image digest')
    definitions = [line for line in manifest_text(image).splitlines() if line.startswith('%define ')]
    for name in ('image.lst','efi_main.lst'):
        listing = (output/name).read_text(encoding='utf-8')
        check(all(len(re.findall(r'(?m)^\s*\d+\s+<1> '+re.escape(line)+r'\s*$',listing)) == 1 for line in definitions),
              'both actual EFI manifest consumers must bind this image: '+name)
    check(BANNER+b'\r\n\0' in (esp/'EFI/BOOT/BOOTX64.EFI').read_bytes(), 'capability probe banner missing')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal-source',type=Path,required=True)
    parser.add_argument('--normal-build-log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    esp = build_probe(args.normal_source,args.normal_build_log,args.output)
    print('XHCI_CAPABILITY_PROBE_BUILD_PASS',esp,flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise SystemExit('xHCI capability probe: '+str(error))

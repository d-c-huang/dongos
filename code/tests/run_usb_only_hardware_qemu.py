#!/usr/bin/env python3
"""Single MBR USB boots EFI and owns FAT with writable internal sentinel disks.

Only the coordinator runs guests. --selftest performs host controls only. Every
image is a new ordinary file; no physical disk, mount or passthrough is used.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import run_usb_runtime_qemu as usb
from tests import fat_paths_oracle as oracle
from tools import make_usb_image, usb_only_profile
from tools.build_usb import verify_build
from tools.make_fat32_disk import create as create_sentinel

ROOT, check, settings, storage, gui = usb.ROOT, usb.check, usb.settings, usb.storage, usb.gui
DIRECTORY = usb.DIRECTORY
DOCUMENT, REMOVED, FIRST, TAIL, PAYLOAD = usb.DOCUMENT, usb.REMOVED, usb.FIRST, usb.TAIL, usb.PAYLOAD
SENTINELS = ('nvmeguard', 'sataguard', 'virtioguard')


def verify_profile(esp):
    """Reject the default build and recheck the entire immutable USB snapshot."""
    esp = Path(esp).resolve()
    verify_build(esp)
    manifest = json.loads((esp.parent / 'build-inputs.json').read_text(encoding='utf-8'))
    check(manifest.get('runtime_level') == 7 and manifest.get('test') is False
          and manifest.get('compiler_job') is False, 'normal runtime7 hardware build required')
    usb_only_profile.verify(esp.parent, manifest.get('usb_only_profile'))
    return manifest, esp.parent / usb_only_profile.DIRECTORY


def checked_layouts(esp):
    """Recompile every completed service from its verified USB snapshot."""
    from lang.dongc import compile_file
    _, source = verify_profile(esp)
    layouts, identity = {}, []
    images = sorted((esp.parent / 'services').iterdir())
    check(images and all(p.is_dir() for p in images), 'completed service directories required')
    for folder in images:
        metadata = json.loads((folder / 'build.json').read_text(encoding='utf-8'))
        path = Path(metadata['source']).resolve()
        check(path.is_relative_to(source.resolve()) and path.is_file()
              and metadata.get('mode') == 'release'
              and Path(metadata['elf']).resolve() == (folder / 'program.elf').resolve()
              and metadata.get('byte_length') == (folder / 'program.elf').stat().st_size,
              'completed service was not built from USB snapshot: ' + folder.name)
        compiled = compile_file(path, roots=[source, ROOT / 'lang/std'], mode='release')
        assembly = folder / 'program.asm'
        check(compiled.assembly == assembly.read_text(encoding='utf-8'),
              'USB snapshot differs from completed actual assembly: ' + folder.name)
        for item in compiled.layout_manifest['types']:
            name = item['full_name']
            check(name not in layouts or layouts[name] == item, 'USB shared ABI differs: ' + name)
            layouts[name] = item
        identity.append(dict(image=folder.name, source=str(path.relative_to(source)),
                             assembly_sha256=settings.sha(assembly), elf_sha256=settings.sha(folder / 'program.elf')))
    check({'block', 'compositor', 'fs', 'input', 'xhci', 'editor', 'terminal', 'files', 'settings'}
          <= {p.name for p in images}, 'essential hardware/desktop services missing')
    for item in json.loads((esp.parent / 'dong_layout.json').read_text(encoding='utf-8'))['types']:
        name = item['full_name']
        check(name not in layouts or layouts[name] == item, 'kernel/USB service ABI differs: ' + name)
        layouts[name] = item
    result = gui.Layouts(layouts.values())
    check(result.size('usb.enumerate.State') == 223 * 8 and result.size('usb.bot.State') <= 64 * 8
          and result.size('drivers.usb_partition.View') == 24, 'USB enumeration/BOT/partition ABI differs')
    seen = result.field('fs.fat32.Scratch', 'seen')
    check(seen['size'] == 2097152, 'USB FAT audit bitmap was not compiled into actual FS')
    return result, identity


def checked_kernel_memory_layout(esp):
    """Keep the original runtime-view checks, using the USB service root."""
    from lang.dongc import compile_file
    source = esp.parent / usb_only_profile.DIRECTORY
    path = esp.parent / 'dong_layout.json'
    completed = {t['full_name']: t for t in json.loads(path.read_text(encoding='utf-8'))['types']}
    compiled = compile_file(ROOT / 'kernel/boot/memory_startup.dg',
                            roots=[ROOT / 'lang/examples', ROOT / 'kernel', source, ROOT / 'lang/std'], mode='debug')
    current = {t['full_name']: t for t in compiled.layout_manifest['types']}
    for name in ('boot.memory_startup.Workspace', 'boot.runtime_view.View'):
        check(current[name] == completed[name], 'kernel runtime-view differs from completed USB build')
    workspace, view = current['boot.memory_startup.Workspace'], current['boot.runtime_view.View']
    fields = {f['name']: f['offset'] for f in view['fields']}
    runtime = next(f for f in workspace['fields'] if f['name'] == 'runtime')
    check(runtime['size'] == view['size'] == 160
          and all(fields.get(n) == o for n, o in dict(pool=96, pool_physical=104,
                                                     pool_pages=112, root_physical=152).items()), 'kernel View ABI changed')
    return dict(layout_file_sha256=settings.sha(path), workspace_size=workspace['size'],
                runtime_offset=runtime['offset'], view_size=160, view_fields=fields)


def ordinary(path, *, exists=True):
    path = make_usb_image._reject_special(path)
    make_usb_image._no_links(path if exists else path.parent, directory=not exists)
    return path


def read_partition(image):
    """Independent strict MBR and BPB reader; never opens a physical device."""
    image = ordinary(image)
    size = image.stat().st_size
    check(size % 512 == 0 and size // 512 <= 0xffffffff, 'incomplete/big raw USB image')
    with image.open('rb') as stream:
        mbr = stream.read(512)
        check(len(mbr) == 512 and mbr[:440] == bytes(440) and mbr[444:446] == b'\0\0'
              and mbr[510:] == b'\x55\xaa', 'unexpected USB MBR boot code/reserved/signature')
        entries = [mbr[446 + i * 16:462 + i * 16] for i in range(4)]
        check(entries[0][0] == 0x80 and entries[0][4] == 0x0c
              and all(value == bytes(16) for value in entries[1:]), 'one unique active FAT32 LBA partition required')
        base, capacity = struct.unpack_from('<II', entries[0], 8)
        check(base == 2048 and capacity >= 65536 and base < size // 512
              and capacity <= size // 512 - base, 'USB partition escaped raw medium')
        stream.seek(base * 512)
        volume = stream.read(capacity * 512)
    check(len(volume) == capacity * 512 and volume[510:512] == b'\x55\xaa'
          and struct.unpack_from('<H', volume, 11)[0] == 512
          and struct.unpack_from('<I', volume, 28)[0] == base
          and struct.unpack_from('<I', volume, 32)[0] == capacity,
          'MBR and FAT32 logical geometry differ')
    backup = struct.unpack_from('<H', volume, 50)[0]
    check(0 < backup < struct.unpack_from('<H', volume, 14)[0]
          and volume[backup * 512:(backup + 1) * 512] == volume[:512], 'FAT backup VBR differs')
    return dict(base=base, capacity=capacity, disk_capacity=size // 512,
                mbr_sha256=hashlib.sha256(mbr).hexdigest(), image_bytes=size), volume


def make_single_media(esp, image, size_mib):
    """Extract verified ordinary GPT ESP into a new, unambiguous MBR file."""
    check(size_mib in (128, 256), 'single media fixture must be 128/256 MiB')
    image = ordinary(image, exists=False)
    check(not image.exists() and image.suffix == '.img', 'new ordinary .img required')
    intermediate = image.with_name(image.stem + '-source-gpt.img')
    created = make_usb_image.create(esp, intermediate, size_mib)
    base, count = created['esp']['first_lba'], created['esp']['sectors']
    check(base == 2048, 'unexpected source ESP offset')
    mbr = bytearray(512)
    struct.pack_into('<I', mbr, 440, 0x554f4e4c)
    mbr[446:462] = bytes((0x80, 0xfe, 0xff, 0xff, 0x0c, 0xfe, 0xff, 0xff)) + struct.pack('<II', base, count)
    mbr[510:] = b'\x55\xaa'
    with intermediate.open('rb') as source, image.open('xb') as target:
        target.truncate(size_mib * 1024 * 1024)
        target.write(mbr)
        source.seek(base * 512); target.seek(base * 512)
        remaining = count * 512
        while remaining:
            data = source.read(min(1024 * 1024, remaining))
            check(data, 'incomplete source ESP')
            target.write(data); remaining -= len(data)
        source.seek(base * 512); vbr = bytearray(source.read(512))
        struct.pack_into('<I', vbr, 28, base)
        backup = struct.unpack_from('<H', vbr, 50)[0]
        for sector in (base, base + backup):
            target.seek(sector * 512); target.write(vbr)
        target.flush(); os.fsync(target.fileno())
    geometry, volume = read_partition(image)
    tree = oracle.FatTree(volume)
    expected = {'/' + n: item for n, item in created['source_files'].items()}
    actual = {n: dict(length=len(data), sha256=hashlib.sha256(data).hexdigest()) for n, data in tree.contents.items()}
    check(actual == expected, 'single USB did not preserve every EFI/kernel/service payload')
    result = dict(geometry=geometry, boot_files=expected,
                  boot_directories=[n for n, e in tree.entries.items() if e['attributes'] & 16],
                  original_gpt_image_sha256=created['image_sha256'], initial_image_sha256=settings.sha(image),
                  one_usb_for_efi_and_data=True, no_gpt_or_other_partition=True)
    storage.write_json(image.with_suffix('.json'), result)
    return result


def disk_evidence(image, initial, *, written):
    geometry, volume = read_partition(image)
    check(geometry == initial['geometry'], 'USB MBR/partition geometry changed')
    tree = oracle.FatTree(volume)
    expected = dict(initial['boot_files'])
    directories = set(initial['boot_directories'])
    if written:
        expected[DOCUMENT] = dict(length=len(PAYLOAD), sha256=hashlib.sha256(PAYLOAD).hexdigest())
        directories.add(DIRECTORY)
    for name in ('/DESK0.CFG', '/DESK1.CFG'):
        if name in tree.entries:
            expected[name] = dict(length=0, sha256=hashlib.sha256(b'').hexdigest())
    if '/Documents' in tree.entries:
        directories.add('/Documents')
    actual = {n: dict(length=len(data), sha256=hashlib.sha256(data).hexdigest()) for n, data in tree.contents.items()}
    check(actual == expected and set(tree.entries) == set(expected) | directories
          and REMOVED not in tree.entries, 'actual complete single-media FAT namespace/payload differs')
    if written:
        check(len(tree.entries[DOCUMENT]['clusters']) > 1, 'guest document did not span data clusters')
    return dict(**tree.report(), image=str(image), image_sha256=settings.sha(image), geometry=geometry,
                boot_payloads_preserved=True, complete_namespace_verified=True, guest_payload_verified=written)


def single_media_command(base, image, sentinels):
    """Accept only builder's unmodified base, then add real writable internals."""
    command = list(base)
    check(command.count('-machine') == 1 and command[command.index('-machine') + 1] == 'q35',
          'one unmodified q35 machine required')
    debug = 'isa-debug-exit,iobase=0xf4,iosize=0x04'
    check([v for i, v in enumerate(command) if i and command[i - 1] == '-device'] == [debug]
          and not any(v in command for v in ('-blockdev', '-hda', '-hdb', '-hdc', '-hdd',
                                             '-cdrom', '-sd', '-snapshot', '-readconfig')),
          'unexpected device/storage/passthrough must not be removed')
    efi = [i for i, v in enumerate(command) if i and command[i - 1] == '-drive'
           and v.startswith('format=raw,file=fat:rw:')]
    ordinary_drives = [v for i, v in enumerate(command) if i and command[i - 1] == '-drive'
                       and not v.startswith('if=pflash,')]
    check(len(efi) == len(ordinary_drives) == 1, 'one exact original EFI volume required')
    check(set(sentinels) == set(SENTINELS), 'all three mixed internal sentinel disks required')
    paths = [ordinary(image), *(ordinary(sentinels[n]) for n in SENTINELS)]
    check(len(set(paths)) == 4, 'USB and internal sentinel media must be distinct')
    del command[efi[0] - 1:efi[0] + 1]
    check(command.count(debug) == 1 and command[command.index(debug) - 1] == '-device', 'base test debug exit required')
    index = command.index(debug); del command[index - 1:index + 1]
    command[command.index('-machine') + 1] = 'q35,sata=on,i8042=off'
    def path(p): return Path(p).resolve().as_posix().replace(',', ',,')
    command += ['-device', 'qemu-xhci,id=usbhost,addr=0x5,p2=3,p3=0',
                '-drive', 'if=none,id=usbdata,format=raw,cache=writeback,file=' + path(image),
                '-device', 'usb-storage,id=usbdisk,bus=usbhost.0,port=1,drive=usbdata,removable=on,bootindex=1',
                '-device', 'usb-kbd,id=usbkeyboard,bus=usbhost.0,port=2',
                '-device', 'usb-mouse,id=usbmouse,bus=usbhost.0,port=3']
    for name in SENTINELS:
        command += ['-drive', f'if=none,id={name},format=raw,cache=writeback,file=' + path(sentinels[name])]
    command += ['-device', 'nvme,id=nvme-sentinel,drive=nvmeguard,serial=USBONLY-NVME,addr=0x6',
                '-device', 'ide-hd,id=ahci-sentinel,drive=sataguard,bus=ide.0',
                '-device', 'virtio-blk-pci,id=virtio-sentinel,drive=virtioguard,disable-legacy=on,addr=0x7']
    return command


def validate_enumeration(devices, ports, protocols, dcbaa):
    check(ports == 3 and list(protocols) == [2] * 3 + [0] * 29 and len(dcbaa) >= 4
          and [(d['port'], d['kind']) for d in devices] == [(1, 3), (2, 1), (3, 2)],
          'single-media USB2 storage/keyboard/mouse root topology differs')
    expected = {d['slot']: d['physical'] + 4096 for d in devices}
    check(len(expected) == 3 and all(0 < slot < len(dcbaa) for slot in expected)
          and all(value == expected.get(slot, 0) for slot, value in enumerate(dcbaa)),
          'actual DCBAA contains missing/shared/unexpected single-media context')


# Reuse every old block/DMA/channel/lease/page-table/FLUSH check verbatim.
# Private function globals alter only the four-port fixture's topology oracle;
# neither the old module nor its methods/globals are monkey-patched.
_BLOCK_SNAPSHOT = types.FunctionType(usb.UsbGuest.block_snapshot.__code__,
    dict(usb.UsbGuest.block_snapshot.__globals__, validate_enumeration=validate_enumeration),
    'single_media_block_snapshot', usb.UsbGuest.block_snapshot.__defaults__)


def validate_volume(view, device, volume, geometry, flush):
    check(view == {n: geometry[n] for n in ('base', 'capacity', 'disk_capacity')},
          'actual USB partition view differs from raw MBR')
    check(device['capacity_sectors'] == volume['total'] == view['capacity']
          and device['max_transfer_sectors'] == 128 and volume['ready'] == 1
          and volume['busy'] == volume['failed'] == volume['read_only'] == 0
          and (not flush or volume['dirty'] == 0), 'FS did not mount healthy writable logical USB partition')


def validate_smp_pcid_cpu(header, metric, registers, kernel_root, processes, cpu, incarnations, roots):
    enabled = header['pcid_enabled']
    check(enabled in (0, 1) and bool(registers['CR4'] & (1 << 17)) == bool(enabled)
          and registers['CR4'] == metric['cr4'] and not registers['CR4'] & (1 << 7),
          'actual per-CPU SMP PCIDE/PGE register/Header/Metrics disagree')
    switches, retained = metric['switches'], metric['retained']
    check(0 <= retained <= switches and (enabled or retained == 0), 'actual SMP retention counters differ')
    raw = registers['CR3']; tag, root = raw & 4095, raw & ~4095
    check(0 < root < 1 << 32 and (enabled or tag == 0), 'actual SMP raw CR3 is invalid/tagged in fallback')
    slot = None
    if enabled and tag:
        check(1 <= tag <= 16, 'actual SMP PCID exceeds the admitted process slots'); slot = tag - 1
    elif root != kernel_root:
        check(not enabled, 'actual SMP PCID tag0 does not name the kernel root'); slot = cpu['slot']
    if slot is not None:
        check(0 <= slot < 16, 'actual SMP current process slot is invalid')
        process = processes[slot]; incarnation = incarnations[slot]
        check(incarnation > 0 and process['incarnation'] == cpu['incarnation'] == incarnation
              and process['token'] == cpu['token'] == (incarnation << 8) | (slot + 1)
              and process['root'] == roots[slot] == cpu['return_root'] == root
              and cpu['slot'] == slot and cpu['mode'] in (2, 3, 6) and process['retiring'] == 0,
              'actual SMP raw CR3/current CPU/process/root/incarnation binding differs')
    return dict(enabled=bool(enabled), registers=registers, switches=switches, retained=retained,
                tag=tag, root=root, current_process_slot=slot)


class SingleMediaGuest(usb.UsbGuest):
    def __init__(self, esp, disk, state, kernel_layout, layouts, sentinels, geometry, startup_timeout=180,
                 accel='tcg', cpu=None, trace_usb=False):
        self.sentinels, self.geometry = sentinels, geometry
        self.accel, self.cpu = accel, cpu
        self.trace_usb = trace_usb
        super().__init__(esp, disk, state, kernel_layout, layouts, True, startup_timeout)

    def alive(self):
        super().alive()
        check(b'DONGOS_P6_TLB_FATAL=' not in self.raw, 'actual kernel TLB fatal: ' +
              bytes(self.raw[-1200:]).decode(errors='replace'))

    def capture_failure(self):
        report = super().capture_failure()
        def arena(virtual, length, label):
            result = bytearray()
            while len(result) < length:
                address = virtual + len(result)
                mapping = self.trusted_kernel_mapping(address)
                check(not mapping['effective_user'], 'SMP arena alias became user accessible')
                count = min(4096 - (address & 4095), length - len(result))
                result.extend(self.physical(mapping['physical'], count, label))
            return bytes(result)
        try:
            match = re.search(r'^GS\s*=\S+\s+([0-9a-fA-F]{16})', report['registers'], re.M)
            check(match is not None, 'actual BSP GS base unavailable')
            gs = int(match[1], 16)
            header = arena(gs, 256, 'actual BSP SMP entry header')
            words = list(struct.unpack('<32Q', header))
            report['actual_smp_header'] = dict(virtual=gs, words=words)
            report['actual_smp_metrics'] = list(struct.unpack('<24Q', arena(
                words[21] + 1024, 192, 'actual BSP SMP entry metrics')))
            report['actual_smp_exception'] = list(struct.unpack('<23Q', arena(
                words[20] - 184, 184, 'actual private SMP exception stack')))
            if words[28]:
                report['actual_smp_raw_frame'] = arena(words[28], 200, 'actual SMP raw user frame').hex()
        except Exception as error: report['actual_smp_header_error'] = str(error)
        for name, size in (('FAILURES', 3584), ('PROGRESS', 768), ('ACTIVE', 8)):
            try:
                report['bridge_' + name.lower()] = list(struct.unpack('<' + 'Q' * (size // 8),
                    self.kernel(self.ksym('sched.user_bridge', name), size, 'actual bridge ' + name)))
            except Exception as error: report['bridge_' + name.lower() + '_error'] = str(error)
        def hid_state():
            self.refresh_processes()
            symbols = self.gui_symbols.setdefault('xhci', gui.read_elf_symbols(
                self.esp.parent / 'services/xhci/program.elf'))
            bias = struct.unpack_from('<Q', self.processes, 13 * gui.lifecycle.PROCESS_BYTES + 224)[0]
            def data(name, size):
                return self.user(13, bias + symbols[storage.symbol('drivers.xhci_service', name)], size, 'actual ' + name)
            transport = self.struct(13, 'xhci', 'drivers.xhci_service', 'TRANSPORT', 'usb.xhci_transport.State')
            controller = self.struct(13, 'xhci', 'drivers.xhci_service', 'STATE', 'usb.xhci_controller.State')
            physical = self.number(self.layouts.part(controller, 'usb.xhci_controller.State', 'setup'),
                                   'usb.xhci_controller.Setup', 'physical')
            (self.state / 'failure-actual-usb-dma.bin').write_bytes(
                self.physical(physical, 131072, 'actual asynchronous HID DMA failure state'))
            return dict(reports=list(struct.unpack('<3Q', data('HID_REPORTS', 24))),
                        posted=struct.unpack('<Q', data('HID_POSTED', 8))[0],
                        connected=data('HID_CONNECTED', 1).hex(), transport_hex=transport.hex(),
                        controller_hex=controller.hex())
        for label, capture in (
                ('usb_input', self.input_snapshot),
                ('qmp_mice', lambda: self.qmp.request('query-mice')),
                ('xhci_hid', hid_state)):
            try: report[label] = capture()
            except Exception as error: report[label + '_error'] = str(error)
        storage.write_json(self.state / 'failure.json', report)
        return report

    def move(self, x, y):
        # A settled frame is not a receipt for a USB interrupt report. Require
        # each bounded relative step to reach input and the real compositor.
        for _ in range(100):
            raw = self.windows()
            current = [self.number(raw, 'desktop.windows.State', n) for n in ('pointer_x', 'pointer_y')]
            delta = [x - current[0], y - current[1]]
            if max(map(abs, delta)) <= 4: return
            before = self.input_snapshot()
            self.resume()
            self.qmp.request('input-send-event', dict(events=[dict(type='rel', data=dict(
                axis=a, value=max(-32, min(32, v)))) for a, v in zip(('x', 'y'), delta) if v]))
            def consumed():
                source = self.input_snapshot()
                state = self.windows()
                position = [self.number(state, 'desktop.windows.State', n) for n in ('pointer_x', 'pointer_y')]
                return (source['mouse_sequence'] > before['mouse_sequence']
                        and source['mouse_kind'] == 2 and source['queue'][1] == 0 and position != current)
            self.until(consumed, 'USB relative report and compositor movement', timeout=10)
        raise ValueError('actual USB relative pointer failed to reach target')

    def launch(self):
        up, qp = storage.free_port(), storage.free_port()
        command = single_media_command(usb.builder.qemu_command(self.esp, self.state / 'guest', test=True,accel=self.accel),
                                       self.disk, self.sentinels)
        if self.accel == 'whpx':
            command[command.index('-machine') + 1] += ',kernel-irqchip=off'
        command[command.index('-serial') + 1] = f'tcp:127.0.0.1:{up},server=on,wait=off'
        cpu = self.cpu or ('host,-vmx,-mpx,-sgx,-sgxlc' if self.accel == 'whpx' else 'max,+smep,+smap,+umip')
        command += ['-cpu', cpu, '-S', '-qmp', f'tcp:127.0.0.1:{qp},server=on,wait=off']
        if self.trace_usb:
            command += ['-trace', 'enable=usb_xhci_ep_*,file=' + str(self.state / 'qemu-usb-trace.log').replace('\\', '/'),
                        '-trace', 'enable=usb_xhci_xfer_*', '-trace', 'enable=usb_xhci_queue_event']
        self.evidence.update(command=command, single_media_efi_and_data=True, mixed_internal_disks_writable=True)
        self.stderr = (self.state / 'stderr.log').open('wb')
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=self.stderr,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.evidence['actual_qemu_executed'] = True
        self.qmp = gui.lifecycle.settings.acpi.QMP(qp, self.process)
        self.uart = socket.create_connection(('127.0.0.1', up)); self.uart.settimeout(.2)
        def reader():
            with (self.state / 'serial.log').open('wb') as stream:
                while self.process.poll() is None:
                    try: data = self.uart.recv(4096)
                    except socket.timeout: continue
                    except OSError: break
                    if not data: break
                    self.raw.extend(data); stream.write(data); stream.flush()
        self.reader = threading.Thread(target=reader, daemon=True); self.reader.start()
        self.qmp.request('cont')

    def bootstrap(self):
        self.symbols = settings.acpi.validation_symbols(self.esp.parent / 'kernel.elf')
        deadline = time.monotonic() + self.startup_timeout
        pattern = rb'^memory_runtime_boot_info=0x([0-9a-f]{16})\r?\n'
        while not re.search(pattern, self.raw, re.M):
            self.alive(); check(time.monotonic() < deadline, 'actual runtime BootInfo not published'); time.sleep(.02)
        addresses = re.findall(pattern, self.raw, re.M)
        check(len(addresses) == 1, 'duplicate actual BootInfo publication')
        self.pause()
        self.boot = struct.unpack('<20Q', self.physical(int(addresses[0], 16) - settings.acpi.HHDM, 160, 'BootInfo'))
        self.resume()
        for marker in (b'DONGOS_XHCI_HID_BLOCK_RPC_READY\r\n', b'DONGOS_USB_ONLY_BLOCK_READY\r\n',
                       b'DONGOS_SHELL_READY\r\n', b'DONGOS_P7_CLIENTS_READY\r\n'):
            self.wait(marker, self.startup_timeout)
        self.pause(); self.refresh_processes(); self.validate_private_pools()
        rates = re.findall(rb'^platform_tsc_hz=0x([0-9a-f]{16})\r?$', self.raw, re.M)
        check(len(rates) == 1, 'one actual trusted platform clock required')
        hz = int(rates[0], 16)
        configs = self.catalog()['configs'][:18]
        check(1000000 <= hz <= 16000000000 and len(configs) == 18
              and all(c['timeout'] == hz * (60 if c['id'] == 1 else 10) for c in configs),
              'actual USB catalog startup budget differs from trusted profile')
        self.evidence['actual_startup_budget'] = dict(tsc_hz=hz, fs_seconds=60, other_seconds=10,
                                                    configs=configs)
        self.bias = struct.unpack_from('<Q', self.processes, 3 * gui.lifecycle.PROCESS_BYTES + 224)[0]
        self.syms = gui.read_elf_symbols(self.esp.parent / 'services/compositor/program.elf')
        self.verify_elf()
        self.evidence['actual_xhci_elf'] = self.verify_process(13, 'xhci')
        self.evidence['actual_kernel_executable_bytes'] = self.verify_code()
        self.settle()

    def topology(self):
        blocks = self.qmp.request('query-block')
        wanted = dict(usbdata=self.disk, **self.sentinels)
        evidence = {}
        for name, path in wanted.items():
            found = [item for item in blocks if item.get('device') == name]
            check(len(found) == 1, 'actual QMP backing drive missing/duplicated: ' + name)
            inserted = found[0].get('inserted', {})
            check(inserted.get('ro') is False and inserted.get('drv') == 'raw'
                  and Path(inserted.get('file', '')).resolve() == Path(path).resolve(),
                  'actual drive backing/format/writability differs: ' + name)
            evidence[name] = found[0]
        pci = self.qmp.request('query-pci')
        def devices(buses):
            for bus in buses:
                for device in bus.get('devices', []):
                    yield device
                    bridge = device.get('pci_bridge', {})
                    if 'bus' in bridge: yield from devices([bridge['bus']])
        ids = [d.get('qdev_id') for d in devices(pci)]
        check(all(ids.count(name) == 1 for name in ('usbhost', 'nvme-sentinel', 'virtio-sentinel')),
              'actual mixed PCI controller topology differs')
        return dict(blocks=evidence, pci=pci, all_internal_disks_actually_writable=True)

    def block_snapshot(self, capacity, flush=False):
        self.pause()
        result = _BLOCK_SNAPSHOT(self, capacity, flush)
        zeros = {}
        for name, size in (('SELECTED', 8), ('SELECTED_KIND', 8), ('ADMITTED_BLOCK', 8),
                           ('BLOCK_GRANT_ATTEMPTED', 1), ('AHCI_DMA_ENABLED', 1), ('NVME_DMA_ENABLED', 1),
                           ('BARS', 6 * 24), ('VIRTUAL', 6 * 8), ('DMA_LEASE', 32)):
            raw = self.kernel(self.ksym('user.devices', name), size, 'denied internal PCI storage ' + name)
            check(raw == bytes(size), 'internal PCI storage received actual authority: ' + name)
            zeros[name] = dict(bytes=size, all_zero=True)
        for name in ('PCI_OWNERS', 'PCI_TOKENS'):
            raw = self.kernel(self.ksym('user.device_host', name), 8, 'actual denied PCI block ledger')
            check(raw == bytes(8), 'device manager attached internal PCI block ledger: ' + name)
            zeros[name + '[0]'] = 0
        raw = self.struct(2, 'block', 'drivers.block_service', 'USB_VIEW', 'drivers.usb_partition.View')
        view = {n: self.number(raw, 'drivers.usb_partition.View', n) for n in ('base', 'capacity', 'disk_capacity')}
        raw = self.struct(1, 'fs', 'fs.service', 'DEVICE', 'fs.fat32.Device')
        device = {n: self.number(raw, 'fs.fat32.Device', n) for n in ('capacity_sectors', 'max_transfer_sectors')}
        raw = self.struct(1, 'fs', 'fs.service', 'VOLUME', 'fs.fat32.Volume')
        volume = {n: self.number(raw, 'fs.fat32.Volume', n)
                  for n in ('device', 'ready', 'busy', 'failed', 'read_only', 'dirty', 'total')}
        fs_bias = struct.unpack_from('<Q', self.processes, gui.lifecycle.PROCESS_BYTES + 224)[0]
        check(volume['device'] == fs_bias + self.gui_symbols['fs'][storage.symbol('fs.service', 'DEVICE')],
              'actual FS volume references another block device')
        validate_volume(view, device, volume, self.geometry, flush)
        for name, value in (('usb_partition_lba', view['base']), ('usb_partition_sectors', view['capacity']),
                            ('usb_raw_capacity', view['disk_capacity'])):
            actual = re.findall(('^' + name + r'=0x([0-9a-f]{16})\r?$').encode(), self.raw, re.M)
            check(len(actual) == 1 and int(actual[0], 16) == value, 'USB serial/actual partition view differs: ' + name)
        result.update(denied_internal_pci_authority=zeros, actual_usb_view=view, actual_fs_device=device, actual_fs_volume=volume)
        return result


class LiveCaptureGuest(SingleMediaGuest):
    """Run without QMP stop; freeze once for the complete terminal audit."""
    def __init__(self, *args, **kwargs):
        self.frozen, self.stop_count, self.live_pixels = False, 0, {}
        super().__init__(*args, **kwargs)

    def pause(self):
        # Legacy HID readers call pause(). During live observation it must never
        # stop a WHPX TSC while an AP waits for the BSP's production BKL.
        check(not self.frozen or self.stopped, 'final frozen guest unexpectedly running')

    def resume(self):
        check(not self.frozen, 'resume forbidden after final live capture stop')

    def stop_final(self):
        check(not self.frozen and self.stop_count == 0, 'only one final stop allowed')
        self.qmp.request('stop'); self.frozen = self.stopped = True; self.stop_count += 1; self.tables = {}
        check(self.qmp.request('query-status').get('running') is False, 'final capture did not stop')
        self.evidence.update(live_capture=True, qmp_stop_count=1, no_resume_after_final_stop=True)

    def capture_failure(self):
        if not self.frozen and self.qmp is not None: self.stop_final()
        return super().capture_failure()

    def bootstrap(self):
        self.symbols = settings.acpi.validation_symbols(self.esp.parent / 'kernel.elf')
        for marker in (b'DONGOS_XHCI_HID_BLOCK_RPC_READY\r\n', b'DONGOS_USB_ONLY_BLOCK_READY\r\n',
                       b'DONGOS_INPUT_USB_READY\r\n', b'DONGOS_SHELL_READY\r\n', b'DONGOS_P7_CLIENTS_READY\r\n'):
            self.wait(marker, self.startup_timeout)
        addresses = re.findall(rb'^memory_runtime_boot_info=0x([0-9a-f]{16})\r?\n', self.raw, re.M)
        check(len(addresses) == 1, 'one live immutable BootInfo publication required')
        self.boot = struct.unpack('<20Q', self.physical(int(addresses[0], 16) - settings.acpi.HHDM, 160, 'live immutable BootInfo'))
        self.refresh_processes(); self.live_roots = self.roots[:]
        self.static_pools, self.storage_runtime = settings.storage_profile(self.esp)
        self.pool_limits = list(struct.unpack('<16Q', self.kernel(self.ksym('user.memory', 'POOL_LIMITS'), 128, 'live immutable pool limits')))
        check(self.pool_limits == [32] * 3 + [128] + [32] * 12, 'live private pool limits differ')
        self.bias = struct.unpack_from('<Q', self.processes, 3 * gui.lifecycle.PROCESS_BYTES + 224)[0]
        self.syms = gui.read_elf_symbols(self.esp.parent / 'services/compositor/program.elf')
        self.live_apps = {role: super(LiveCaptureGuest, self).app(role) for role in range(1, 5)}

    def app(self, role):
        return super().app(role) if self.frozen else self.live_apps[role]

    def refresh_processes(self):
        if not self.frozen and hasattr(self, 'live_roots'): return self.processes
        return super().refresh_processes()

    def model_text(self, role, name='text'):
        if self.frozen: return super().model_text(role, name)
        pid, image, _ = self.app(role)
        if image not in self.gui_symbols:
            self.gui_symbols[image] = gui.read_elf_symbols(self.esp.parent / 'services' / image / 'program.elf')
        bias = struct.unpack_from('<Q', self.processes, pid * gui.lifecycle.PROCESS_BYTES + 224)[0]
        address = bias + self.gui_symbols[image][storage.symbol('lib.gui_app', 'MODEL')]
        field = self.layouts.field('lib.widget_state.State', name)
        length_address = address + self.layouts.offset('lib.widget_state.State', name + '_length')
        length = int.from_bytes(self.user(pid, length_address, 8, 'live actual model length'), 'little')
        check(length <= field['size'], 'live model string exceeds actual buffer')
        data = self.user(pid, address + field['offset'], length, 'live actual model characters') if length else b''
        # A changing length is no consumer receipt; retry the existing predicate.
        return data if self.user(pid, length_address, 8, 'live stable model length') == struct.pack('<Q', length) else b'\xff'

    def frame_stable(self):
        return (self.value('FRAME_BUSY') == self.value('CACHE_MASK') == self.value('MOTION_ACTIVE') == 0
                and self.field('CACHES_DIRTY', 1) == self.field('BACKGROUND_DIRTY', 1) == b'\0'
                and self.field('ALPHA', 32) == self.field('PRESENTED_ALPHA', 32)
                and self.field('VISUAL_RECTS', 128) == self.field('PRESENTED_RECTS', 128)
                and self.value('STYLE_REVISION') == self.value('PRESENTED_STYLE_REVISION'))

    def until(self, predicate, label, timeout=30):
        deadline = time.monotonic() + timeout
        while not predicate():
            self.alive(); check(not self.frozen and time.monotonic() < deadline, 'missing live receipt: ' + label)
            time.sleep(.03)

    def settle(self):
        if self.frozen:
            check(self.frame_stable(), 'final frozen compositor frame is incomplete'); return
        self.until(self.frame_stable, 'complete actual compositor frame')

    def button(self, down):
        check(not self.frozen, 'mouse activity forbidden after final stop')
        before = self.input_snapshot(); super().button(down)
        self.await_mouse(down, before['mouse_sequence'])

    def shell(self, command, expected=None, *, expect_error=False, exact=None):
        check(not self.frozen, 'UART activity forbidden after final stop')
        encoded = gui.lifecycle.fat.command_bytes(command); before = len(self.raw)
        self.uart.sendall(encoded + b'\r'); deadline = time.monotonic() + 120
        while True:
            segment = bytes(self.raw[before:])
            response = gui.lifecycle.fat.fresh_response(segment, command, expected=expected, expect_error=expect_error, exact=exact)
            if response is not None: break
            self.alive(); check(time.monotonic() < deadline, 'live UTF-8 UART response timeout'); time.sleep(.02)
        return dict(command=command, command_utf8_sha256=hashlib.sha256(encoded).hexdigest(),
                    serial_offset=before, serial_segment_sha256=hashlib.sha256(segment).hexdigest(), **response)

    def sample_pixels(self, role, surface):
        check(self.frozen, 'static smoke pixels require final stop')
        points = self.live_pixels[role]
        captured = points[0]['capture_surface']
        check(captured == dict(pid=surface['image']['pid'], **{n: surface[n] for n in ('client_address', 'width', 'height', 'stride')}),
              'live/final pixel surface identity or geometry changed')
        for point in points:
            source = struct.unpack('<I', self.user(surface['image']['pid'], surface['client_address'] +
                point['source_y'] * surface['stride'] + point['source_x'] * 4, 4, 'frozen same client sample'))[0] | 0xff000000
            cache = struct.unpack('<I', self.user(3, point['cache_virtual'], 4, 'frozen same private cache sample'))[0]
            check(source == point['source'] and cache == point['cache'], 'live/frozen client or cache sample changed')
            if role == 1:
                d = self.descriptor()
                gop = struct.unpack('<I', self.physical(self.boot[8] + (point['y'] * d[3] + point['x']) * 4, 4, 'final current GOP sample'))[0] & 0xffffff
                gui.validate_pixels(source, cache, gop, d[4])
                check(gop == point['gop'], 'final focused GOP differs from live capture')
        return points

    def capture_live_pixels(self):
        for role in (2, 3, 4, 1):
            pid, image, _ = self.app(role)
            raw = self.struct(pid, image, 'lib.gui_app', 'WINDOW', 'lib.window.Session')
            record = {n: self.number(raw, 'lib.window.Session', n) for n in ('width', 'height', 'stride')}
            record.update(image=dict(pid=pid), client_address=self.number(raw, 'lib.window.Session', 'address'))
            points = gui.GuiGuest.sample_pixels(self, role, record)
            d = self.descriptor(); q = d[14]; px = lambda v: (v * q + 128) // 256
            slots = self.layouts.part(self.windows(), 'desktop.windows.State', 'slots'); size = self.layouts.size('desktop.windows.Slot')
            rect = struct.unpack('<4q', self.layouts.part(slots[(role - 1) * size:role * size], 'desktop.windows.Slot', 'rect'))
            left, top, right, bottom = rect; stride = right - left + px(24)
            for p in points:
                x, y = p['x'] - left - px(12), p['y'] - top - px(43)
                p.update(cache_virtual=d[13] + (role - 1) * 0x200000 + ((y + px(55)) * stride + x + px(24)) * 4,
                         gop_capture_phase='running-before-final-stop',
                         capture_surface=dict(pid=pid, **{n: record[n] for n in ('client_address', 'width', 'height', 'stride')}))
            self.live_pixels[role] = points

    def smp_fields(self, typename, address):
        raw = self.virtual_kernel(address, self.layouts.size(typename), 'actual ' + typename)
        return {f['name']: self.number(raw, typename, f['name']) for f in self.layouts.types[typename]['fields'] if f['size'] in (1, 4, 8)}

    def smp_health(self):
        check(self.frozen and self.stopped and self.stop_count == 1, 'SMP audit requires the one final stopped epoch')
        if hasattr(self, '_smp_health_cache'): return self._smp_health_cache
        failures = self.kernel(self.ksym('sched.user_bridge', 'FAILURES'), 16 * 224, 'all first Bridge failures')
        check(failures == bytes(16 * 224), 'actual SMP Bridge recorded a failure')
        bridge = self.smp_fields('sched.user_bridge.Bridge', self.kval('sched.user_bridge', 'ACTIVE'))
        report = self.smp_fields('sched.user_boot.Report', self.kval('sched.user_boot', 'INFO'))
        domain = self.smp_fields('sched.user_domain.Domain', report['domain'])
        check(bridge['ready'] == report['ready'] == domain['ready'] == 1
              and bridge['failed'] == report['failed'] == domain['failed'] == 0
              and bridge['domain'] == report['domain'] and bridge['headers'] == report['headers']
              and report['published'] == 1 and report['count'] == 4 and report['online'] == domain['online'] == 15
              and report['root'] == domain['kernel_root'], 'actual SMP Report/Bridge/Domain failed')
        headers = struct.unpack('<4Q', self.virtual_kernel(report['headers'], 32, 'actual four SMP Headers'))
        check(len(set(headers)) == 4 and all(headers), 'actual CPU Header identity differs')
        metrics = [self.smp_fields('sched.user_entry_plan.Metrics', h + 5632) for h in headers]
        check(all(m['failed'] == 0 for m in metrics), 'actual CPU metrics.failed is nonzero')
        registers = [self.qmp.request('human-monitor-command', {'command-line': 'info registers', 'cpu-index': cpu}) for cpu in range(4)]
        header_values = []
        for cpu, text in enumerate(registers):
            head = self.smp_fields('sched.user_entry_plan.Cpu', headers[cpu]); header_values.append(head)
            gs = re.search(r'^GS\s*=\S+\s+([0-9a-fA-F]{16})', text, re.M)
            cr4 = re.search(r'\bCR4=([0-9a-fA-F]+)', text)
            check(head['ready'] == 2 and head['last_error'] == 0 and head['result'] == 0x55534552534d5036
                  and head['domain'] == report['domain'] and head['logical_id'] == cpu and head['original_cr3'] == report['root']
                  and head['kernel_stack'] > head['stack_bottom'] > 0 and head['root_frame'] != 0
                  and head['kernel_xstate'] == headers[cpu] + 4608
                  and gs is not None and int(gs[1], 16) in (0, headers[cpu])
                  and cr4 is not None and int(cr4[1], 16) == metrics[cpu]['cr4'], 'CPU GS/Header/metrics identity differs')
        self._smp_health_cache = dict(bridge=bridge, report=report, domain=domain, headers=list(headers), metrics=metrics,
            header_values=header_values, registers=registers, all_bridge_failure_bytes_zero=True, all_cpu_failed_zero=True)
        return self._smp_health_cache

    def pcid_snapshot(self):
        smp = self.smp_health(); domain = smp['domain']
        if hasattr(self, '_smp_pcid_cache'): return self._smp_pcid_cache
        processes = [self.smp_fields('sched.user_domain.Process', domain['processes'] + slot * self.layouts.size('sched.user_domain.Process')) for slot in range(16)]
        cpus = [self.smp_fields('sched.user_domain.Cpu', domain['cpus'] + cpu * self.layouts.size('sched.user_domain.Cpu')) for cpu in range(4)]
        incarnations = self.catalog()['incarnations']; records = []
        for cpu in range(4):
            registers = gui.lifecycle.parse_registers(smp['registers'][cpu])
            record = validate_smp_pcid_cpu(smp['header_values'][cpu], smp['metrics'][cpu], registers,
                domain['kernel_root'], processes, cpus[cpu], incarnations, self.roots)
            record.update(cpu=cpu, header=smp['headers'][cpu], actual_cpu=cpus[cpu],
                seen=[self.smp_fields('sched.user_domain.Seen', cpus[cpu]['seen'] + slot * self.layouts.size('sched.user_domain.Seen')) for slot in range(16)])
            records.append(record)
        self._smp_pcid_cache = dict(enabled=all(r['enabled'] for r in records), registers=records[0]['registers'],
            switches=sum(r['switches'] for r in records), retained=sum(r['retained'] for r in records), per_cpu=records,
            per_cpu_smp=True, warm_retention_acceptance=False, processes=processes, actual_incarnations=incarnations)
        return self._smp_pcid_cache

    def exercise_live(self, boot):
        raw = self.struct(2, 'block', 'drivers.block_service', 'USB', 'drivers.usb_block_proxy.State')
        before = self.number(raw, 'drivers.usb_block_proxy.State', 'completed')
        trace = self.kernel(self.ksym('boot.trace_runtime', 'STORAGE'), 4096, 'live sealed boot trace')
        evidence = dict(topology=self.topology(), hid=self.hid(), live_capture=True,
                        actual_completed_before_live_actions=before)
        commands = []
        self.evidence.update(live_hid=evidence['hid'], live_commands=commands)
        if boot == 0:
            for command, expected in [('mkdir ' + gui.lifecycle.fat.quote(DIRECTORY), b'MKDIR OK\r\n'),
                ('write ' + gui.lifecycle.fat.quote(DOCUMENT) + ' ' + FIRST.decode(), b'WRITE OK\r\n'),
                ('append ' + gui.lifecycle.fat.quote(DOCUMENT) + ' ' + TAIL.decode(), b'APPEND OK\r\n'),
                ('write ' + gui.lifecycle.fat.quote(REMOVED) + ' remove-me', b'WRITE OK\r\n'),
                ('rm ' + gui.lifecycle.fat.quote(REMOVED), b'RM OK\r\n')]: commands.append(self.shell(command, exact=expected))
        commands.append(self.shell('cat ' + gui.lifecycle.fat.quote(DOCUMENT), exact=PAYLOAD + b'\r\n'))
        self.capture_live_pixels()
        commands.append(self.shell('sync', exact=b'SYNC OK\r\n'))
        for _ in range(3): self.settle(); time.sleep(.05)
        self.stop_final(); self.settle(); self.refresh_processes()
        check(self.roots == self.live_roots, 'live/final service roots changed')
        check(all(self.app(role) == self.live_apps[role] for role in range(1, 5)), 'live/final GUI incarnation changed')
        self.validate_private_pools(); self.verify_elf()
        self.evidence['actual_xhci_elf'] = self.verify_process(13, 'xhci')
        self.evidence['actual_kernel_executable_bytes'] = self.verify_code()
        rates = re.findall(rb'^platform_tsc_hz=0x([0-9a-f]{16})\r?$', self.raw, re.M)
        check(len(rates) == 1, 'one actual trusted platform clock required')
        hz = int(rates[0], 16); configs = self.catalog()['configs'][:18]
        check(1000000 <= hz <= 16000000000 and len(configs) == 18
              and all(c['timeout'] == hz * (60 if c['id'] == 1 else 10) for c in configs), 'actual USB startup budgets changed')
        self.evidence['actual_startup_budget'] = dict(tsc_hz=hz, fs_seconds=60, other_seconds=10, configs=configs)
        evidence.update(gui=self.smoke('single-usb-live-final'), durable_flush=self.block_snapshot(self.geometry['disk_capacity'], flush=True),
                        smp=self.smp_health(), final_input=self.input_snapshot(), commands=commands, actual_shell_same_disk_readback=True)
        check(evidence['durable_flush']['block']['completed'] > before, 'live USB operations caused no actual completions')
        final = self.input_snapshot(); check(not final['usb_keyboard_down'] and not final['aggregate_keyboard_down']
            and not final['usb_left'] and not final['aggregate_left'] and final['queue'][1] == 0, 'final actual input not released/drained')
        evidence['boot_trace'] = self.trace_snapshot('final-live-capture')
        check((self.state / 'trace-final-live-capture/trace.bin').read_bytes() == trace, 'sealed trace changed during live activity')
        evidence.update(final_screenshot=self.screenshot('single-usb-live-desktop-final'), evidence=self.evidence)
        check(self.stop_count == 1 and self.qmp.request('query-status').get('running') is False, 'final audit resumed guest')
        return evidence


def sentinel_hashes(sentinels):
    return {name: settings.sha(ordinary(path)) for name, path in sentinels.items()}


def run(args):
    esp = args.reuse_esp.resolve()
    out = args.output or ROOT / 'build/test/usb-only-hardware/qemu' / ('run-' + uuid.uuid4().hex[:12])
    out = make_usb_image._reject_special(out)
    check(not out.exists(), 'output must be a new independent directory')
    out.parent.mkdir(parents=True, exist_ok=True)
    make_usb_image._no_links(out.parent, directory=True)
    out.mkdir()
    result = dict(passed=False, boots=[], actual_qemu_boots=0, full_os_build_executed=False,
                  no_guest_memory_or_register_writes=True, no_physical_devices=True,
                  guest_test_files_created_only_by_actual_shell=True)
    guest = None
    names = ('tests/run_usb_only_hardware_qemu.py', 'tests/run_usb_runtime_qemu.py', 'tests/run_gui_clients_qemu.py',
             'tests/run_process_lifecycle_qemu.py', 'tests/run_desktop_settings_qemu.py', 'tests/run_fat_paths_qemu.py',
             'tests/run_clock_calibration_qemu.py', 'tests/fat_paths_oracle.py', 'tests/boot_trace_capture.py',
             'tests/boot_trace_oracle.py', 'tools/build.py', 'tools/build_usb.py', 'tools/usb_only_profile.py',
             'tools/make_usb_image.py', 'tools/make_fat32_disk.py')
    fingerprints = {n: settings.sha(ROOT / n) for n in names}
    sentinels = None; before = None
    try:
        manifest, _ = verify_profile(esp)
        build_sha = settings.sha(esp.parent / 'build-inputs.json')
        result.update(build_manifest_sha256=build_sha, usb_only_profile=manifest['usb_only_profile'])
        layouts, identity = checked_layouts(esp)
        result['completed_source_identity'] = identity
        result['inherited_block_contract_sha256'] = hashlib.sha256(inspect.getsource(usb.UsbGuest.block_snapshot).encode()).hexdigest()
        kernel_layout = checked_kernel_memory_layout(esp)
        image = out / 'single-usb.img'
        initial = make_single_media(esp, image, args.size_mib)
        result['single_media'] = initial
        result['initial_raw_disk'] = disk_evidence(image, initial, written=False)
        sentinels = {name: out / (name + '.img') for name in SENTINELS}
        for name, path in sentinels.items():
            create_sentinel(path, 64)
            with path.open('r+b') as stream:
                stream.seek(-512, os.SEEK_END); stream.write(('DongOS untouched ' + name).encode().ljust(512, b'\xa5'))
                stream.flush(); os.fsync(stream.fileno())
        before = sentinel_hashes(sentinels)
        check(len(set(before.values())) == 3, 'internal sentinel disk identities are not distinct')
        result['internal_disks_initial_sha256'] = before
        for boot in range(2):
            guest_class = LiveCaptureGuest if args.live_capture else SingleMediaGuest
            guest = guest_class(esp, image, out / ('boot-' + str(boot + 1)), kernel_layout,
                                     layouts, sentinels, initial['geometry'], args.startup_timeout,
                                     accel=args.accel,cpu=args.cpu,trace_usb=args.trace_usb)
            if args.live_capture:
                evidence = guest.exercise_live(boot)
                if args.require_pcid:
                    check(evidence['gui']['pcid']['enabled'] and evidence['gui']['pcid']['retained'] > 0,
                          'actual PCID retention required')
            else:
                evidence = paused_exercise(guest, initial, boot, args.require_pcid)
            guest.close(); guest = None
            evidence['raw_disk'] = disk_evidence(image, initial, written=True)
            evidence['internal_disks_sha256'] = sentinel_hashes(sentinels)
            check(evidence['internal_disks_sha256'] == before, 'whole writable internal sentinel disk SHA changed')
            result['boots'].append(evidence)
            storage.write_json(out / 'progress.json', result)
            if boot:
                check(result['boots'][0]['raw_disk']['image_sha256'] == evidence['raw_disk']['image_sha256'],
                      'read-only second boot changed durable single USB')
        verify_profile(esp)
        check(settings.sha(esp.parent / 'build-inputs.json') == build_sha, 'completed build identity changed')
        result['passed'] = True
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        if guest is not None:
            for label, action in (('failure_state', guest.capture_failure),
                                  ('failure_screenshot', lambda: guest.screenshot('failure'))):
                try: action(); result[label] = True
                except Exception as nested: result[label + '_error'] = str(nested)
    finally:
        if guest is not None:
            try: guest.close()
            except Exception as error: result.update(passed=False, cleanup_error=str(error))
        manifests = [json.loads(p.read_text()) for p in out.glob('boot-*/guest.json')]
        result['actual_qemu_boots'] = sum(r.get('actual_qemu_executed') is True for r in manifests)
        result['all_started_guests_stopped'] = all(not r.get('actual_qemu_executed') or r.get('qemu_stopped') for r in manifests)
        result['runner_inputs_unchanged'] = all(settings.sha(ROOT / n) == h for n, h in fingerprints.items())
        result['runner_input_sha256'] = fingerprints
        if sentinels is not None and before is not None:
            result['internal_disks_final_sha256'] = sentinel_hashes(sentinels)
            result['complete_internal_disks_unchanged'] = result['internal_disks_final_sha256'] == before
            if not result['complete_internal_disks_unchanged']:
                result.update(passed=False, error='whole writable internal sentinel disk SHA changed')
        if result['passed']:
            try:
                result.update(usb.validate_boots(manifests, 2))
                check(result['runner_inputs_unchanged'], 'runner source changed during execution')
            except ValueError as error: result.update(passed=False, error=str(error))
        storage.write_json(out / 'result.json', result)
    print('Single USB hardware', 'PASS' if result['passed'] else 'FAIL', out, result.get('error', ''), flush=True)
    return 0 if result['passed'] else 1


def paused_exercise(guest, initial, boot, require_pcid):
    evidence = dict(topology=guest.topology(), gui=guest.smoke('usb-only-' + str(boot + 1)),
                    before=guest.block_snapshot(initial['geometry']['disk_capacity']), hid=guest.hid())
    evidence['boot_trace'] = guest.trace_snapshot('before-storage')
    if require_pcid:
        check(evidence['gui']['pcid']['enabled'] and evidence['gui']['pcid']['retained'] > 0,
              'actual PCID retention required')
    commands = []
    if boot == 0:
        for command, expected in [('mkdir ' + gui.lifecycle.fat.quote(DIRECTORY), b'MKDIR OK\r\n'),
            ('write ' + gui.lifecycle.fat.quote(DOCUMENT) + ' ' + FIRST.decode(), b'WRITE OK\r\n'),
            ('append ' + gui.lifecycle.fat.quote(DOCUMENT) + ' ' + TAIL.decode(), b'APPEND OK\r\n'),
            ('write ' + gui.lifecycle.fat.quote(REMOVED) + ' remove-me', b'WRITE OK\r\n'),
            ('rm ' + gui.lifecycle.fat.quote(REMOVED), b'RM OK\r\n')]:
            commands.append(guest.shell(command, exact=expected))
        commands.append(guest.shell('sync', exact=b'SYNC OK\r\n'))
        evidence['durable_flush'] = guest.block_snapshot(initial['geometry']['disk_capacity'], flush=True)
        check(evidence['durable_flush']['block']['completed'] > evidence['before']['block']['completed'],
              'guest writes/FLUSH caused no USB completions')
    commands.append(guest.shell('cat ' + gui.lifecycle.fat.quote(DOCUMENT), exact=PAYLOAD + b'\r\n'))
    evidence.update(commands=commands, actual_shell_same_disk_readback=True, evidence=guest.evidence)
    evidence['after'] = guest.block_snapshot(initial['geometry']['disk_capacity'])
    evidence['boot_trace_after_storage'] = guest.trace_snapshot('after-storage')
    check((guest.state / 'trace-before-storage/trace.bin').read_bytes()
          == (guest.state / 'trace-after-storage/trace.bin').read_bytes(), 'sealed boot trace changed')
    evidence['final_screenshot'] = guest.screenshot('single-usb-desktop-final')
    return evidence

class HostControls(unittest.TestCase):
    def test_smp_pcid_binds_actual_per_cpu_controls_roots_and_incarnations(self):
        processes = [dict(root=0, token=0, incarnation=0, retiring=0) for _ in range(16)]
        processes[4] = dict(root=0x180000, token=(7 << 8) | 5, incarnation=7, retiring=0)
        roots, incarnations = [0] * 16, [0] * 16; roots[4], incarnations[4] = 0x180000, 7
        header = dict(pcid_enabled=1); metric = dict(switches=10, retained=8, cr4=1 << 17)
        registers = dict(CR0=0, CR3=0x180005, CR4=1 << 17)
        cpu = dict(slot=4, token=(7 << 8) | 5, incarnation=7, return_root=0x180000, mode=2)
        args = dict(header=header, metric=metric, registers=registers, kernel_root=0x400000,
                    processes=processes, cpu=cpu, incarnations=incarnations, roots=roots)
        self.assertEqual(validate_smp_pcid_cpu(**args)['current_process_slot'], 4)
        self.assertIsNone(validate_smp_pcid_cpu(**dict(args, registers=dict(registers, CR3=0x400000)))['current_process_slot'])
        fallback = dict(args, header=dict(pcid_enabled=0), metric=dict(switches=10, retained=0, cr4=0),
                        registers=dict(CR0=0, CR3=0x180000, CR4=0))
        self.assertFalse(validate_smp_pcid_cpu(**fallback)['enabled'])
        self.assertIsNone(validate_smp_pcid_cpu(**dict(fallback, registers=dict(CR0=0, CR3=0x400000, CR4=0)))['current_process_slot'])
        for bad in (dict(args, registers=dict(registers, CR4=0)),
                    dict(args, metric=dict(metric, retained=11)),
                    dict(args, metric=dict(metric, cr4=(1 << 17) | (1 << 7)), registers=dict(registers, CR4=(1 << 17) | (1 << 7))),
                    dict(args, registers=dict(registers, CR3=0x180000)),
                    dict(args, registers=dict(registers, CR3=0x180011)),
                    dict(args, registers=dict(registers, CR3=0x181005)),
                    dict(args, incarnations=[0] * 16), dict(args, cpu=dict(cpu, token=1)),
                    dict(fallback, metric=dict(fallback['metric'], retained=1)),
                    dict(fallback, registers=dict(registers, CR4=0)), dict(fallback, cpu=dict(cpu, slot=5))):
            with self.assertRaises(ValueError): validate_smp_pcid_cpu(**bad)

    def test_live_observer_never_stops_until_terminal_freeze_and_cannot_resume(self):
        guest = object.__new__(LiveCaptureGuest)
        guest.frozen, guest.stopped, guest.stop_count, guest.tables, guest.evidence = False, False, 0, {}, {}
        calls = []
        guest.qmp = types.SimpleNamespace(request=lambda command: calls.append(command) or {'running': False})
        guest.pause(); guest.resume(); guest.pause()
        self.assertEqual(calls, [])
        guest.stop_final(); guest.pause()
        self.assertEqual(calls, ['stop', 'query-status'])
        with self.assertRaises(ValueError): guest.resume()
        with self.assertRaises(ValueError): guest.stop_final()
        guest.frame_stable = lambda: False
        with self.assertRaises(ValueError): guest.settle()
        self.assertEqual(calls, ['stop', 'query-status'])

    def test_three_port_contract_rejects_old_four_port_fixture(self):
        devices = [dict(port=p, kind=k, slot=p, physical=p * 0x10000) for p, k in ((1, 3), (2, 1), (3, 2))]
        dcbaa = [0] + [d['physical'] + 4096 for d in devices]
        validate_enumeration(devices, 3, [2] * 3 + [0] * 29, dcbaa)
        for ports, protocols, table in ((4, [2] * 4 + [0] * 28, dcbaa),
                                         (3, [2] * 3 + [0] * 29, dcbaa + [123]),
                                         (3, [2] * 2 + [3] + [0] * 29, dcbaa)):
            with self.assertRaises(ValueError): validate_enumeration(devices, ports, protocols, table)
        self.assertIs(_BLOCK_SNAPSHOT.__code__, usb.UsbGuest.block_snapshot.__code__)
        self.assertIs(usb.UsbGuest.block_snapshot.__globals__['validate_enumeration'], usb.validate_enumeration)
        self.assertIsNot(_BLOCK_SNAPSHOT.__globals__, usb.UsbGuest.block_snapshot.__globals__)

    def test_logical_volume_boundary_contract(self):
        geometry = dict(base=2048, capacity=258048, disk_capacity=262144)
        device = dict(capacity_sectors=geometry['capacity'], max_transfer_sectors=128)
        volume = dict(total=geometry['capacity'], ready=1, busy=0, failed=0, read_only=0, dirty=0)
        validate_volume(geometry, device, volume, geometry, True)
        for view, dev, vol in ((dict(geometry, base=0), device, volume),
                               (geometry, dict(device, capacity_sectors=geometry['disk_capacity']), volume),
                               (geometry, device, dict(volume, total=geometry['disk_capacity'])),
                               (geometry, device, dict(volume, dirty=1))):
            with self.assertRaises(ValueError): validate_volume(view, dev, vol, geometry, True)

    def test_single_media_mbr_payloads_and_real_writable_topology(self):
        with tempfile.TemporaryDirectory(prefix='dongos-usb-only-') as temporary:
            folder = Path(temporary)
            esp = folder / 'esp'; (esp / 'EFI/BOOT').mkdir(parents=True)
            for name, data in (('EFI/BOOT/BOOTX64.EFI', b'EFI fixture'), ('DONGOS.IMG', b'kernel fixture'),
                               ('SERVICES.BIN', b'services fixture')):
                (esp / name).write_bytes(data)
            image = folder / 'single.img'
            initial = make_single_media(esp, image, 128)
            self.assertTrue(disk_evidence(image, initial, written=False)['boot_payloads_preserved'])
            sentinels = {}
            for name in SENTINELS:
                path = folder / (name + '.img'); path.write_bytes(b'sentinel')
                sentinels[name] = path
            base = ['qemu', '-machine', 'q35', '-drive', 'if=pflash,format=raw,file=code.fd',
                    '-drive', 'if=pflash,format=raw,file=vars.fd', '-drive', 'format=raw,file=fat:rw:esp',
                    '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
            command = single_media_command(base, image, sentinels)
            self.assertEqual(base[base.index('-machine') + 1], 'q35')
            self.assertIn('q35,sata=on,i8042=off', command)
            self.assertFalse(any('fat:rw:' in value or 'readonly=on' in value or 'snapshot=on' in value for value in command))
            self.assertEqual(sum(value.startswith('usb-storage,') for value in command), 1)
            self.assertEqual(sum(value.startswith('if=none,') for value in command), 4)
            self.assertIn('qemu-xhci,id=usbhost,addr=0x5,p2=3,p3=0', command)
            for suffix in (['-drive', 'if=none,id=unrelated,file=x.img'], ['-device', 'nvme,drive=x'],
                           ['-device', 'usb-host,vendorid=0x1234'], ['-device', 'scsi-hd,drive=x'],
                           ['-snapshot'], ['-blockdev', 'driver=file,node-name=x,filename=x.img']):
                with self.assertRaises(ValueError): single_media_command(base + suffix, image, sentinels)
            broken = dict(sentinels); broken['nvmeguard'] = image
            with self.assertRaises(ValueError): single_media_command(base, image, broken)
            with image.open('r+b') as stream: stream.seek(462); stream.write(b'\x80')
            with self.assertRaises(ValueError): read_partition(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-esp', type=Path)
    parser.add_argument('--output', type=Path, help='new independent output directory; never reused')
    parser.add_argument('--size-mib', type=int, choices=(128, 256), default=128)
    parser.add_argument('--startup-timeout', type=int, default=180)
    parser.add_argument('--require-pcid', action='store_true')
    parser.add_argument('--accel', choices=('tcg','whpx','kvm'), default='tcg')
    parser.add_argument('--cpu', help='explicit CPU model recorded in the actual QEMU command')
    parser.add_argument('--trace-usb', action='store_true', help='record actual QEMU USB endpoint/transfer diagnostics')
    parser.add_argument('--live-capture', action='store_true', help='run without stop; one final freeze and no resume for full audit')
    parser.add_argument('--selftest', action='store_true', help='host controls only; never starts QEMU')
    args = parser.parse_args()
    if args.selftest:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HostControls))
        return 0 if result.wasSuccessful() else 1
    if args.reuse_esp is None: parser.error('--reuse-esp is required; this runner never builds')
    check(1 <= args.startup_timeout <= 600, 'invalid startup deadline')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())

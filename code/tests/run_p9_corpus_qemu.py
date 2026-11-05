"""Run an archived P9 corpus ELF via normal runtime7 EXEC and capture external UART."""
from pathlib import Path
import argparse
import json
import re
import struct
import time

from tests import run_process_lifecycle_qemu as life
from tools.guest_corpus.log_transport import corpus_log


FILE_APP = 12
EXEC = 'exec /APP.ELF'
check = life.settings.check


def uart_streams(transcript):
    """Separate atomic P9 writes from shell text split across log syscalls."""
    records, control, cursor = [], [], 0
    for marker in re.finditer(rb'P9LOG1', transcript):
        check(len(records) < 258, 'too many P9 UART records')
        record = corpus_log.LINE.match(transcript, marker.start())
        check(record is not None and len(record[3]) <= 128, 'malformed or truncated P9 UART record')
        control.append(transcript[cursor:marker.start()])
        records.append(record[0])
        cursor = record.end()
    control.append(transcript[cursor:])
    capture = b''.join(records)
    corpus_log.decode(capture)
    return capture, b''.join(control)


def immutable_loads(payload):
    check(payload.startswith(b'\x7fELF\x02\x01\x01') and len(payload) >= 64,
          'corpus artifact is not little-endian ELF64')
    kind, machine = struct.unpack_from('<HH', payload, 16)
    headers = struct.unpack_from('<Q', payload, 32)[0]
    stride, count = struct.unpack_from('<HH', payload, 54)
    check(kind == 3 and machine == 62 and stride == 56 and 1 <= count <= 32
          and 64 <= headers <= len(payload) - count * stride, 'corpus ELF program headers differ')
    for index in range(count):
        kind, flags, offset, address, _, size, memory, _ = struct.unpack_from(
            '<IIQQQQQQ', payload, headers + index * stride)
        if kind != 1 or flags & 2:
            continue
        check(flags in (4, 5) and 0 < size <= memory <= len(payload) + 4096
              and offset <= len(payload) - size and address + memory < 0x10000000,
              'unbounded or unexpected immutable corpus ELF segment')
        yield address, payload[offset:offset + size], flags == 5


def live_payload(guest, slot, payload, cases):
    guest.refresh_processes()
    at = slot * life.PROCESS_BYTES
    ready, root = struct.unpack_from('<QQ', guest.processes, at)
    bias = struct.unpack_from('<Q', guest.processes, at + 224)[0]
    check(ready == 1 and root > 0 and root % 4096 == 0
          and 0x10000000 <= bias <= 0x1fff0000 and bias % 65536 == 0,
          'invalid live corpus process root or load bias')
    executable = []
    found_cases = False
    for address, data, code in immutable_loads(payload):
        first, end = bias + address, bias + address + len(data)
        for page in range(first & ~4095, (end + 4095) & ~4095, 4096):
            pte = guest.pte(root, page)
            check(pte & 0x8000000000000007 == 5 | (0 if code else life.NF),
                  'corpus executable or read-only user PTE differs')
        actual = guest.user(slot, first, len(data), 'loaded P9 immutable ELF segment')
        check(actual == data, 'live corpus segment differs from archived ELF')
        if code:
            executable.append((first, end))
        if cases in data:
            found_cases = True
    check(executable and found_cases, 'live code or immutable corpus cases missing')
    return dict(slot=slot, root=root, bias=bias, executable=executable, elf_sha256=corpus_log.sha(payload))


def syscall_return_ip(frame, image):
    words = struct.unpack('<25Q', frame)
    rip, root, count = words[15], words[18], words[22]
    if count and root == image['root'] and any(first + 2 <= rip < end for first, end in image['executable']):
        return rip
    return None


def terminal_exit(launch, wait, final, live):
    check(launch['token'] == wait['token'] == live['process']
          and launch['generation'] == wait['generation'] == final['generation'] == live['generation'],
          'EXEC, mapped process, WAIT and catalog identities differ')
    check((wait['state'], wait['status'], final['state'], final['status'], final['process']) == (3, 0, 3, 0, 0),
          'corpus process did not exit cleanly')
    return wait['status']


class CorpusGuest(life.ProcessGuest):
    def __init__(self, esp, disk, state):
        self._nvme_closed = False
        self.kernel_memory_layout = life.nvme.check_kernel_memory_layout(esp)
        life.settings.Guest.__init__(self, esp, disk, state, block_backend='virtio')

    def bootstrap_audit(self):
        # Other desktop processes may still be staging when desktop READY is sent.
        # Read only the retained kernel layout here and the target pool once live.
        acpi = life.settings.acpi
        self.symbols = acpi.validation_symbols(self.esp.parent / 'kernel.elf')
        markers = re.findall(rb'^memory_runtime_boot_info=0x([0-9a-f]{16})\r?$', self.raw, re.M)
        check(len(markers) == 1 and int(markers[0], 16) > acpi.HHDM, 'missing trusted BootInfo marker')
        self.boot = struct.unpack('<20Q', self.physical(int(markers[0], 16) - acpi.HHDM, 160, 'BootInfo'))

    def map_corpus(self, slot, payload, cases):
        check(type(slot) is int and 7 <= slot < 16, 'invalid launched file application slot')
        limits = self.kernel(self.ksym('user.memory', 'POOL_LIMITS'), 128, 'trusted private pool limits')
        self.pool_limits = list(struct.unpack('<16Q', limits))
        root = struct.unpack('<Q', self.kernel(self.ksym('user.memory', 'DYNAMIC_PHYSICAL') + slot * 8,
                                               8, 'file application held arena root'))[0]
        check(root != 0 and self.pool_limits[slot] == 32, 'unexpected file application private pool')
        image = live_payload(self, slot, payload, cases)
        check(image['root'] == root, 'corpus root differs from the allocated private pool')
        return image

    def run_corpus(self, payload, cases, result):
        self.resume()
        self.wait(b'DONGOS_P7_CLIENTS_READY', 90)
        self.pause()
        prior = self.catalog()['snapshots'][FILE_APP]
        offset = len(self.raw)
        check(b'P9LOG1' not in self.raw, 'unexpected corpus records before EXEC')
        result['exec_serial_offset'] = offset
        self.resume()
        self.uart.sendall(EXEC.encode('ascii') + b'\r')
        self.wait(b'P9LOG1 ', 90)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.pause()
            catalog = self.catalog()
            snapshot = catalog['snapshots'][FILE_APP]
            result['catalog_last'] = snapshot
            if snapshot['generation'] > prior['generation']:
                if snapshot['state'] in (1, 2) and snapshot['process']:
                    if 'mapped' not in result:
                        result['mapped'] = self.map_corpus(catalog['slots'][FILE_APP], payload, cases)
                        result['catalog_live'] = snapshot
                    image = result['mapped']
                    slot = image['slot']
                    check(catalog['slots'][FILE_APP] == slot and snapshot['process'] == result['catalog_live']['process'],
                          'file application identity changed before the user entry observation')
                    frame_at = self.ksym('user.memory', 'PROCESSES') + slot * life.PROCESS_BYTES + 16
                    frame = self.kernel(frame_at, 200, 'actual captured corpus user Frame')
                    rip = syscall_return_ip(frame, image)
                    # The production syscall entry saves the user RCX, root and
                    # syscall counter. Verify the instruction just before RCX.
                    if rip is not None and self.user(slot, rip - 2, 2, 'executed corpus SYSCALL') == b'\x0f\x05':
                        result['cpl3'] = dict(rip=rip, frame_hex=frame.hex(), instruction='0f05')
                        break
                else:
                    break
            check(self.process.poll() is None and b'PANIC' not in self.raw, 'guest failed during P9 EXEC')
            self.resume()
            time.sleep(.002)
        check('mapped' in result and 'cpl3' in result, 'no captured CPL3 syscall frame matched the corpus ELF')
        self.resume()
        last = f'P9LOG1 {len(cases) // 64 + 1:04x} '.encode('ascii')
        self.wait(last, 90)
        response = self.shell('wait ' + str(result['catalog_live']['process']), expected=b'WAIT OK')
        capture, control = uart_streams(bytes(self.raw[offset:]))
        launched = life.parse_record(control, 'EXEC OK', '/APP.ELF')
        result['launch'] = launched
        result['wait'] = life.parse_record(bytes.fromhex(response['response_hex']), 'WAIT OK')
        result['catalog_terminal'] = self.catalog()['snapshots'][FILE_APP]
        status = terminal_exit(launched, result['wait'], result['catalog_terminal'], result['catalog_live'])
        return status, capture


def run(esp, corpus, state, generation, expected_manifest):
    check(not state.exists() and state.is_relative_to(life.ROOT / 'build'), 'output must be new and under build/')
    state.mkdir(parents=True)
    result = dict(passed=False, guest_execution_scope='qemu-cpl3-corpus', generation=generation)
    guest = None
    try:
        metadata = life.verify_build(esp)
        check(metadata.get('runtime_level') == 7 and metadata.get('test') is False, 'normal runtime7 ESP required')
        life.settings.storage_profile(esp)
        payload = corpus_log.bounded(corpus / 'program.elf')
        cases = corpus_log.bounded(corpus / 'cases.bin')
        envelope = corpus_log.bounded(corpus / 'transport-manifest.json')
        check(corpus_log.sha(envelope) == expected_manifest, 'trusted transport manifest differs')
        manifest = corpus_log.bounded(corpus / 'manifest.json')
        check(corpus_log.sha(manifest) == json.loads(envelope)['manifest_sha256']
              and corpus_log.sha(payload) == json.loads(manifest)['elf_sha256'], 'staged ELF identity differs')
        result.update(transport_manifest_sha256=expected_manifest, elf_sha256=corpus_log.sha(payload),
                      build_inputs_sha256=life.settings.sha(esp.parent / 'build-inputs.json'))
        disk = state / 'data.img'
        seeded = life.seed_executable(disk, payload)
        check(seeded['payload_sha256'] == result['elf_sha256'], 'FAT payload identity differs')
        guest = CorpusGuest(esp, disk, state / 'boot')
        status, capture = guest.run_corpus(payload, cases, result)
        guest.close()
        result['guest'] = guest.evidence
        transcript = bytes(guest.raw[result['exec_serial_offset']:])
        guest = None
        check(uart_streams(transcript)[0] == capture, 'capture changed after guest shutdown')
        (state / 'p9.log').write_bytes(capture)
        result['transport_validation'] = corpus_log.verify_log(
            corpus, capture, expected_manifest_sha256=expected_manifest, generation=generation,
            exit_code=status, timed_out=False)
        disk_after = life.disk_oracle.inspect(disk, files=life.input_files(payload), exact_namespace=True)
        check(disk_after['image_sha256'] == seeded['raw']['image_sha256'], 'seeded FAT disk changed')
        life.verify_build(esp)
        check(result['guest']['actual_qemu_executed'] and result['guest']['qemu_stopped']
              and result['guest']['qemu_returncode'] == 0, 'actual QEMU execution/cleanup missing')
        result['passed'] = True
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        if guest is not None:
            try:
                guest.capture_failure()
            except Exception as capture_error:
                result['failure_capture_error'] = str(capture_error)
    finally:
        if guest is not None:
            try:
                guest.close()
                result['guest'] = guest.evidence
            except Exception as error:
                result.update(passed=False, cleanup_error=str(error))
        life.storage.write_json(state / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-esp', type=Path, required=True)
    parser.add_argument('--corpus-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    result = run(args.reuse_esp.resolve(), args.corpus_build.resolve(), args.output.resolve(),
                 args.generation, args.manifest_sha256)
    print(args.output / 'result.json', result.get('error', 'PASS'))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

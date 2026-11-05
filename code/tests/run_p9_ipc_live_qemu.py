"""Run an isolated echo fixture against the unchanged production IPC peer."""
from pathlib import Path
import argparse
import hashlib
import json
import re

from tests import run_process_lifecycle_qemu as life
from tests.run_virtio_reset_qemu import ResetGuest
from tools.make_fat32_disk import create


TARGET = 'services/apps/echo.dg'
FIXTURE = 'tests/p9_ipc_live_fixture.dg'
CALLER = 7
PEER = 10
SEED = 324508639
ECHO_MISMATCH = 0x09510003
MARKERS = (b'P9IPC1 PROBES PASS\r\n', b'P9IPC1 ECHO 32 PASS\r\n', b'P9IPC1 PEER GONE PASS\r\n')
TRACE = re.compile(rb'P9IPC1[^\r\n]*\r\n')
check = life.settings.check


def fixture_variant(raw, negative=False):
    if not negative:
        return raw
    anchor = b'RESPONSE.words[word]!=REQUEST.words[word]'
    check(raw.count(anchor) == 1, 'need one exact reply comparison')
    return raw.replace(anchor, b'RESPONSE.words[word]!=(REQUEST.words[word]^1)')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_source_delta(pristine, completed, replacement):
    check(pristine.keys() == completed.keys(), 'fixture changed the build input inventory')
    changed = [name for name in pristine if pristine[name] != completed[name]]
    check(changed == [TARGET] and completed[TARGET] == digest(replacement),
          'fixture does not contain exactly the declared echo replacement')


def extract_trace(serial):
    records = tuple(match[0] for match in TRACE.finditer(serial))
    control = TRACE.sub(b'', serial)
    check(b'P9IPC1' not in control, 'truncated P9 IPC marker')
    return records, control


def verify_trace(serial, negative=False):
    records, _ = extract_trace(serial)
    check(records == (MARKERS[:1] if negative else MARKERS), 'unexpected IPC proof markers or ordering')


def verify_terminal(launch, wait, catalog, config, state, status):
    identity = (launch['token'], launch['generation'])
    check((wait['token'], wait['generation']) == identity and (wait['state'], wait['status']) == (state, status),
          'WAIT identity or terminal result differs')
    snapshot = catalog['snapshots'][config]
    check((snapshot['process'], snapshot['generation'], snapshot['state'], snapshot['status'])
          == (0, launch['generation'], state, status), 'kernel catalog terminal result differs')
    events = [event for event in catalog['events'] if event['configuration'] == config
              and (event['process'], event['generation']) == identity and event['state'] in (3, 4, 5)]
    check(len(events) == 1 and (events[0]['state'], events[0]['status']) == (state, status),
          'missing exact kernel catalog terminal event')
    return events[0]


def exercise(guest, result, negative):
    guest.resume()
    guest.wait(b'DONGOS_P7_CLIENTS_READY', 90)
    guest.pause()

    def command(text, label, name=None):
        record = guest.shell(text)
        result['commands'].append(record)
        _, control = extract_trace(bytes.fromhex(record['response_hex']))
        return life.parse_record(control, label, name)

    peer = command('run ipc-peer 123', 'RUN OK', 'ipc-peer')
    peer_ready = guest.wait_state(PEER, 2)['snapshots'][PEER]
    check((peer_ready['process'], peer_ready['generation']) == (peer['token'], peer['generation']),
          'production peer is not READY for this run')
    result['peer_ready'] = peer_ready
    offset = len(guest.raw)
    result['trace_offset'] = offset
    caller = command('run echo ' + str(SEED), 'RUN OK', 'echo')
    waited = command('wait ' + str(caller['token']), 'WAIT OK')
    catalog = guest.catalog()
    result['caller_terminal'] = verify_terminal(caller, waited, catalog, CALLER, 3, ECHO_MISMATCH if negative else 0)
    check(catalog['snapshots'][CALLER]['argument'] == SEED, 'catalog caller seed differs')
    if negative:
        check(catalog['snapshots'][PEER] == peer_ready, 'peer unexpectedly changed during wrong-reply control')
    else:
        waited = command('wait ' + str(peer['token']), 'WAIT OK')
        result['peer_terminal'] = verify_terminal(peer, waited, guest.catalog(), PEER, 4, 6)
    verify_trace(bytes(guest.raw[offset:]), negative)


def run(esp, pristine_root, state, negative=False):
    check(not state.exists() and state.is_relative_to(life.ROOT / 'build'), 'output must be new and under build/')
    state.mkdir(parents=True)
    result = dict(passed=False, negative=negative, seed=SEED, commands=[])
    guest = None
    try:
        metadata = life.verify_build(esp)
        check('usb_only_profile' not in metadata, 'normal VirtIO-backed image required')
        completed = metadata['source_sha256']
        pristine = {name: digest((pristine_root / name).read_bytes()) for name in completed}
        replacement = fixture_variant((pristine_root / FIXTURE).read_bytes(), negative)
        verify_source_delta(pristine, completed, replacement)
        result.update(source_delta=[TARGET], fixture_sha256=digest(replacement),
                      build_manifest_sha256=life.settings.sha(esp.parent / 'build-inputs.json'),
                      peer_elf_sha256=life.settings.sha(esp.parent / 'services/ipc-peer/program.elf'),
                      echo_elf_sha256=life.settings.sha(esp.parent / 'services/echo/program.elf'))
        disk = state / 'data.img'
        create(disk, 64)
        before = life.settings.sha(disk)
        guest = ResetGuest(esp, disk, state / 'boot')
        exercise(guest, result, negative)
        guest.close()
        result['guest'] = guest.evidence
        guest = None
        serial = (state / 'boot/serial.log').read_bytes()
        verify_trace(serial[result['trace_offset']:], negative)
        result['serial_sha256'] = digest(serial)
        check(life.settings.sha(disk) == before, 'temporary disk changed')
        result['disk_sha256'] = before
        life.verify_build(esp)
        check(result['guest']['actual_qemu_executed'] and result['guest']['cleanup_completed']
              and result['guest']['qemu_returncode'] == 0, 'QEMU execution or cleanup missing')
        result['passed'] = True
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        if guest is not None:
            try:
                guest.capture_failure()
            except Exception as error:
                result['capture_error'] = str(error)
            try:
                guest.close()
            except Exception as error:
                result['cleanup_error'] = str(error)
            result['guest'] = guest.evidence
        life.storage.write_json(state / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-esp', required=True, type=Path)
    parser.add_argument('--pristine-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    result = run(args.reuse_esp.resolve(), args.pristine_root.resolve(), args.output.resolve(), args.negative)
    print(args.output / 'result.json', result.get('error', 'PASS'))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

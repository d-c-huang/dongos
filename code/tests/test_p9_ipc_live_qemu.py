"""Host-side evidence controls for the real IPC fixture runner."""
from pathlib import Path
import shutil
import tempfile
import unittest

from lang.dongc import compile_file
from tests import run_p9_ipc_live_qemu as runner


ROOT = Path(__file__).resolve().parents[1]


class LiveIpcControls(unittest.TestCase):
    def test_fixture_compiles_and_mutation_is_unique(self):
        source = ROOT / runner.FIXTURE
        raw = source.read_bytes()
        negative = runner.fixture_variant(raw, True)
        self.assertNotEqual(raw, negative)
        self.assertEqual(negative.count(b'!=(REQUEST.words[word]^1)'), 1)
        with self.assertRaises(ValueError):
            runner.fixture_variant(raw + raw, True)
        with tempfile.TemporaryDirectory() as path:
            staged = Path(path) / 'apps/echo.dg'
            staged.parent.mkdir()
            shutil.copytree(ROOT / 'services/lib', Path(path) / 'lib')
            for body in (raw, negative):
                staged.write_bytes(body)
                for mode in ('debug', 'release'):
                    compiled = compile_file(staged, roots=[Path(path)], mode=mode)
                    self.assertIn('service_main', compiled.assembly)

    def test_fixture_delta_is_exact(self):
        raw = b'fixture'
        original = {runner.TARGET: runner.digest(b'echo'), 'kernel/keep.dg': runner.digest(b'keep')}
        target = dict(original)
        target[runner.TARGET] = runner.digest(raw)
        runner.verify_source_delta(original, target, raw)
        with self.assertRaises(ValueError):
            runner.verify_source_delta(original, {runner.TARGET: target[runner.TARGET]}, raw)
        with self.assertRaises(ValueError):
            runner.verify_source_delta(original, dict(target, **{'kernel/keep.dg': 'changed'}), raw)
        with self.assertRaises(ValueError):
            runner.verify_source_delta(original, target, b'other fixture')

    def test_trace_recovers_split_shell_fields_and_rejects_bad_receipts(self):
        markers = runner.MARKERS
        serial = b'RUN OK ' + markers[0] + b'echo token=259\r\n' + b''.join(markers[1:])
        self.assertEqual(runner.extract_trace(serial), (markers, b'RUN OK echo token=259\r\n'))
        runner.verify_trace(serial)
        runner.verify_trace(markers[0], negative=True)
        for bad in (serial + markers[0], b''.join(markers[::-1]), b''.join(markers)[:-1],
                    markers[0] + b'P9IPC1 FORGED\r\n', b''.join(markers[:2])):
            with self.subTest(serial=bad), self.assertRaises(ValueError):
                runner.verify_trace(bad)

    def test_terminal_binds_shell_and_catalog(self):
        launch = dict(token=268, generation=2)
        wait = dict(launch, state=3, status=0)
        snapshots = [{} for _ in range(18)]
        snapshots[runner.CALLER] = dict(process=0, generation=2, state=3, status=0)
        event = dict(process=268, generation=2, configuration=runner.CALLER, state=3, status=0)
        catalog = dict(snapshots=snapshots, events=[event])
        self.assertEqual(runner.verify_terminal(launch, wait, catalog, runner.CALLER, 3, 0), event)
        for bad in (dict(wait, token=259), dict(wait, state=4), dict(wait, status=1)):
            with self.assertRaises(ValueError):
                runner.verify_terminal(launch, bad, catalog, runner.CALLER, 3, 0)
        with self.assertRaises(ValueError):
            runner.verify_terminal(launch, wait, dict(catalog, events=[event, event]), runner.CALLER, 3, 0)


if __name__ == '__main__':
    unittest.main()

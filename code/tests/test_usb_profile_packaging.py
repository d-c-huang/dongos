"""A USB-only receipt cannot hide a missing/changed shared service snapshot."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import build_usb
from tools import usb_only_profile as profile


class UsbProfilePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root/'build'
        self.esp = self.output/'esp'
        self.esp.mkdir(parents=True)
        source = self.root/'services'/profile.MODULE
        source.parent.mkdir(parents=True)
        source.write_bytes(profile.DEFAULT_BYTES)
        extra = self.root/'services/drivers/example.dg'
        extra.parent.mkdir()
        extra.write_text('module drivers.example;\n', encoding='utf-8')
        _, self.usb = profile.generate(self.output, source_root=self.root)
        # This unit fixture checks packaging provenance, not executable PE/ELF.
        payload = self.esp/'payload.fixture'
        payload.write_bytes(b'fixed packaging identity')
        self.metadata = dict(runtime_level=7, test=False, graphics_case=None,
                             source_unchanged=True,
                             source_sha256={p.relative_to(self.root).as_posix(): self.sha(p)
                                            for p in (source, extra)},
                             artifacts={str(payload): self.sha(payload)},
                             usb_only_profile=self.usb)
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save(self):
        (self.output/'build-inputs.json').write_text(json.dumps(self.metadata), encoding='utf-8')

    def verify(self):
        with patch.object(build_usb, 'ROOT', self.root):
            return build_usb.verify_build(self.esp)

    def test_valid_default_and_usb_only_builds_keep_distinct_receipts(self):
        self.assertEqual(self.verify()['usb_only_profile'], self.usb)
        del self.metadata['usb_only_profile']
        self.save()
        self.assertNotIn('usb_only_profile', self.verify())

    def test_unchanged_artifacts_cannot_mask_changed_or_missing_snapshot(self):
        staged = self.output/profile.DIRECTORY/profile.MODULE
        staged.write_bytes(profile.DEFAULT_BYTES)
        with self.assertRaises(ValueError):
            self.verify()
        staged.write_bytes(profile.USB_BYTES)
        extra = self.output/profile.DIRECTORY/'drivers/example.dg'
        extra.write_text('module drivers.example;\npub const BAD:u64=1;\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.verify()
        extra.unlink()
        with self.assertRaises(ValueError):
            self.verify()

    def test_malformed_profile_receipt_fails_closed(self):
        for value in (None, {}, dict(self.usb, usb_only=False), dict(self.usb, fat_audit_bytes=True)):
            with self.subTest(value=value):
                self.metadata['usb_only_profile'] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_cli_usb_only_cannot_relabel_an_ordinary_reused_esp(self):
        del self.metadata['usb_only_profile']
        self.save()
        argv = ['build_usb', '--esp', str(self.esp), '--usb-only',
                '--output', str(self.root/'refused.img')]
        with patch.object(build_usb, 'ROOT', self.root), patch('sys.argv', argv), \
             patch.object(build_usb, 'create') as create:
            with self.assertRaises(ValueError):
                build_usb.main()
            create.assert_not_called()


if __name__ == '__main__':
    unittest.main()

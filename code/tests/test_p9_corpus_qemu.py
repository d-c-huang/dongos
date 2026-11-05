"""Host controls for guest UART, loaded ELF and lifecycle evidence."""
import struct
import unittest

from tests import run_p9_corpus_qemu as runner
from tests.test_corpus_log import wire


class CorpusGuestControls(unittest.TestCase):
    def test_external_uart_extracts_complete_exclusive_lines(self):
        raw = bytes(range(128))
        records = wire(raw)
        first, tail = records.split(b'\n', 1)
        transcript = b'EXEC OK ' + first + b'\n/APP.ELF\r\n> ' + tail
        self.assertEqual(runner.uart_streams(transcript), (records, b'EXEC OK /APP.ELF\r\n> '))
        for bad in (b'no protocol', records[:-1], b'P9LOG1 forged\n' + records,
                    first + b'\n' + tail + tail, first + b'\n' + tail[80:]):
            with self.subTest(transcript=bad), self.assertRaises(ValueError):
                runner.uart_streams(bad)

    def test_loaded_elf_identity_and_user_permissions(self):
        image = bytearray(0x2200)
        image[:7] = b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HH', image, 16, 3, 62)
        struct.pack_into('<Q', image, 32, 64)
        struct.pack_into('<HH', image, 54, 56, 2)
        struct.pack_into('<IIQQQQQQ', image, 64, 1, 5, 0x1000, 0x1000, 0, 8, 8, 4096)
        struct.pack_into('<IIQQQQQQ', image, 120, 1, 4, 0x2000, 0x2000, 0, 8, 8, 4096)
        image[0x1000:0x1008] = b'EXECUTED'
        image[0x2000:0x2008] = b'P9CASES!'

        class Guest:
            def refresh_processes(self):
                self.processes = bytearray(runner.life.PROCESS_BYTES)
                struct.pack_into('<QQ', self.processes, 0, 1, 0x2000)
                struct.pack_into('<Q', self.processes, 224, 0x10000000)

            def pte(self, root, page):
                return 5 | (runner.life.NF if page == 0x10002000 else 0)

            def user(self, slot, address, length, role):
                offset = address - 0x10000000
                return bytes(image[offset:offset + length])

        archived = bytes(image)
        live = runner.live_payload(Guest(), 0, archived, b'P9CASES!')
        self.assertEqual(live['executable'], [(0x10001000, 0x10001008)])
        image[0x1000] ^= 1
        with self.assertRaisesRegex(ValueError, 'segment differs'):
            runner.live_payload(Guest(), 0, archived, b'P9CASES!')
        with self.assertRaises(ValueError):
            list(runner.immutable_loads(archived[:80]))

    def test_cpl3_registers_and_exit_are_bound_to_process(self):
        image = dict(root=0x2000, executable=[(0x10001000, 0x10001008)])
        words = [0] * 25
        words[15], words[18], words[22] = 0x10001005, 0x2000, 1
        self.assertEqual(runner.syscall_return_ip(struct.pack('<25Q', *words), image), 0x10001005)
        for index, value in ((15, 0x10002000), (18, 0x3000), (22, 0)):
            changed = words.copy()
            changed[index] = value
            self.assertIsNone(runner.syscall_return_ip(struct.pack('<25Q', *changed), image))
        launch = dict(token=259, generation=2)
        wait = dict(launch, state=3, status=0)
        live = dict(process=259, generation=2)
        final = dict(process=0, generation=2, state=3, status=0)
        self.assertEqual(runner.terminal_exit(launch, wait, final, live), 0)
        for bad in (dict(wait, token=515), dict(wait, generation=3), dict(wait, status=1)):
            with self.assertRaises(ValueError):
                runner.terminal_exit(launch, bad, final, live)


if __name__ == '__main__':
    unittest.main()

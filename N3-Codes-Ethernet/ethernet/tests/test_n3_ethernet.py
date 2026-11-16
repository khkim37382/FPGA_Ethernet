import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "multi_fpga_receiver"))
from src.n3_records import decode_records
from src.packet import PacketError, decode_packet, encode_packet
from src.receiver import Receiver


class N3EthernetTests(unittest.TestCase):
    def receiver(self, temp):
        config = Path(temp) / "config.json"
        config.write_text(json.dumps({
            "computer": {"bind_ip": "127.0.0.1", "udp_port": 5000},
            "fpgas": [{"id": i, "ip": f"192.168.1.{100+i}"} for i in range(1, 13)]}))
        result = Receiver(str(config), log_directory=str(Path(temp) / "logs"), quiet=True)
        for state in result.router.states.values():
            state.expected_ip = "127.0.0.1"
        return result

    def test_twelve_concurrent_c_senders_preserve_full_records_and_logs(self):
        with tempfile.TemporaryDirectory() as temp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
            sock.bind(("127.0.0.1", 0))
            sock.settimeout(3)
            receiver = self.receiver(temp)
            expected = {}
            jobs = []
            for board in range(1, 13):
                # All 160 bits matter, including embedded LF CR and nonzero MSBs.
                payload = b"".join(struct.pack("!Q", n * 1000 + board) +
                                   bytes([0xe0, board, 10, 13]) + n.to_bytes(16, "big")
                                   for n in range(101))
                expected[board] = payload
                source = Path(temp) / f"source_{board}.bin"
                source.write_bytes(payload)
                jobs.append(subprocess.Popen([str(ROOT / "build/n3_udp_sender"), "--input", str(source),
                    "--id", str(board), "--dest", "127.0.0.1", "--port", str(sock.getsockname()[1]),
                    "--sequence", str(0xfffffffe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            received = {i: {} for i in range(1, 13)}
            try:
                for _ in range(36):
                    data, address = sock.recvfrom(65535)
                    packet = decode_packet(data)
                    self.assertEqual(packet.packet_type, 2)
                    records = decode_records(packet.payload)
                    self.assertEqual(packet.timestamp, records[0].timestamp)
                    received[packet.fpga_id][packet.sequence_number] = bytes(packet.payload)
                    self.assertTrue(receiver.process_datagram(data, address))
                for job in jobs:
                    out, err = job.communicate(timeout=3)
                    self.assertEqual(job.returncode, 0, (out, err))
                for board, state in receiver.router.states.items():
                    self.assertEqual(state.packets_received, 3)
                    self.assertEqual(state.packets_lost, 0)
                    self.assertEqual(b"".join(received[board][seq] for seq in (0xfffffffe, 0xffffffff, 0)), expected[board])
            finally:
                receiver.logger.close()
                for job in jobs:
                    if job.poll() is None:
                        job.kill()
                    job.communicate()
            for board, payload in expected.items():
                self.assertEqual((Path(temp) / "logs" / f"fpga_{board:02d}.bin").read_bytes(), payload)

    def test_rtl_to_c_to_python_byte_order(self):
        source = ROOT / "build/rtl_records.bin"
        self.assertTrue(source.exists(), "run make test to generate the RTL trace first")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0)); sock.settimeout(3)
            subprocess.run([str(ROOT / "build/n3_udp_sender"), "--id", "7", "--dest", "127.0.0.1",
                            "--port", str(sock.getsockname()[1]), "--input", str(source)], check=True, capture_output=True)
            packet = decode_packet(sock.recv(65535))
        records = decode_records(packet.payload)
        self.assertEqual(len(records), 5)
        self.assertEqual([r.tag for r in records], [0x20, 0x80, 0xe0, 0xe1, 0x20])
        self.assertEqual([int.from_bytes(r.raw[1:], "big") for r in records], [1, 2, 3, 4, 5])
        self.assertEqual(bytes(packet.payload), source.read_bytes())
        converted = subprocess.run([str(ROOT / "build/test_n3_word_order"),
                                    str(ROOT / "build/rtl_mmio_words.bin")], check=True, capture_output=True)
        self.assertEqual(converted.stdout, source.read_bytes())

    def test_reject_bad_n3_size_and_bad_crc_before_routing(self):
        with tempfile.TemporaryDirectory() as temp:
            receiver = self.receiver(temp)
            try:
                for payload in (b"", bytes(27), bytes(29), bytes(1428)):
                    self.assertFalse(receiver.process_datagram(encode_packet(1, 0, 0, payload, packet_type=2), ("127.0.0.1", 1)))
                valid = bytearray(encode_packet(1, 0, 0, bytes(28), packet_type=2))
                valid[-1] ^= 1
                self.assertFalse(receiver.process_datagram(valid, ("127.0.0.1", 1)))
                self.assertEqual(receiver.router.states[1].packets_received, 0)
                self.assertFalse(receiver.process_datagram(encode_packet(1, 0, 1, bytes(28), packet_type=2), ("127.0.0.1", 1)))
                with self.assertRaises(PacketError):
                    decode_records(bytes(29))
            finally:
                receiver.logger.close()

    def test_truncated_replay_and_invalid_board_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "truncated.bin"
            source.write_bytes(bytes(27))
            for board in ("0", "13", "1"):
                result = subprocess.run([str(ROOT / "build/n3_udp_sender"), "--input", str(source),
                    "--id", board, "--dest", "127.0.0.1"], capture_output=True)
                self.assertNotEqual(result.returncode, 0)

    def test_legacy_export_preserves_binary_delimiters_inside_word(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output, legacy = [Path(temp) / name for name in ("input.bin", "out.csv", "legacy.bin")]
            word = b"\xe0\n\r" + bytes(range(17))
            source.write_bytes(struct.pack("!Q20s", 50000000, word))
            subprocess.run([sys.executable, str(ROOT / "decode_n3_log.py"), str(source), str(output),
                            "--legacy-output", str(legacy)], check=True)
            self.assertEqual(legacy.read_bytes(), word + b"\n\r")
            self.assertIn("1.000000000", output.read_text())

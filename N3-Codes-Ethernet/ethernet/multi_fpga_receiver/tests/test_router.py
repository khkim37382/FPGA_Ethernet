import unittest
import time

from src.packet import decode_packet, encode_packet
from src.router import FpgaRouter


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = FpgaRouter({i: f"192.168.1.{100+i}" for i in range(1, 13)}, 3)

    def test_interleaved_twelve_streams_are_independent(self):
        for sequence in range(3):
            for fpga_id in (1, 7, 2, 12, 4, 9, 3, 10, 5, 11, 6, 8):
                p = decode_packet(encode_packet(fpga_id, sequence, sequence, bytes([fpga_id])))
                self.router.route(p, f"192.168.1.{100+fpga_id}")
        for fpga_id, state in self.router.states.items():
            self.assertEqual(state.packets_received, 3)
            self.assertEqual(bytes(state.payload_buffer[-1]), bytes([fpga_id]))

    def test_loss_duplicate_out_of_order_and_bounded_buffer(self):
        state = self.router.states[1]
        for seq in (100, 101, 104, 104, 103, 105, 106):
            self.router.route(decode_packet(encode_packet(1, seq, 0, b"x")), "192.168.1.101")
        self.assertEqual(state.packets_lost, 2)
        self.assertEqual(state.duplicates, 1)
        self.assertEqual(state.out_of_order, 1)
        self.assertEqual(len(state.payload_buffer), 3)
        self.assertGreater(state.application_drops, 0)

    def test_mismatched_source_is_recorded_but_stream_is_routed_by_id(self):
        self.router.route(decode_packet(encode_packet(5, 0, 0, b"x")), "192.168.1.109")
        self.assertEqual(self.router.states[5].packets_received, 1)
        self.assertEqual(self.router.states[5].ip_mismatches, 1)

    def test_offline_and_high_rate_state_accounting(self):
        state = self.router.states[2]
        now = time.monotonic()
        for sequence in range(10_000):
            state.accept(sequence, sequence, memoryview(b"1234"), now)
        self.assertEqual(state.packets_received, 10_000)
        self.assertTrue(state.active(2.0, now + 1.9))
        self.assertFalse(state.active(2.0, now + 2.1))

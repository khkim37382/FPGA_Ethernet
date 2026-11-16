import unittest

from src.packet import HEADER_SIZE, PacketError, decode_packet, encode_packet


class PacketTests(unittest.TestCase):
    def test_round_trip(self):
        raw = encode_packet(12, 99, 123456789, b"\x01\x02")
        packet = decode_packet(raw)
        self.assertEqual((packet.fpga_id, packet.sequence_number, packet.timestamp, bytes(packet.payload)),
                         (12, 99, 123456789, b"\x01\x02"))
        self.assertEqual(HEADER_SIZE, 26)

    def test_invalid_magic_id_length_and_crc_rejected(self):
        raw = bytearray(encode_packet(1, 0, 0, b"abc"))
        raw[0] ^= 1
        with self.assertRaises(PacketError): decode_packet(raw)
        with self.assertRaises(PacketError): encode_packet(13, 0, 0, b"")
        with self.assertRaises(PacketError): decode_packet(encode_packet(1, 0, 0, b"abc")[:-1])
        raw = bytearray(encode_packet(1, 0, 0, b"abc")); raw[-1] ^= 1
        with self.assertRaises(PacketError): decode_packet(raw)

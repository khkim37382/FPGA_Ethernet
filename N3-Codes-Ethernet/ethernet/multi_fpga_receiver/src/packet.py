"""Version 1 wire protocol for the multi-FPGA UDP receiver.

All multi-byte integers are unsigned and network byte order (big-endian).
The CRC is CRC-32/IEEE over header bytes 0..21 followed by payload bytes.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

MAGIC = 0x46504741  # ASCII "FPGA"
VERSION = 1
PACKET_TYPE_SAMPLES_U16 = 1
HEADER_WITHOUT_CRC_FORMAT = "!IBBBBIQH"
HEADER_FORMAT = "!IBBBBIQHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 26 bytes
MAX_PAYLOAD = 65_507 - HEADER_SIZE


class PacketError(ValueError):
    pass


@dataclass(frozen=True)
class FpgaPacket:
    fpga_id: int
    packet_type: int
    sequence_number: int
    timestamp: int
    payload: memoryview
    flags: int = 0


def encode_packet(fpga_id: int, sequence_number: int, timestamp: int, payload: bytes,
                  packet_type: int = PACKET_TYPE_SAMPLES_U16, flags: int = 0) -> bytes:
    if not 1 <= fpga_id <= 12:
        raise PacketError("FPGA ID must be in range 1..12")
    if len(payload) > MAX_PAYLOAD:
        raise PacketError(f"payload exceeds UDP maximum ({MAX_PAYLOAD} bytes)")
    prefix = struct.pack(HEADER_WITHOUT_CRC_FORMAT, MAGIC, VERSION, fpga_id, packet_type,
                         flags & 0xFF, sequence_number & 0xFFFFFFFF,
                         timestamp & 0xFFFFFFFFFFFFFFFF, len(payload))
    crc = zlib.crc32(prefix)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return prefix + struct.pack("!I", crc) + payload


def decode_packet(datagram: bytes | bytearray | memoryview) -> FpgaPacket:
    view = memoryview(datagram)
    if len(view) < HEADER_SIZE:
        raise PacketError(f"packet shorter than {HEADER_SIZE}-byte header")
    magic, version, fpga_id, packet_type, flags, sequence, timestamp, payload_length, crc = (
        struct.unpack_from(HEADER_FORMAT, view)
    )
    if magic != MAGIC:
        raise PacketError(f"bad magic 0x{magic:08x}")
    if version != VERSION:
        raise PacketError(f"unsupported protocol version {version}")
    if not 1 <= fpga_id <= 12:
        raise PacketError(f"invalid FPGA ID {fpga_id}")
    if payload_length > MAX_PAYLOAD or len(view) != HEADER_SIZE + payload_length:
        raise PacketError(f"payload length {payload_length} does not match datagram length {len(view)}")
    payload = view[HEADER_SIZE:]
    calculated = zlib.crc32(view[:HEADER_SIZE - 4])
    calculated = zlib.crc32(payload, calculated) & 0xFFFFFFFF
    if calculated != crc:
        raise PacketError("CRC-32 mismatch")
    return FpgaPacket(fpga_id, packet_type, sequence, timestamp, payload, flags)


def decode_u16_samples(payload: memoryview) -> tuple[int, ...]:
    if len(payload) % 2:
        raise PacketError("uint16 sample payload has odd byte length")
    return struct.unpack(f"!{len(payload) // 2}H", payload)

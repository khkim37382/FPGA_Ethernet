"""Type 2 payload: whole {uint64 clock ticks, 160-bit N3 word} records, big endian."""
from dataclasses import dataclass
import struct

from .packet import PacketError

PACKET_TYPE_N3 = 2
RECORD_SIZE = 28
CLOCK_HZ = 50_000_000


@dataclass(frozen=True)
class N3Record:
    timestamp: int
    raw: bytes

    @property
    def tag(self) -> int:
        return self.raw[0]


def validate_payload(payload: bytes | memoryview) -> None:
    if not payload or len(payload) % RECORD_SIZE or len(payload) > 1400:
        raise PacketError("N3 payload must contain 1..50 whole 28-byte records")


def decode_records(payload: bytes | memoryview) -> tuple[N3Record, ...]:
    validate_payload(payload)
    return tuple(N3Record(ticks, raw) for ticks, raw in struct.iter_unpack("!Q20s", payload))

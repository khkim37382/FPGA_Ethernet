from __future__ import annotations

import math
import socket
import struct
import time

from src.packet import PACKET_TYPE_SAMPLES_U16, encode_packet


class SimulatedFpga:
    def __init__(self, fpga_id: int, destination: tuple[str, int], rate: float, samples_per_packet: int,
                 drop_every: int = 0, malformed_every: int = 0, stop_after: float = 0.0) -> None:
        self.fpga_id = fpga_id
        self.destination, self.rate, self.samples_per_packet = destination, rate, samples_per_packet
        self.drop_every, self.malformed_every, self.stop_after = drop_every, malformed_every, stop_after
        self.sequence = 0
        self.clock = 0
        self.sent = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def make_payload(self) -> bytes:
        # Distinct deterministic sine-like uint16 values for each FPGA.
        values = [int(32768 + 30000 * math.sin((self.clock + i) / 30 + self.fpga_id))
                  for i in range(self.samples_per_packet)]
        self.clock += self.samples_per_packet
        return struct.pack(f"!{len(values)}H", *values)

    def send_one(self) -> None:
        self.sequence = (self.sequence + 1) & 0xFFFFFFFF
        if self.drop_every and self.sequence % self.drop_every == 0:
            return  # Intentional sequence gap: packet is never placed on wire.
        data = encode_packet(self.fpga_id, self.sequence, self.clock, self.make_payload(), PACKET_TYPE_SAMPLES_U16)
        if self.malformed_every and self.sequence % self.malformed_every == 0:
            data = data[:-1]
        self.socket.sendto(data, self.destination)
        self.sent += 1

    def close(self) -> None:
        self.socket.close()

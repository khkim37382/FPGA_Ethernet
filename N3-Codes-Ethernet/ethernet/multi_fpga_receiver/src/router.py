from __future__ import annotations

import logging
import time
from .fpga_state import FpgaState
from .packet import FpgaPacket, PACKET_TYPE_SAMPLES_U16, decode_u16_samples


class FpgaRouter:
    def __init__(self, configured_ips: dict[int, str], buffer_packets: int, decode_samples: bool = False) -> None:
        self.states = {fpga_id: FpgaState(fpga_id, ip, buffer_packets) for fpga_id, ip in configured_ips.items()}
        self.ip_warnings = 0
        self._warned_mismatches: set[int] = set()
        self.decode_samples = decode_samples

    def route(self, packet: FpgaPacket, source_ip: str) -> FpgaState:
        state = self.states[packet.fpga_id]
        if source_ip != state.expected_ip:
            state.ip_mismatches += 1
            self.ip_warnings += 1
            # Local simulation intentionally shares 127.0.0.1. Warn once per
            # board so a sustained mismatch remains visible without flooding.
            if packet.fpga_id not in self._warned_mismatches:
                logging.warning("FPGA %d claims source %s; expected %s", packet.fpga_id, source_ip, state.expected_ip)
                self._warned_mismatches.add(packet.fpga_id)
        last_sample = None
        if self.decode_samples and packet.packet_type == PACKET_TYPE_SAMPLES_U16 and len(packet.payload) >= 2:
            last_sample = decode_u16_samples(packet.payload)[-1]
        state.accept(packet.sequence_number, packet.timestamp, packet.payload, time.monotonic(), last_sample)
        return state

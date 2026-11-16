from __future__ import annotations

import sys
import time
from .fpga_state import FpgaState


def render(states: dict[int, FpgaState], timeout: float, malformed: int, ip_warnings: int,
           show_samples: bool = False) -> None:
    now = time.monotonic()
    lines = ["Multi-FPGA UDP receiver  (Ctrl-C to stop)",
             "ID  IP               STATUS   PPS       Mbps   RX PACKETS     LOST  OOO DUP BUF" + (" SAMPLE" if show_samples else ""),]
    total_pps = total_mbps = 0.0
    for fpga_id, state in states.items():
        pps, mbps = state.rates(now)
        total_pps += pps
        total_mbps += mbps
        status = "ACTIVE " if state.active(timeout, now) else "OFFLINE"
        line = (
            f"{fpga_id:2d}  {state.expected_ip:15s}  {status} {pps:7.0f}  {mbps:8.3f}  "
            f"{state.packets_received:11d} {state.packets_lost:8d} {state.out_of_order:3d} "
            f"{state.duplicates:3d} {len(state.payload_buffer):3d}"
        )
        lines.append(line + (f" {state.latest_sample if state.latest_sample is not None else '-'}" if show_samples else ""))
    lines.append(f"Total: {total_pps:.0f} packets/s, {total_mbps:.3f} Mbps | Rejected malformed: {malformed} | source-IP warnings: {ip_warnings}")
    sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(lines) + "\n")
    sys.stdout.flush()

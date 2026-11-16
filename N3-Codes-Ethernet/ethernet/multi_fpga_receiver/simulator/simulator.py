#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from simulator.simulated_fpga import SimulatedFpga


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate 1..12 FPGA UDP senders on one host")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--fpgas", type=int, default=12, choices=range(1, 13))
    parser.add_argument("--rate", type=float, default=100.0, help="packets/sec per FPGA")
    parser.add_argument("--samples-per-packet", type=int, default=256)
    parser.add_argument("--duration", type=float, default=0.0, help="0 runs until Ctrl-C")
    parser.add_argument("--drop-every", type=int, default=0, help="skip every Nth sequence on each FPGA")
    parser.add_argument("--malformed-every", type=int, default=0, help="truncate every Nth packet")
    parser.add_argument("--stop-fpga", type=int, choices=range(1, 13), help="FPGA to stop early")
    parser.add_argument("--stop-after", type=float, default=0.0, help="seconds before --stop-fpga stops")
    args = parser.parse_args()
    if args.stop_after and not args.stop_fpga:
        parser.error("--stop-after requires --stop-fpga")
    devices = [SimulatedFpga(i, (args.host, args.port), args.rate, args.samples_per_packet,
                             args.drop_every, args.malformed_every,
                             args.stop_after if i == args.stop_fpga else 0.0)
               for i in range(1, args.fpgas + 1)]
    interval, next_send, started = 1.0 / args.rate, time.monotonic(), time.monotonic()
    try:
        while args.duration <= 0 or time.monotonic() - started < args.duration:
            now = time.monotonic()
            if now < next_send:
                time.sleep(min(next_send - now, 0.005))
                continue
            elapsed = now - started
            for device in devices:
                if not device.stop_after or elapsed < device.stop_after:
                    device.send_one()
            next_send += interval
            if next_send < now - interval:
                next_send = now + interval
    except KeyboardInterrupt:
        pass
    finally:
        for device in devices:
            device.close()
    print("Simulator stopped; packets sent: " + ", ".join(f"{d.fpga_id}={d.sent}" for d in devices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

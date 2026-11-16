from __future__ import annotations

import argparse
import logging
import signal
import socket
import threading
import time

from .config import load_config
from .dashboard import render
from .logger import StreamLogger
from .packet import PacketError, decode_packet
from .router import FpgaRouter
from .n3_records import PACKET_TYPE_N3, validate_payload


class Receiver:
    """One UDP socket, one parser/router, and twelve independent stream states."""
    def __init__(self, config_path: str, *, log_directory: str | None = None, quiet: bool = False,
                 socket_buffer: int = 8 * 1024 * 1024, decode_samples: bool = False) -> None:
        self.config = load_config(config_path)
        self.router = FpgaRouter(self.config.fpgas, self.config.buffer_packets, decode_samples)
        self.logger = StreamLogger(log_directory or "logs", log_directory is not None)
        self.quiet = quiet
        self.socket_buffer = socket_buffer
        self.running = True
        self.malformed_packets = 0
        self.total_datagrams = 0
        self.decode_samples = decode_samples

    def stop(self, *_: object) -> None:
        self.running = False

    def process_datagram(self, data: bytes, address: tuple[str, int]) -> bool:
        self.total_datagrams += 1
        try:
            packet = decode_packet(data)
            if packet.packet_type == PACKET_TYPE_N3:
                validate_payload(packet.payload)
                if packet.timestamp != int.from_bytes(packet.payload[:8], "big"):
                    raise PacketError("N3 header timestamp does not match the first record")
        except PacketError as exc:
            self.malformed_packets += 1
            logging.warning("Rejected packet from %s: %s", address[0], exc)
            return False
        state = self.router.route(packet, address[0])
        self.logger.write(packet.fpga_id, packet.payload, packet.sequence_number, address[0], state.packets_lost)
        return True

    def run(self, duration: float = 0.0, dashboard_interval: float = 0.5) -> int:
        # Unit tests and embedding can run a receiver on a worker thread.
        # POSIX only permits signal handler installation from the main thread.
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.socket_buffer)
        sock.bind((self.config.bind_ip, self.config.udp_port))
        sock.settimeout(0.1)
        actual_buffer = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        logging.info("Listening on %s:%d (socket receive buffer %d bytes)", self.config.bind_ip, self.config.udp_port, actual_buffer)
        end = None if duration <= 0 else time.monotonic() + duration
        last_dashboard = 0.0
        try:
            while self.running and (end is None or time.monotonic() < end):
                try:
                    data, address = sock.recvfrom(65_535)
                    self.process_datagram(data, address)
                except socket.timeout:
                    pass
                now = time.monotonic()
                if not self.quiet and now - last_dashboard >= dashboard_interval:
                    render(self.router.states, self.config.offline_timeout_seconds,
                           self.malformed_packets, self.router.ip_warnings, self.decode_samples)
                    last_dashboard = now
        finally:
            sock.close()
            self.logger.close()
        if not self.quiet:
            render(self.router.states, self.config.offline_timeout_seconds, self.malformed_packets, self.router.ip_warnings, self.decode_samples)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Receive and demultiplex up to 12 FPGA UDP streams")
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument("--log-dir", help="enable per-FPGA binary and CSV metadata logs in this directory")
    parser.add_argument("--duration", type=float, default=0.0, help="stop after seconds; 0 means run until Ctrl-C")
    parser.add_argument("--quiet", action="store_true", help="disable live terminal dashboard")
    parser.add_argument("--socket-buffer", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--decode-samples", action="store_true", help="show the latest uint16 type-1 sample per FPGA")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    return Receiver(args.config, log_directory=args.log_dir, quiet=args.quiet,
                    socket_buffer=args.socket_buffer, decode_samples=args.decode_samples).run(args.duration)


if __name__ == "__main__":
    raise SystemExit(main())

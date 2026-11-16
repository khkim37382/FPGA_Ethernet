"""Create a clearly simulated N3 replay and verify one board's received smoke test.

Uses Python's standard library only. Does not access FPGA hardware or network.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import struct


def create(path):
    # Five valid SR-counter-format words: indices 0..4, simulated counts 10..14.
    # Timestamps are synthetic 50 MHz ticks, not physical FPGA measurements.
    records = b"".join(
        struct.pack("!Q", index * 1000)
        + ((0x20 << 152) | (index << 12) | (10 + index)).to_bytes(20, "big")
        for index in range(5)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != records:
            raise ValueError(f"refusing to replace a different file: {path}")
    else:
        path.write_bytes(records)
    print(f"SIMULATED fixture: 5 records / 140 bytes: {path}")
    print(f"SHA256 {hashlib.sha256(records).hexdigest()}")


def verify(expected, capture, metadata, source_ip):
    original, received = expected.read_bytes(), capture.read_bytes()
    if not original or len(original) % 28:
        raise ValueError("expected fixture must contain complete 28-byte records")
    if original != received:
        raise ValueError(f"payload mismatch: expected {len(original)} bytes, received {len(received)}")
    with metadata.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    # The documented five-record replay uses batch=50 and a fresh sequence=0.
    if len(original) != 140 or len(rows) != 1:
        raise ValueError("expected one fresh five-record smoke-test datagram")
    row = rows[0]
    if (row["fpga_id"], row["sequence_number"], row["payload_size"],
            row["source_ip"], row["packets_lost"]) != ("1", "0", "140", source_ip, "0"):
        raise ValueError("unexpected board ID, sequence, payload size, source IP or loss count")
    print("PASS: all 5 simulated records / 140 bytes match exactly")
    print(f"PASS: 1 datagram, board 1, sequence 0, source {source_ip}, reported gaps 0")
    print("This verifies replay transport only; it does not verify FPGA/UIO/DUT acquisition.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    make = actions.add_parser("create", help="write deterministic simulated SR records")
    make.add_argument("output", type=Path)
    check = actions.add_parser("verify", help="compare a completed fresh receiver session")
    check.add_argument("--expected", type=Path, required=True)
    check.add_argument("--capture", type=Path, required=True)
    check.add_argument("--metadata", type=Path, required=True)
    check.add_argument("--source-ip", default="192.168.50.2")
    args = parser.parse_args()
    try:
        if args.action == "create":
            create(args.output)
        else:
            verify(args.expected, args.capture, args.metadata, args.source_ip)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")


if __name__ == "__main__":
    main()

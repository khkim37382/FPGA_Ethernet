"""Export one board's type-2 payload log to CSV and optional legacy N3 bytes."""
import argparse
import csv
from pathlib import Path
import struct

from multi_fpga_receiver.src.n3_records import CLOCK_HZ, RECORD_SIZE
from n3_analysis import FIELD_NAMES, VARIANTS, decode_fields


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--legacy-output", type=Path, help="20 N3 bytes followed by LF CR, as in xmit_mux")
    parser.add_argument("--variant", choices=sorted(VARIANTS), help="also decode fields using this board's source-defined widths")
    args = parser.parse_args()
    paths = [args.input.resolve(), args.output_csv.resolve()]
    if args.legacy_output:
        paths.append(args.legacy_output.resolve())
    if len(set(paths)) != len(paths):
        parser.error("input and output paths must differ")
    if args.input.stat().st_size % RECORD_SIZE:
        parser.error("input is not a whole number of 28-byte N3 records")
    legacy = args.legacy_output.open("wb") if args.legacy_output else None
    try:
        with args.input.open("rb") as source, args.output_csv.open("w", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["fpga_clock_ticks", "seconds_since_fpga_reset", "tag_hex", "n3_word_hex"] + (FIELD_NAMES if args.variant else []))
            while record := source.read(RECORD_SIZE):
                ticks, raw = struct.unpack("!Q20s", record)
                fields = decode_fields(raw, args.variant) if args.variant else {}
                writer.writerow([ticks, f"{ticks / CLOCK_HZ:.9f}", f"{raw[0]:02x}", raw.hex()] +
                                ([fields.get(name, "") for name in FIELD_NAMES] if args.variant else []))
                if legacy:
                    legacy.write(raw + b"\n\r")
    finally:
        if legacy:
            legacy.close()


if __name__ == "__main__":
    main()

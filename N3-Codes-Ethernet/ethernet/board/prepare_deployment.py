"""Prepare per-board identities and network files without touching a board."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = {v["name"] for v in json.loads((HERE.parent / "variants.json").read_text())}


def generate(output, variant, assignments=None):
    if variant not in VARIANTS:
        raise ValueError("unknown DE10 variant")
    assignments = assignments or {}
    if any(int(i) not in range(1, 13) or v not in VARIANTS for i, v in assignments.items()):
        raise ValueError("assignments must map IDs 1..12 to known DE10 variants")
    boards = []
    for fpga_id in range(1, 13):
        selected = assignments.get(str(fpga_id), variant)
        directory = output / f"board_{fpga_id:02d}"
        directory.mkdir(parents=True, exist_ok=True)
        ip = f"192.168.1.{100+fpga_id}"
        environment = (f"# {selected}; select N3_UIO after checking the generated bridge ID.\n"
                       f"FPGA_ID={fpga_id}\nN3_DEST=192.168.1.100\nN3_PORT=5000\nN3_BATCH=50\n"
                       "# N3_UIO=/dev/uioN\n")
        (directory / "n3-board.env").write_text(environment)
        (directory / "10-n3-eth0.network").write_text(f"[Match]\nName=eth0\n\n[Network]\nAddress={ip}/24\nDHCP=no\n")
        boards.append({"id": fpga_id, "ip": ip, "variant": selected,
                       "destination": "192.168.1.100", "port": 5000,
                       "uio_device": None, "timestamp_hz": 50000000})
    (output / "deployment.json").write_text(json.dumps({"status": "template: verify physical board variants and fill UIO assignments before deployment", "boards": boards}, indent=2) + "\n")
    return boards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="Athena_DE10_LSB")
    parser.add_argument("--assignments", type=Path, help='JSON object, e.g. {"2":"Athena_DE10_PUF"}')
    parser.add_argument("--output", type=Path, default=HERE / "deployment")
    args = parser.parse_args()
    assignments = json.loads(args.assignments.read_text()) if args.assignments else None
    try:
        generate(args.output, args.variant, assignments)
    except ValueError as error:
        parser.error(str(error))
    print(f"Prepared twelve board configurations in {args.output}; no files installed on hardware")


if __name__ == "__main__":
    main()

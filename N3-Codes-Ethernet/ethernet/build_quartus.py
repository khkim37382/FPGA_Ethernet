"""Generate the common HPS IP, derive UIO metadata and compile DE10 variants.

Run on a supported Quartus host with Quartus Prime Standard/Lite 23.1 and
Cyclone V support. This script does not program boards or modify SD cards.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    variants = json.loads((HERE / "variants.json").read_text())
    parser.add_argument("--variant", choices=[v["name"] for v in variants], action="append")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.variant:
        variants = [v for v in variants if v["name"] in args.variant]
    search = str(HERE / "rtl") + "/**/*,$"
    commands = [(HERE / "board", ["qsys-generate", "n3_hps.qsys", "--synthesis=VERILOG", f"--search-path={search}"]),
                (HERE, [sys.executable, "board/generate_uio.py", "board/n3_hps.sopcinfo"])]
    commands += [(ROOT / v["directory"], ["quartus_sh", "--flow", "compile", "N3_Ethernet", "-c", "N3_Ethernet"]) for v in variants]
    if args.dry_run:
        for work, command in commands:
            print(f"In {work}:\n  {subprocess.list2cmdline(command)}")
        return
    for tool in ("qsys-generate", "quartus_sh"):
        if not shutil.which(tool):
            parser.error(f"{tool} is not on PATH; run on the Quartus host (use --dry-run to inspect commands)")
    report = {"commands": [], "inputs": {}}
    inputs = [HERE / "board/n3_hps.qsys", *sorted((HERE / "rtl").glob("*"))]
    for v in variants:
        inputs += [ROOT / v["directory"] / "N3_Ethernet.qsf", ROOT / v["directory"] / "DE10_TOP_Ethernet.v"]
    for path in inputs:
        if path.is_file():
            report["inputs"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    log_dir = HERE / "build/quartus"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, (work, command) in enumerate(commands):
            print(f"Running {' '.join(command)} in {work}", flush=True)
            with (log_dir / f"step_{index:02d}.log").open("w") as log:
                result = subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT)
            report["commands"].append({"cwd": str(work), "command": command, "exit_code": result.returncode})
            if result.returncode:
                raise SystemExit(f"Build step failed; see {log_dir / f'step_{index:02d}.log'}")
    finally:
        (log_dir / "build_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Quartus compilation finished. Review fitter/timing reports before programming hardware.")


if __name__ == "__main__":
    main()

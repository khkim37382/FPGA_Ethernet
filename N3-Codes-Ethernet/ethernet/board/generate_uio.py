"""Generate polling UIO device-tree fragments from a freshly generated system.

No fixed physical bridge address or IRQ is assumed. The address must be
present in the HPS CPU view, or be composed from its lightweight bridge
window and the generated HPS lightweight-master view of n3_bridge.avs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def number(text):
    text = text.strip()
    return int(text, 16 if text.lower().startswith("0x") else 10)


def resolve_address(path):
    root = ET.parse(path).getroot()
    if root.get("name") != "n3_hps":
        raise ValueError("expected freshly generated n3_hps.sopcinfo, not an old loan_io system")
    if not any(m.get("name") == "n3_bridge" and m.get("kind") == "n3_ethernet_bridge"
               for m in root.findall("module")):
        raise ValueError("generated system does not contain the N3 bridge component")
    cpu_blocks = []
    relative_blocks = []
    for module in root.findall("module"):
        for interface in module.findall("interface"):
            blocks = interface.findall("memoryBlock")
            if (module.get("name") or "").endswith("arm_a9_0"):
                cpu_blocks += blocks
            if module.get("name") == "hps_0" and interface.get("name") == "h2f_lw_axi_master":
                relative_blocks += blocks
    direct = [b for b in cpu_blocks if b.findtext("moduleName") == "n3_bridge" and b.findtext("slaveName") == "avs"]
    candidates = [(number(b.findtext("baseAddress")), number(b.findtext("span")), "HPS CPU memory view") for b in direct]
    if not candidates:
        windows = [b for b in cpu_blocks if b.findtext("slaveName") == "axi_h2f_lw" and b.findtext("isBridge") == "true"]
        targets = [b for b in relative_blocks if b.findtext("moduleName") == "n3_bridge" and b.findtext("slaveName") == "avs"]
        if len(windows) == 1 and len(targets) == 1:
            window, target = windows[0], targets[0]
            base, window_size = number(window.findtext("baseAddress")), number(window.findtext("span"))
            offset, size = number(target.findtext("baseAddress")), number(target.findtext("span"))
            if offset + size > window_size:
                raise ValueError("N3 bridge lies outside generated HPS lightweight bridge window")
            candidates = [(base + offset, size, "HPS CPU lightweight window + HPS lightweight master target")]
    if len(candidates) != 1:
        raise ValueError("cannot uniquely resolve n3_bridge.avs in generated HPS address maps; inspect fresh metadata")
    address, span, method = candidates[0]
    if address % 4096 or span < 0x80 or address + span > 2**32:
        raise ValueError("expected a page-aligned 32-bit physical N3 resource of at least 0x80 bytes")
    return address, span, method


def generate(sopcinfo, output):
    address, span, method = resolve_address(sopcinfo)
    output.mkdir(parents=True, exist_ok=True)
    node = f'''n3_uio: n3-record-bridge@{address:x} {{
    compatible = "generic-uio";
    reg = <0x{address:08x} 0x{span:08x}>;
    status = "okay";
}};
'''
    # DE10-Standard ARMv7 root: one address cell, one size cell. A root-level
    # node avoids guessing the live FPGA bus's ranges or labels.
    (output / "n3-uio.dtsi").write_text("// Generated from n3_hps.sopcinfo. Include in the board DTS.\n/ {\n" + node + "};\n")
    overlay = '/dts-v1/;\n/plugin/;\n/ {\n    fragment@0 {\n        target-path = "/";\n        __overlay__ {\n            #address-cells = <1>;\n            #size-cells = <1>;\n' + node + "        };\n    };\n};\n"
    (output / "n3-uio.dtso").write_text(overlay)
    (output / "n3-uio-address.json").write_text(json.dumps({
        "source": str(sopcinfo), "source_sha256": hashlib.sha256(sopcinfo.read_bytes()).hexdigest(),
        "physical_address": f"0x{address:08x}", "span": f"0x{span:x}", "resolution": method,
        "interrupt": None, "root_address_cells": 1, "root_size_cells": 1,
    }, indent=2) + "\n")
    return address, span


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sopcinfo", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "generated")
    args = parser.parse_args()
    try:
        address, span = generate(args.sopcinfo, args.output)
    except (ValueError, ET.ParseError) as error:
        parser.error(str(error))
    print(f"Generated polling UIO at 0x{address:08x}, span 0x{span:x}")


if __name__ == "__main__":
    main()

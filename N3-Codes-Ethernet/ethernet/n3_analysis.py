"""Decode the source-defined fields of N3 DE10 words without losing raw data."""
import json
from pathlib import Path

VARIANTS = {v["name"]: v for v in json.loads((Path(__file__).parent / "variants.json").read_text())}
FIELD_NAMES = ["kind", "sr_index", "count", "frame_address", "ff_bits_hex", "sram_index",
               "address", "data_hex", "data_meaning", "adc_first_raw", "adc_second_raw"]


def decode_fields(raw: bytes, variant_name: str) -> dict:
    if len(raw) != 20:
        raise ValueError("an N3 word is exactly 20 bytes")
    variant = VARIANTS[variant_name]
    tag, value = raw[0], int.from_bytes(raw, "big")
    if tag == 0x20:
        return {"kind": "sr_counter", "sr_index": (value >> 12) & 0x7f, "count": value & 0xfff}
    if tag == 0x60:
        return {"kind": "ff_snapshot", "frame_address": (value >> 64) & 0x1ffffff,
                "ff_bits_hex": f"{value & ((1 << 60) - 1):015x}"}
    if tag in (0xe0, 0xe1):
        index = tag & 1
        width, address_bits = variant[f"sram{index}_data_bits"], variant[f"sram{index}_address_bits"]
        return {"kind": "sram", "sram_index": index, "address": (value >> width) & ((1 << address_bits) - 1),
                "data_hex": f"{value & ((1 << width) - 1):0{(width + 3)//4}x}",
                "data_meaning": "raw_power_on_word" if variant["puf"] else "xor_error_mask"}
    if tag in (0x80, 0x40):
        return {"kind": "adc_channels_1_2" if tag == 0x80 else "adc_channels_3_4",
                "adc_first_raw": (value >> 16) & 0xffff, "adc_second_raw": value & 0xffff}
    return {"kind": "unknown_tag"}

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReceiverConfig:
    bind_ip: str
    udp_port: int
    fpgas: dict[int, str]
    buffer_packets: int = 2048
    offline_timeout_seconds: float = 2.0


def load_config(path: str | Path) -> ReceiverConfig:
    raw = json.loads(Path(path).read_text())
    computer = raw["computer"]
    fpgas = {int(item["id"]): str(item["ip"]) for item in raw["fpgas"]}
    if sorted(fpgas) != list(range(1, 13)):
        raise ValueError("configuration must define exactly FPGA IDs 1 through 12")
    if len(set(fpgas.values())) != 12:
        raise ValueError("each FPGA requires a unique configured IP address")
    return ReceiverConfig(str(computer.get("bind_ip", "0.0.0.0")), int(computer["udp_port"]), fpgas,
                          int(raw.get("buffer_packets", 2048)),
                          float(raw.get("offline_timeout_seconds", 2.0)))

from __future__ import annotations

import csv
from pathlib import Path


class StreamLogger:
    def __init__(self, directory: str | Path, enabled: bool) -> None:
        self.enabled = enabled
        self.files: dict[int, object] = {}
        self.metadata: dict[int, csv.writer] = {}
        if not enabled:
            return
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        for fpga_id in range(1, 13):
            self.files[fpga_id] = (directory / f"fpga_{fpga_id:02d}.bin").open("ab", buffering=1024 * 1024)
            csv_file = (directory / f"fpga_{fpga_id:02d}_metadata.csv").open("a", newline="", buffering=1024 * 1024)
            writer = csv.writer(csv_file)
            if csv_file.tell() == 0:
                writer.writerow(["receive_time_unix", "fpga_id", "sequence_number", "payload_size", "source_ip", "packets_lost"])
            self.files[-fpga_id] = csv_file
            self.metadata[fpga_id] = writer

    def write(self, fpga_id: int, payload: memoryview, sequence: int, source_ip: str, lost: int) -> None:
        if not self.enabled:
            return
        self.files[fpga_id].write(payload)
        self.metadata[fpga_id].writerow([f"{__import__('time').time():.6f}", fpga_id, sequence, len(payload), source_ip, lost])

    def close(self) -> None:
        for stream in self.files.values():
            stream.close()

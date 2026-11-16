from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class FpgaState:
    fpga_id: int
    expected_ip: str
    buffer_capacity: int
    latest_sequence: int | None = None
    latest_timestamp: int | None = None
    latest_sample: int | None = None
    last_arrival: float | None = None
    packets_received: int = 0
    payload_bytes_received: int = 0
    packets_lost: int = 0
    duplicates: int = 0
    out_of_order: int = 0
    application_drops: int = 0
    ip_mismatches: int = 0
    payload_buffer: deque[memoryview] = field(init=False)
    _recent: deque[tuple[float, int]] = field(default_factory=deque, init=False)
    _seen: set[int] = field(default_factory=set, init=False)
    _seen_order: deque[int] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self.payload_buffer = deque(maxlen=self.buffer_capacity)

    def observe_sequence(self, sequence: int) -> None:
        # uint32 modular comparison: forward distances below 2^31 are newer.
        if sequence in self._seen:
            self.duplicates += 1
            return
        self._seen.add(sequence)
        self._seen_order.append(sequence)
        if len(self._seen_order) > 65_536:
            self._seen.discard(self._seen_order.popleft())
        if self.latest_sequence is None:
            self.latest_sequence = sequence
            return
        expected = (self.latest_sequence + 1) & 0xFFFFFFFF
        distance = (sequence - expected) & 0xFFFFFFFF
        if distance == 0:
            self.latest_sequence = sequence
        elif 0 < distance < 0x80000000:
            self.packets_lost += distance
            self.latest_sequence = sequence
        else:
            self.out_of_order += 1

    def accept(self, sequence: int, timestamp: int, payload: memoryview, now: float | None = None,
               latest_sample: int | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.observe_sequence(sequence)
        self.latest_timestamp = timestamp
        if latest_sample is not None:
            self.latest_sample = latest_sample
        self.last_arrival = now
        self.packets_received += 1
        self.payload_bytes_received += len(payload)
        self._recent.append((now, len(payload)))
        while self._recent and self._recent[0][0] < now - 1.0:
            self._recent.popleft()
        if len(self.payload_buffer) == self.buffer_capacity:
            self.application_drops += 1
        self.payload_buffer.append(payload)

    def rates(self, now: float | None = None) -> tuple[float, float]:
        now = time.monotonic() if now is None else now
        while self._recent and self._recent[0][0] < now - 1.0:
            self._recent.popleft()
        return float(len(self._recent)), sum(size for _, size in self._recent) * 8 / 1_000_000

    def active(self, timeout: float, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return self.last_arrival is not None and now - self.last_arrival <= timeout

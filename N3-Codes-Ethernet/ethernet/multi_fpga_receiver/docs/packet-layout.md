# Multi-FPGA UDP Packet Layout (Protocol Version 1)

Every UDP datagram has this fixed 26-byte header followed by payload. All multibyte fields use big-endian (network byte order). The IPv4/UDP headers are built by the FPGA's network stack and are not included below.

| Offset | Bytes | Type | Field | Purpose |
|---:|---:|---|---|---|
| 0 | 4 | `uint32` | `magic` | `0x46504741`, ASCII `FPGA`; rejects unrelated traffic. |
| 4 | 1 | `uint8` | `version` | `1`. |
| 5 | 1 | `uint8` | `fpga_id` | Board identity, must be 1 through 12. |
| 6 | 1 | `uint8` | `packet_type` | `1` = big-endian `uint16` sample payload. |
| 7 | 1 | `uint8` | `flags` | Reserved; transmit zero in version 1. |
| 8 | 4 | `uint32` | `sequence_number` | Increment once for every attempted packet, wraps from `0xffffffff` to zero. |
| 12 | 8 | `uint64` | `timestamp` | FPGA clock counter, with its timebase defined by the FPGA design. |
| 20 | 2 | `uint16` | `payload_length` | Payload byte count, 0 through 65,481. |
| 22 | 4 | `uint32` | `crc32` | CRC-32/IEEE over bytes 0–21 followed by all payload bytes. |
| 26 | N | `uint8[N]` | `payload` | Application data. For type 1: `N/2` samples, each `uint16` big-endian. |

The receiver validates magic, version, ID, exact length, and CRC before routing. It routes by the in-band FPGA ID, while treating source IP as a separately logged cross-check. This intentionally supports local simulations where all senders have `127.0.0.1`.

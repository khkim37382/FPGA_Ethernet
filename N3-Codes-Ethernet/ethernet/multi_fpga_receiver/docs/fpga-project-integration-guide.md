# FPGA Project Integration Guide: Data Collection to Laptop

This guide defines the boundary between a future FPGA data-collection project and the computer receiver. Treat [packet-layout.md](packet-layout.md) as the immutable version-1 wire contract. The FPGA project may change its sensors, sampling rate, FIFO depth, or board vendor, but it must not change those bytes without a protocol-version change on both sides.

## Recommended implementation split

```text
FPGA fabric                         Bridge (HPS / soft CPU / Ethernet engine)        Computer
ADC or sensor -> sample formatter -> asynchronous FIFO -> packet builder -> UDP/IP/MAC -> receiver.py
                 FPGA clock domain      memory / DMA           Ethernet PHY          12 streams
```

Use an asynchronous FIFO whenever collection and bridge/network clocks differ. The producer writes complete fixed-size samples; the bridge only reads when a whole sample is available. This prevents partially read samples and allows short network stalls without corrupting acquisition.

The bridge can be: (1) Linux code on an FPGA SoC HPS, (2) a Nios/soft CPU with a UDP stack, or (3) pure RTL containing UDP/IP/Ethernet logic. The included portable C reference in `bridge/` is the recommended first implementation for an HPS/soft-CPU bridge. It makes the packet contract executable before implementing a full hardware network stack.

## Mandatory per-board constants

Program these values once for each physical board and keep a deployment record:

| FPGA ID | Static IPv4 address | UDP destination |
|---:|---|---|
| 1 | `192.168.1.101` | Laptop `192.168.1.100:5000` |
| 2 | `192.168.1.102` | Laptop `192.168.1.100:5000` |
| ... | ... | ... |
| 12 | `192.168.1.112` | Laptop `192.168.1.100:5000` |

Set subnet mask `255.255.255.0`; a gateway is not needed for this isolated switch network. FPGA ID and IP must each be unique. Update the computer mapping in `config/config.json` if these assignments change.

## What every transmitted datagram must do

1. Increment a **per-board** unsigned 32-bit packet sequence number for every attempted packet, including one that later fails to transmit.
2. Copy one or more whole samples from the acquisition FIFO into the payload. Never mix samples from a different board.
3. Write every multi-byte header and `uint16` type-1 sample in big-endian order.
4. Set the 64-bit timestamp to the first sample's FPGA clock count. Document the counter frequency in the FPGA project readme.
5. Set payload length exactly to the number of payload bytes.
6. Compute CRC-32/IEEE over header offsets `0..21`, then the payload; place it big-endian at offsets `22..25`.
7. Send the entire custom header plus payload as the payload of one IPv4 UDP datagram addressed to port `5000`.

For ordinary 1500-byte Ethernet MTU, choose payload length no larger than **1400 bytes**. With the 26-byte application header, the UDP payload is 1426 bytes, leaving room for UDP (8 bytes) and IPv4 (20 bytes) headers without fragmentation. For type-1 16-bit samples this is 700 samples per packet.

## Bridge reference implementation

`bridge/fpga_udp_bridge.c` and `.h` generate exactly the same custom packet accepted by `receiver.py`. They contain no vendor-specific calls. In a Linux/HPS project, retain `fpga_udp_build_packet()` and replace `make_samples()` in `udp_bridge_sender.c` with FIFO/DMA reads. Send the returned buffer with the platform's UDP API.

Validate its deterministic header logic with:

```bash
cc -std=c11 -Wall -Wextra -Werror bridge/fpga_udp_bridge.c bridge/tests/test_bridge_packet.c -o /tmp/fpga_udp_bridge_test
/tmp/fpga_udp_bridge_test
```

On a POSIX HPS/Linux system, a no-hardware network smoke test is:

```bash
cc -std=c11 -Wall -Wextra bridge/fpga_udp_bridge.c bridge/udp_bridge_sender.c -o udp_bridge_sender
./udp_bridge_sender 192.168.1.100 1 100
```

The FPGA FIFO read replaces only payload generation; identity, sequence ownership, byte order, header construction, CRC, and UDP destination stay as written.

## FPGA-side collection interface to define in every project

Write this small interface into the new FPGA project's design document before RTL begins:

```text
Sample word:     uint16 sample, big-endian when serialized
Timestamp:       uint64 free-running acquisition-clock counter, captured with first sample
FIFO unit:       one complete sample (or a documented wider record)
Overflow policy: count drops; never overwrite silently
Packet batch:    up to 700 uint16 samples / 1400 payload bytes
Flow control:    bridge reads only when FIFO reports data available
```

If a project needs richer records, allocate a new `packet_type` and document its payload layout, sampling units, and byte order. Do not repurpose type `1`, which always means a contiguous big-endian `uint16` sample array.

## Bring-up checklist for every data collection run

1. Confirm physical FPGA ID, static IP, and config mapping match.
2. Confirm laptop adapter is `192.168.1.100/24` and connected to the same switch.
3. Launch `python3 receiver.py --log-dir logs --decode-samples` from `multi_fpga_receiver`.
4. Start one board first. Verify its dashboard row becomes `ACTIVE`, source IP is correct, CRC/malformed count remains zero, and sequence increases.
5. Start remaining boards. Confirm every expected row is active and its rate is plausible.
6. Check `LOST`, `OOO`, and `DUP` separately per FPGA. A fault on one board must not change another board’s counters.
7. After acquisition, archive per-board `.bin` and metadata `.csv` files together with the FPGA bitstream version, board-ID/IP table, timestamp frequency, and receiver config.

## Acceptance criteria before real acquisition

- Python simulation succeeds with all 12 IDs.
- The bridge self-test above succeeds.
- A single physical board produces valid packets for at least ten minutes without malformed packets.
- All active boards show the intended packet type and payload length.
- At the intended rate, packet loss and FIFO-overflow counters are measured and recorded—not assumed zero.
- Disconnecting one board only changes that board to `OFFLINE` after the configured timeout.

This procedure means future FPGA project work has one clear obligation: produce the versioned bytes in the packet-layout document. The receiver and bridge do not need to be redesigned for each data-collection experiment.

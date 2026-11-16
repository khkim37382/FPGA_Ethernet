# 12-Stream FPGA Ethernet Receiver

This is a working, standard-library Python prototype for receiving UDP data from up to twelve FPGA boards through one Ethernet switch and one computer Ethernet port. It is intentionally a separate project from the existing single-DE10 receiver so the verified legacy protocols remain unchanged.

```text
FPGA 1..12 -> Ethernet switch -> one computer Ethernet interface -> one UDP socket
                                                                  -> parser -> FPGA-ID router
                                                                  -> 12 independent state/buffer/log streams
```

Ethernet is not a collection of COM ports. The switch multiplexes Ethernet frames onto the computer link, and the operating system delivers the resulting UDP datagrams to one socket. Packets can interleave arbitrarily; the application header identifies each board. Each stream retains its own sequence tracking, buffer, rate statistics, file logging, timestamps, and offline status.

## Quick local demonstration

No dependencies beyond Python 3.10+ are required. From this directory, use two terminals:

```bash
python3 receiver.py --config config/config.json
python3 simulator.py --fpgas 12 --rate 100
```

The simulator runs all twelve senders from `127.0.0.1`. Source-IP warnings are therefore expected with the physical-network configuration; identity and separation still work because they are based on `fpga_id` in each packet. To create separate binary data and CSV metadata files, start the receiver with:

```bash
python3 receiver.py --log-dir logs
```

This produces `logs/fpga_01.bin` through `logs/fpga_12.bin` and matching `*_metadata.csv` files. Binary payload logging is separate from metadata so high-rate data does not require CSV conversion.

For the optional uint16-sample demo view, use `python3 receiver.py --decode-samples`. It adds the most recent type-1 sample for every FPGA to the dashboard; packet reception does not depend on this decoding.

Useful simulator fault tests:

```bash
python3 simulator.py --fpgas 12 --rate 1000 --drop-every 20
python3 simulator.py --fpgas 12 --rate 100 --malformed-every 25
python3 simulator.py --fpgas 12 --rate 100 --stop-fpga 7 --stop-after 2
```

`--drop-every` skips a sequence number, which exercises per-FPGA loss accounting. A stopped source becomes `OFFLINE` after the configured timeout. Type-1 simulator payloads are network-order `uint16` sample values and can be decoded independently with `src.packet.decode_u16_samples`; no visualization dependency is coupled to reception.

## Network configuration for hardware

Set the computer Ethernet adapter to `192.168.1.100/24`, set each FPGA to the static address in `config/config.json` (`192.168.1.101` through `.112`), and set the UDP destination to computer address `192.168.1.100`, port `5000`. Connect all boards and the computer to the same normal Ethernet switch. No router or internet is needed.

For real hardware, optionally set `computer.bind_ip` to `192.168.1.100` rather than `0.0.0.0`. Keep the configured FPGA IP mapping unique: receiver source-IP checks warn if, for example, a packet that claims FPGA 5 arrives from FPGA 9’s configured IP. The packet is still routed by its declared ID so a warning does not turn a wiring/configuration fault into silent data mixing.

## Packet protocol

The exact FPGA-implementable binary layout is in [docs/packet-layout.md](docs/packet-layout.md). It is versioned and uses a fixed `FPGA` magic number, board ID, packet type, uint32 sequence, uint64 FPGA clock counter, explicit payload length, and CRC-32/IEEE. All multibyte fields are network byte order.

For the repeatable FPGA/bridge implementation procedure, see [docs/fpga-project-integration-guide.md](docs/fpga-project-integration-guide.md). It includes the portable C bridge packet builder, FPGA FIFO contract, board configuration table, payload limits, and bring-up checklist.

On each source independently, a forward sequence gap increments that source’s lost count. Previously observed sequences are duplicates; older, unseen sequences are counted as out of order. Sequence arithmetic wraps correctly at uint32 rollover. The receiver validates header, exact datagram length, and CRC before any stream is updated.

## Dashboard and performance

The terminal dashboard updates in place rather than printing lines continuously. It reports one-second packet rate and payload Mbps for all twelve boards, plus RX, loss, duplicate, out-of-order, and buffer counts. Per-board payload buffers are bounded by `buffer_packets` in config; when full, the oldest buffered item is displaced and `application_drops` rises rather than allowing memory growth.

The receive path uses one socket and keeps payloads as `memoryview`s into their received datagram rather than making an extra payload copy. Logging uses 1 MiB file buffers. A practical starting benchmark is:

```bash
python3 receiver.py --quiet --socket-buffer $((8*1024*1024)) --duration 10
python3 simulator.py --fpgas 12 --rate 1000 --samples-per-packet 700 --duration 10
```

Actual sustainable rate depends on NIC, switch, packet size, Python CPU time, disk logging, and OS UDP socket buffering. Keep IPv4 UDP payloads at or below the link MTU budget (typically ≤1472 bytes for Ethernet MTU 1500) to avoid fragmentation; the protocol itself supports larger UDP payloads.

## Test suite

```bash
python3 -m unittest discover -s tests -v
```

Tests cover wire serialization and rejection, all twelve interleaved streams, independent sequence loss/duplicate/out-of-order accounting, bounded buffers, source-IP mismatch handling, and a live localhost UDP integration test that routes packets from every ID into its own state.

## Troubleshooting

- **No packets:** verify the receiver bind address/port, FPGA UDP destination, link LEDs, and macOS firewall policy. Try `computer.bind_ip` as `0.0.0.0` in config.
- **Wrong subnet:** computer and boards must all be `/24` on `192.168.1.x` in the supplied example; no default route is required.
- **IP/ID warnings:** check static-IP programming and FPGA IDs; each physical board needs a unique value for both.
- **Malformed packets:** compare FPGA builder output field-for-field with the packet-layout document, including big-endian byte order and CRC coverage.
- **Packet loss:** inspect dashboard loss per board, switch/NIC counters, link speed, MTU, receiver CPU, and OS receive buffer. Increase `--socket-buffer` only after measuring.

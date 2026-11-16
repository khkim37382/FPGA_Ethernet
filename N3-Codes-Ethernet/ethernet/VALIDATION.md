# Local validation — 2026-11-03

All four DE10 Ethernet revisions were checked locally. The original N3
repository remains clean; this copy has no Git metadata. See `COPY_AUDIT.json`.

## Results

| Check | Result |
|---|---|
| Athena LSB actual producer | Pass: all 60 channels, two reset sessions, stable records under backpressure |
| Athena FFMCU actual producer | Pass: first 128 complete snapshots/frame addresses, two reset sessions and stalls |
| Athena PUF actual FF producer | Pass: first 128 complete snapshots/frame addresses, two reset sessions and stalls |
| Zeus LSB actual producer | Pass: all 60 channels, two reset sessions and stalls |
| SRAM controller timing, all variants | Pass: original divider versus new /21 clock enable, matching control pins and complete records |
| SRAM address order and rollover | Pass: real-width tests plus compact address-space rollover tests for all variants |
| PUF long waiting path | Pass: candidate with a tiny wait-counter bound remains equivalent to the reference while waiting for triggers |
| LSB primitive counter, both variants | Pass: vector interface, enable, modulo-4096 rollover and reset |
| Actual VHDL synthesis | Pass: producers, IVT/I2C, clock divider and both SRAM specializations for every variant |
| Complete top structural lint | Pass: synthesized VHDL plus vendor HPS port contract; width, implicit-net and constant unsigned-comparison errors are fatal |
| Shared FIFO/Avalon bridge | Pass: simultaneous sources, fairness, held-ready deduplication, full/backpressure recovery, capture/release, empty capture, timestamps and reset |
| RTL Avalon words through real C serializer | Pass: exact complete-record byte order verified by Python |
| Twelve concurrent C UDP senders | Pass: 101 records per board; 1,212 records / 36 datagrams; exact separate logs; zero sequence gaps; uint32 rollover |
| Packet rejection | Pass: bad CRC, bad N3 sizes, timestamp mismatch, invalid board IDs and truncated replay |
| Four-variant field decoding | Pass: full-width SRAM data/address limits, raw PUF versus XOR masks, FF addresses and snapshots |
| Deployment/UIO generation | Pass: unique IDs/IPs, mixed variants, physical address derivation, rejection of stale or unaligned metadata |
| Device-tree syntax | Pass: generated polling UIO overlay compiled by DTC |
| Legacy N3 export | Pass: all twenty data bytes retained, including embedded binary LF/CR |
| Original receiver regression | All seven tests pass |
| ARM HPS sender | Cross-build passes: static, stripped ELF32 ARM EABI5 for Cortex-A9; architecture inspected, not executed on hardware |
| Quartus build workflow | All-four-project dry-run checked; actual Quartus tools unavailable on this Mac |

There are 14 GHDL simulation benches (four producers, eight SRAM benches and
two counter tests), one self-checking Verilator bridge simulation, 13 N3/
configuration Python tests, and seven original receiver tests.

The source repairs are described in the main README. SRAM timing equivalence
applies the same intentional address/timer repair to the original reference.
It does not assert equivalence to its broken scan termination behavior.
Independent address scoreboards check address zero, ordering, rollover, reset
and disabled waiting.

## Evidence and reproduction

```sh
make test
make hdl-check GHDL=/path/to/ghdl
make arm ZIG=/path/to/zig
python3 build_quartus.py --dry-run
```

- `build/software-validation.log`: bridge/C/Python test output.
- `build/hdl-validation.log` and `build/hdl_validation.json`: all-variant HDL summary.
- `build/<variant>/hdl_check/*.log`: analysis, simulation, synthesis and top lint details.
- `build/arm-linux/BUILD.json`: compiler/target, source hashes and ARM binary hash.
- `board/terasic/SOURCE.json`: official board reference provenance and hashes.

Tools used: Apple Clang 21.0.0, GHDL 6.0.0 with LLVM backend, Verilator 5.050,
DTC 1.8.1 and Zig 0.17.1. GHDL came from its
[official release](https://github.com/ghdl/ghdl/releases/tag/v6.0.0); the ARM
cross compiler came from the [official Zig download](https://ziglang.org/download/).
These tool binaries are not included as source-copy runtime dependencies.

## Remaining Quartus and board validation

No Intel HPS behavioral model or physical FPGA was used. Structural lint uses
the official HPS port contract, so it cannot establish DDR training, Linux
boot, PHY operation, Quartus generation, fitting, timing closure, live UIO
access, sustained throughput, DUT signal timing or sensor calibration.

Fresh physical UIO fragments require Quartus to generate the new
`n3_hps.sopcinfo`; no physical address or interrupt has been guessed. HPS
Ethernet/DDR/SD/console settings are supplied from the Terasic reference and
need Quartus validation against the actual board and boot setup. Historical
generated N3 IP, handoff and boot artifacts are not used by the new revisions.

The original FFMCU/PUF tops leave DUT control wires `clk_piso`, `clr_ctr` and
`load_b` without drivers. Confirm their required behavior for the daughtercard
mode before programming. The inherited Zeus TCAM issue also requires a DUT
functional check. These remain visible in the main README.

No board programming, SD-card changes, live network changes or instrument
commands were performed.

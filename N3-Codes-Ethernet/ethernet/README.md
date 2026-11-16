# N3 DE10 Ethernet acquisition — all four variants

This local project adapts Athena LSB, Athena FFMCU, Athena PUF, and Zeus LSB
to the existing twelve-board Ethernet receiver. The original `N3-Codes` and
`Current` projects are untouched. This copy contains no `.git` metadata and
needs no network connection to generate projects, build senders, or receive data.

**Status:** all four source integrations pass local VHDL simulation, GHDL
synthesis, and structural top-level lint. The common bridge and twelve-board
UDP path pass local tests. An ARM Linux sender binary is provided.
A fresh ARM sender build has also passed a physical HPS-to-Mac five-record
simulated replay, with Linux boot and SSH verified. See
[setup lessons](../../docs/SETUP_LESSONS.md) for the direct-link configuration
and host-OS procedures.
**Quartus generation/fitting/timing and physical N3 FPGA/UIO/daughtercard
acquisition have not been run.** No copied historical bitstream contains this integration.

## Open the Ethernet revisions

Each project has its own `N3_Ethernet.qpf`, `N3_Ethernet.qsf`,
`N3_Ethernet.sdc`, and `DE10_TOP_Ethernet.v`:

| Directory under `../FPGA_DE10/` | Main acquisition producer | SRAM0 | SRAM1 | Data meaning |
|---|---|---|---|---|
| `Athena_DE10_LSB` | 60 SR counters | 13 address bits / 64 data bits | 11 / 128 | XOR error masks |
| `Athena_DE10_FFMCU` | FF snapshots and frame addresses | 13 / 64 | 11 / 128 | XOR error masks |
| `Athena_DE10_PUF` | FF snapshots; chained SRAM triggers retained | 13 / 64 | 11 / 128 | Raw power-on SRAM words |
| `Zeus_DE10_LSB` | 60 SR counters | 9 / 40, TCAM mode retained | 10 / 128 | XOR error masks |

Open **`N3_Ethernet.qpf`**, rather than a historical project revision.
The original source files/settings remain available separately. Newly generated
source files live in `acquisition/<variant>/`; do not edit them directly.

`variants.json` records producer types and widths. `prepare_projects.py`
regenerates the Ethernet revisions from the local originals and the included
Terasic reference files. It does not read the sibling original repository.

```sh
cd N3-Codes-Ethernet/ethernet
make prepare
```

This also prepares twelve example board identities under `board/deployment/`.
Those default to Athena LSB and are clearly marked as templates. Set each
physical board's actual variant and UIO device before deployment.

## Architecture and wire contract

```text
Each DE10:
  SR/FF producer + IVT + SRAM0 + SRAM1
    -> round-robin arbiter -> 1024 complete-record FIFO
    -> HPS lightweight Avalon master -> Linux UIO -> n3_udp_sender

Twelve concurrent boards:
  DE10 1..12 -> Ethernet switch -> laptop UDP port 5000
    -> header/CRC validation -> board-ID router -> separate per-board logs
```

The arbiter acknowledges a word only after buffering all 160 bits, holds ACK
until READY falls, and applies backpressure when full. Four simultaneous
sources cannot starve one another. The bridge and SRAM controllers use
`CLOCK_50`; FFMCU retains its falling-edge 50 MHz producer. SRAM state machines
use a clock enable with the original divider's exact 21-cycle cadence, which
removes the old divided-clock ready/ack boundary. The LSB DUT PISO clock is
retained, including its actual 50 MHz / 21 frequency and waveform.

Packet type **2** uses the existing receiver's **version-1, 26-byte header**,
board IDs 1..12, uint32 per-board packet sequences, big-endian byte order,
and CRC-32/IEEE. This differs from the older single-board `DS10` protocol.
See `multi_fpga_receiver/docs/packet-layout.md` for the unchanged outer header.
Type 1 remains uint16 samples.

A type-2 payload has 1..50 complete 28-byte records:

| Record bytes | Contents |
|---|---|
| 0..7 | uint64 FPGA acceptance timestamp, big endian, 50 MHz |
| 8..27 | Original complete 160-bit N3 word, most significant byte first |

The header timestamp equals the first record's timestamp. The bundled
receiver checks that equality and the record count before routing. The
maximum payload is 1400 bytes; complete UDP application data is 1426 bytes.
Every timestamp is captured when the FIFO accepts the word, rather than at
its original detection instant. Timestamps are local to each board; Ethernet
does not synchronize their clocks. UART LF/CR delimiters are removed during
transport, while embedded LF/CR bytes inside binary words are preserved.

Backpressure can pause acquisition. `stalled_cycles` counts full-FIFO waiting,
not lost DUT events. UDP has no retransmission here. Measure producer stalls,
network loss, disk rate, and aggregate switch/NIC capacity on hardware.

## Source issues corrected in the Ethernet revisions

These changes are isolated in generated Ethernet sources; copied originals
are preserved:

- Added missing FFMCU controller/trigger files and corrected source lists.
- Matched the LSB counter's required 12-bit vector interface; overflow now
  explicitly wraps at 4096. The shipped SharedFiles counter used an incompatible
  integer output.
- Reset the LSB transmit index to zero, so channels 0 and 1 are included in the
  first acquisition. Corrected its bounded periodic timer comparison.
- Corrected ordinary SRAM scan completion: an N-bit address cannot reach
  `2**N`. Scans now include address zero, complete at the representable last
  address, and enter the existing inter-scan waiting state. The waiting timer
  triggers at its limit and saturates while disabled.
- Removed an unused PUF waiting-counter increment that could overflow while
  waiting for a trigger. The FF-to-SRAM0-to-SRAM1 trigger chain is retained.
- Added a synchronous IVT controller reset so a reset cannot leave an old
  record marked ready. Rewrote generic-dependent I2C case ranges as equivalent
  comparisons for standard VHDL compatibility.
- Converted Verilog string generics to explicit bit-vector literals and
  declared the FFMCU SRAM status wire explicitly.

The SRAM timing comparison uses the original divided-clock implementation
with the same intentional address/timer corrections applied. Independent
address scoreboards verify ordering and rollover; this is not a claim that
all behavior of the buggy original remains unchanged.

## HPS configuration is now supplied

`board/n3_hps.qsys` supplies the shared HPS system, including the new bridge
at relative lightweight-master offset **0x10000**, span **0x80**. It uses the
complete DE10-Standard board memory and peripheral preset from Terasic's
[official System CD](https://download.terasic.com/downloads/cd-rom/de10-standard/DE10-Standard_v.1.4.0_SystemCD.zip):

- 32-bit HPS DDR3, 15 row-address bits, 10 column-address bits, 400 MHz memory
  setting, and the complete reference memory timing/board-skew settings.
- EMAC1 RGMII on HPS I/O Set 0.
- SD/MMC, console UART0, and the other reference HPS peripheral pin assignments.
- UART pins returned to the HPS console; old FPGA UART loan-I/O is removed.
- Only the lightweight HPS fabric master is enabled for this data path.

`board/terasic/SOURCE.json` records the download URL, archive hash, exact
reference paths and file hashes. Reference Qsys parameter names were matched
to the N3 project's 23.1 parameter set. Static checks verify the configured
memory and pin settings against that reference. These prepared settings still
need validation by Quartus and confirmation against the actual board revision.

## Local verification

Requirements: Python 3.10+, a C11 compiler, Verilator with timing support,
and GHDL with synthesis support. `dtc` is optional for device-tree syntax tests.
No extra Python packages are needed.

```sh
make test          # bridge simulation, C/Python transport, deployment/decoder checks
make hdl-check    # actual VHDL simulation/synthesis and all four top-level connections
# A GHDL path can be supplied explicitly:
make hdl-check GHDL=/path/to/ghdl
```

Results and limits are recorded in `VALIDATION.md`; detailed logs are under
`build/`. The Intel HPS is represented by its sourced interface contract for
structural lint. DDR training, Linux boot, RGMII traffic, fitting and timing
closure are not simulated by that contract.

For a localhost demo, start the receiver in one terminal:

```sh
cd multi_fpga_receiver
python3 receiver.py --log-dir ../logs/demo
```

From `ethernet/` in another terminal:

```sh
./build/n3_udp_sender --input build/rtl_records.bin --id 1 --dest 127.0.0.1
```

Run `make test` first to generate that fixture. A localhost/source-IP warning
is expected with the physical-network configuration; routing still uses ID.
The type-1 `--decode-samples` dashboard option does not decode N3 records.

## Quartus build on the supported host

Use Quartus Prime Standard/Lite 23.1 with Cyclone V support and both
`quartus_sh` and `qsys-generate` on PATH. Inspect the commands first if useful:

```sh
python3 build_quartus.py --dry-run
python3 build_quartus.py
# Or compile one variant:
python3 build_quartus.py --variant Athena_DE10_PUF
```

The script generates the shared `n3_hps` IP, derives the Linux UIO resource
from the **fresh** `.sopcinfo`, and compiles the selected Ethernet revisions.
Logs and an input-hash/build report are written under `build/quartus/`.
This workflow was prepared and its dry-run checked locally; Quartus itself
is not installed on this Mac, so those commands have not been executed here.

Review full fitter/TimeQuest reports, including HPS resets, DDR/RGMII I/O,
FFMCU trigger clocks, DUT I/O timing and any unconstrained paths. The SDC
supplies CLOCK_50 and the LSB PISO waveform; actual daughtercard delays must
come from the hardware timing specification. No guessed I/O delays or blanket
false paths are supplied.

Generate matching HPS handoff/preloader/U-Boot/device-tree artifacts using the
board's selected Linux boot toolchain. Historical `loan_io/`, handoff files,
`.sopcinfo`, preloader files and bitstreams copied from N3 are stale for this
new system. The new revision references `n3_hps`, so it cannot silently use the
old generated `loan_io` IP.

## Linux UIO and board identities

After Qsys generation:

```sh
python3 board/generate_uio.py board/n3_hps.sopcinfo
```

This creates `board/generated/n3-uio.dtsi`, `n3-uio.dtso` and an address record.
It resolves the physical address from the generated HPS CPU view, or composes
its lightweight window with the generated slave offset. It rejects old systems,
ambiguous mappings, short spans and nonzero page offsets. **0x10000 is a
relative Qsys offset, not a Linux physical address.** No interrupt is invented.

Include the `.dtsi` in the matching DE10-Standard DTS, or use the overlay only
if the selected kernel/bootloader supports overlays. The fragments assume the
DE10 ARMv7 root's one address cell and one size cell. The kernel needs UIO and
`uio_pdrv_genirq`, matched to `generic-uio`; depending on the image, use
`modprobe uio_pdrv_genirq of_id=generic-uio` or the equivalent built-in boot
parameter. Terasic's [4.5 UIO driver](https://github.com/terasic/linux-socfpga/blob/socfpga-4.5/drivers/uio/uio_pdrv_genirq.c)
supports an absent interrupt for polling. Enable the lightweight FPGA bridge
using the selected image's bridge/FPGA-manager mechanism before MMIO access.

UIO map0 must describe this component, have a span of at least 0x80 and zero
map offset. Select the actual `/dev/uioN` from sysfs after boot. The sender
checks size, offset, ID, version and timestamp frequency, and takes an
exclusive advisory lock before enabling collection.

Default network: laptop **192.168.1.100/24**, boards **192.168.1.101..112/24**,
IDs **1..12**, destination **UDP 5000**. Every board has a unique ID and IP;
all boards of the same variant share the same bitstream and sender binary.
Different variants can be mixed with the same outer packet protocol.

```sh
python3 board/prepare_deployment.py --variant Athena_DE10_FFMCU
# For mixed variants, provide a JSON ID-to-variant object, for example:
# {"2":"Athena_DE10_PUF", "3":"Zeus_DE10_LSB"}
python3 board/prepare_deployment.py --assignments board/mixed-example.json
```

`board/deployment/board_XX/` contains an environment file and a
`systemd-networkd` static-IP file. They are prepared files, not installed on a
board. Fill in `N3_UIO`; confirm interface name `eth0`; install only that
board's network file and identity. `board/n3-acquisition.service` is an optional
service template. It deliberately does not restart automatically into a reused
receiver sequence history. Archive `deployment.json` with each acquisition;
the payload does not itself identify the scientific variant.

## Sender and receiver

The host-native sender is `build/n3_udp_sender`. The HPS executable is
**`build/arm-linux/n3_udp_sender`**, a statically linked ARMv7/Cortex-A9 EABI5
Linux binary. It was cross-built, not run on a physical board. Provenance and
hashes are in `build/arm-linux/BUILD.json`. Alternatively build from source
on the HPS with `make all`, or rebuild the ARM binary with `make arm ZIG=/path/to/zig`.

On a configured board, with the actual UIO number and board ID:

```sh
./n3_udp_sender --uio /dev/uio0 --id 1 --dest 192.168.1.100
```

`--batch 1..50` limits records per datagram; an incomplete batch sends when the
FIFO becomes empty. Ctrl-C disables acceptance and prints counters. Send
errors are fatal; data already consumed into a failed outgoing batch is not
retransmitted. Use one sender per component.

On the laptop:

```sh
cd multi_fpga_receiver
python3 receiver.py --log-dir ../logs/run_001
```

Use a fresh log directory and receiver process for each session. A sender
restart starts its sequence at zero; continue a running session only with an
explicit suitable `--sequence`, or start a new session. FPGA reset restarts
its local clock. Do not mix different protocols or sessions in a binary log.
The unchanged source-IP checks warn about incorrect ID/IP combinations.

After stopping the receiver, from `ethernet/`:

```sh
python3 decode_n3_log.py logs/run_001/fpga_01.bin logs/run_001/fpga_01.csv \
    --variant Athena_DE10_PUF --legacy-output logs/run_001/fpga_01_legacy.bin
```

CSV retains ticks, seconds, tag and complete raw hex. With `--variant`, it
also decodes source-defined SR counts, FF frame addresses/60-bit snapshots,
correct-width SRAM addresses/data, PUF raw-word versus XOR-mask meaning, and
raw ADC channel pairs. No calibration is invented. The optional legacy file
restores twenty bytes plus LF CR per record. Original COM-port scripts still
need file-input adaptation to consume that file directly.

## Register contract

Avalon addresses are **word** addresses; host offsets below are bytes.
Span is 0x80. Reads have no side effects.

| Offset | Register |
|---|---|
| 0x00 | ID 0x4e334531 (`N3E1`) |
| 0x04 | Version 0x00010000 |
| 0x08 | CONTROL bit 0 enables acceptance; disabled after reset |
| 0x0c | STATUS bit 0 empty, bit 1 full, bit 2 captured latch valid |
| 0x10 | COMMAND bit 0 captures/pops if free and nonempty; bit 1 releases latch |
| 0x14 | Queued records, excluding the latch |
| 0x20..0x38 | Seven stable words, low word first, of `{ticks[63:0], N3[159:0]}` |
| 0x40..0x44 | Accepted uint64, low/high |
| 0x48..0x4c | Captured/consumed uint64, low/high |
| 0x50..0x54 | Full-FIFO stalled uint64 cycles, low/high |
| 0x58 | Timestamp frequency, 50,000,000 Hz |

Repeated capture while latched and capture on empty do nothing. Explicit
capture avoids the old first-DATA0-read latch ambiguity. The sender reads
64-bit counters high/low/high. Disabling preserves queued records; reset
clears the FIFO, latch, counters and timestamp.

## Remaining bring-up checks

The prepared HPS settings replace the earlier manual Ethernet/DDR placeholder.
Remaining unverified work is Quartus IP generation, full compilation/fitting/
timing review, matching boot/device-tree installation, and physical acquisition.
Begin with one board at low rate, reconcile counters, then enable all twelve.
Confirm source reset, N3 data interpretation, FIFO stalls and packet loss.

The original FFMCU and PUF tops leave `clk_piso`, `clr_ctr`, and `load_b`
without drivers. This adaptation retains that inherited daughtercard wiring;
confirm whether those signals are used in the selected DUT mode and provide
the required levels/control before programming. LSB ties its clear/load
signals as upstream and retains the PISO clock. The upstream Zeus README
also reports TCAM issues; Ethernet transport tests do not establish TCAM/DUT
functional correctness. No board, SD card, live network setting or instrument
has been programmed or changed by this work.

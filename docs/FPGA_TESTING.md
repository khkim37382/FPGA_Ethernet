# Testing N3 Ethernet with an FPGA

Start with **one DE10-Standard running Athena LSB**, then expand to other
variants and multiple boards after the first board works. This project targets
the Cyclone V SoC DE10-Standard, not an interchangeable DE10-Lite/Nano design.

Local simulations passed previously, but the first Quartus build and physical
bring-up remain to be done. A successful UDP transfer alone does not establish
correct N3 DUT behavior.

```text
N3 daughtercard -> FPGA producer/FIFO -> HPS Linux/UIO -> ARM UDP sender
               -> Ethernet -> laptop receiver -> binary log -> decoded CSV
```

## 1. Choose where each task runs

| Task | Mac | Supported Windows/Linux build host | DE10 HPS Linux |
|---|---|---|---|
| Edit code and run available local simulations | Yes | Yes | Optional |
| Generate/compile FPGA design with Quartus | No native Quartus | Yes | No |
| Program through Quartus USB-Blaster | No native Quartus | Yes | No |
| Run ARM acquisition sender against UIO | No | No | Yes |
| Receive packets and decode logs | Yes | Yes | Optional |

Quartus supports Windows and Linux; see the
[official OS support page](https://www.altera.com/developers/software/os-support).
Use the project's specified Quartus Prime Standard/Lite 23.1 with Cyclone V
support. Check the exact supported OS for the selected release. A remote build
host is usable from a Mac; board programming still needs an appropriate
connection to the hardware.

## 2. Build the FPGA image on the Quartus host

Clone this repository and make `quartus_sh` and `qsys-generate` available on
PATH. From the repository root:

```sh
cd N3-Codes-Ethernet/ethernet
python3 build_quartus.py --variant Athena_DE10_LSB --dry-run
python3 build_quartus.py --variant Athena_DE10_LSB
```

On Windows, use the Python command available in your environment if it is
`python` rather than `python3`.

The script generates the shared `n3_hps` system, derives UIO metadata from the
fresh `.sopcinfo`, and compiles the selected revision. Logs and a build report
are written under `ethernet/build/quartus/`.

For the GUI project, open
`N3-Codes-Ethernet/FPGA_DE10/Athena_DE10_LSB/N3_Ethernet.qpf`.
The output directory is `output_files/ethernet/` inside that variant directory.
Use the newly generated `N3_Ethernet.sof`, never an old project bitstream.

Review fitter and TimeQuest reports before programming. Resolve timing failures
and assess unconstrained paths, HPS reset/DDR/RGMII timing, and actual
daughtercard I/O timing. The project does not invent daughtercard I/O delays.

Other build selections are `Athena_DE10_FFMCU`, `Athena_DE10_PUF`, and
`Zeus_DE10_LSB`. FFMCU/PUF inherit undriven DUT controls `clk_piso`, `clr_ctr`,
and `load_b`: determine and implement their required behavior before using
those modes. Zeus inherits a reported TCAM issue requiring separate DUT checks.

## 3. Prepare matching HPS Linux boot and UIO

**Programming the FPGA alone is insufficient.** The Ethernet path uses the
DE10's HPS ARM processor and Linux. Prepare a compatible SD-card boot system:

1. Generate matching HPS handoff/preloader, bootloader and device-tree artifacts
   with the board's selected Linux boot toolchain. Historical artifacts from
   the original `loan_io` design do not match this system.
2. Include the freshly generated `ethernet/board/generated/n3-uio.dtsi` in the
   matching DE10-Standard device tree, or use its `.dtso` only when supported.
3. Enable Linux UIO and `uio_pdrv_genirq` matched to `generic-uio`. Depending on
   the image this may use `modprobe uio_pdrv_genirq of_id=generic-uio` or an
   equivalent built-in boot parameter.
4. Configure the FPGA and enable the lightweight HPS-to-FPGA bridge using that
   image's FPGA-manager/bridge mechanism before accessing the component.
5. Copy `ethernet/build/arm-linux/n3_udp_sender` to the DE10. This is the ARM
   binary; `ethernet/build/n3_udp_sender` built on a Mac is a host test binary.

The exact boot image, bootloader and kernel determine the installation and
configuration sequence. This repository does not include a ready-to-flash SD
image or a validated boot recipe for a specific installed image.

After boot, inspect:

```sh
ls /sys/class/uio
cat /sys/class/uio/uio*/name
```

Select the actual `/dev/uioN`. Map0 must cover this component, span at least
`0x80` bytes and have zero map offset. The sender validates bridge ID
`0x4e334531`, version `0x00010000` and frequency `50000000` Hz. The Qsys
`0x10000` slave offset is relative, not a Linux physical address; use fresh
metadata rather than guessing an address.

## 4. Connect the first board

With power off, connect the N3 daughtercard and any required expansion/cabling
according to the [original wiring notes](../N3-Codes-Ethernet/README.md) and
[schematic](../N3-Codes-Ethernet/2_Documentation/N3_Daughtercard%20v136.pdf).
Verify board selection, rails, cable orientation and grounds against the actual
hardware. The legacy README includes DE2 switch numbers: use the selected
`DE10_TOP_Ethernet.v` for DE10 controls, not those numbers verbatim.

Connect the DE10 power supply, USB-Blaster, HPS console as needed, Linux SD card,
and HPS Ethernet port. Load the newly built `.sof` in Quartus Programmer:
select USB-Blaster, identify the correct FPGA, add the image, check
Program/Configure and start. Coordinate this with the HPS boot/bridge sequence
from step 3. For a first test, leave automatic acquisition services disabled
and start the sender manually.

## 5. Set up a one-board acquisition network

Use an isolated acquisition network or an otherwise suitable network without
conflicting addresses:

| Device | Address |
|---|---|
| Laptop/Mac Ethernet interface | `192.168.1.100/24` |
| First DE10 HPS Ethernet interface | `192.168.1.101/24` |
| Board ID | `1` |
| Destination UDP port | `5000` |

Allow incoming UDP port 5000 on the receiving computer. Confirm the actual DE10
interface name before installing a static-network template. Files under
`ethernet/board/deployment/board_01/` are templates, not already-installed
configuration; set the actual variant and UIO device. Prefer manual startup
for the first test.

## 6. Receive on the Mac, then start the sender on the DE10

On the Mac, from this repository root:

```sh
cd N3-Codes-Ethernet/ethernet/multi_fpga_receiver
python3 receiver.py --log-dir ../logs/hw_test_001
```

In the DE10 HPS Linux terminal, in the directory containing the copied ARM
binary, substitute the correct UIO number:

```sh
chmod +x n3_udp_sender
sudo ./n3_udp_sender --uio /dev/uio0 --id 1 --dest 192.168.1.100
```

Root is only needed if the current user's UIO permissions require it. The
sender defaults to UDP 5000 and supports batches of 1..50 records. Run only
one sender per bridge component.

Collect a short run, stop the sender with Ctrl-C to print counters, allow the
receiver to finish incoming traffic, then stop the receiver. Queued FPGA
records may remain; do not assume that stopping the sender drains the FIFO.

On the Mac, from `N3-Codes-Ethernet/ethernet/`:

```sh
python3 decode_n3_log.py \
  logs/hw_test_001/fpga_01.bin \
  logs/hw_test_001/fpga_01.csv \
  --variant Athena_DE10_LSB
```

Always select the actual variant for scientific decoding. PUF SRAM records
contain raw power-on words; the other listed variants contain XOR error masks.

## 7. Decide whether the run passed

- Receiver: valid records for board 1, no CRC/packet validation errors, and no
  sequence gaps for a clean low-rate run.
- Timing: nondecreasing record timestamps within a reset session; the 50 MHz
  timestamp marks FIFO acceptance, not the original DUT event time.
- Athena LSB: all 60 SR channels appear over a complete reporting cycle.
- SRAM: valid addresses, address-zero coverage, complete/repeating scans, and
  expected data for the configured pattern/mode.
- DUT behavior: baseline values are plausible and a known controlled stimulus
  or error injection causes the expected decoded response. Network success
  cannot prove this on its own.
- Capacity: inspect accepted/consumed counters, queued/latched records, and
  full-FIFO stall cycles. Reconcile counts accounting for any remaining FIFO
  data. Stalls mean backpressure and may pause acquisition; they are not a
  direct measurement of lost DUT events. UDP has no retransmission.

Use a **fresh receiver process and log directory for each reset/restart
session**. Sender sequences start at zero by default; FPGA reset restarts its
local timestamp. Do not reset the FPGA while an active sender accesses UIO.

If no packets arrive, check in order: HPS boot -> FPGA configured -> bridge
enabled/UIO mapped -> sender validation -> network addressing/firewall ->
receiver. If packets arrive but data is wrong, inspect DUT wiring, controls,
producer handshakes and SRAM timing with suitable instruments/SignalTap.

After low-rate correctness is established, increase load and then add boards.
Use unique board IDs 1..12 and addresses `192.168.1.101` through `.112`.
Timestamps are local to each board and are not synchronized by Ethernet.

See [the project README](../N3-Codes-Ethernet/ethernet/README.md) and
[validation limits](../N3-Codes-Ethernet/ethernet/VALIDATION.md) for details.

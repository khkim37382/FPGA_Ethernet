# FPGA Ethernet — N3 acquisition

N3 acquisition over Ethernet for the **DE10-Standard (Cyclone V SoC)**, with
Athena LSB, Athena FFMCU, Athena PUF, and Zeus LSB revisions.

**Status:** local HDL/software checks pass. Physical DE10 Linux boot, key-based
SSH, and a five-record HPS-to-Mac Ethernet smoke test also pass. Quartus IP
generation/fitting/timing, matching custom N3 HPS/UIO integration and physical
N3 daughtercard acquisition remain unverified. No hardware-validated N3 bitstream
is included.

## Start here

- [Setup lessons and Windows/Linux portability](docs/SETUP_LESSONS.md): what we
  learned on the physical board, verified results, and moving to another host.
- [Reusable FPGA setup skill](skills/fpga-board-setup/SKILL.md): identifies the
  laptop OS and selects its macOS, Windows or Linux procedure.

- [Hardware testing and Mac workflow](docs/FPGA_TESTING.md): build, program,
  configure HPS Linux, collect on your Mac, and check a first-board run.
- [N3 Ethernet project](N3-Codes-Ethernet/ethernet/README.md): architecture,
  register map, all four variants, deployment and decoding.
- [Validation record](N3-Codes-Ethernet/ethernet/VALIDATION.md): checks already
  performed and their limits.
- [Original wiring notes](N3-Codes-Ethernet/README.md): legacy daughtercard
  connections; use the actual DE10 top-level source for switch mappings.
- [Import scope](docs/IMPORT_NOTES.md): what is included and excluded.

## Local software checks

With Python 3.10+, a C11 compiler, and Verilator installed:

```sh
cd N3-Codes-Ethernet/ethernet
make test
```

For actual VHDL checks, install GHDL with synthesis support and run
`make hdl-check GHDL=/path/to/ghdl`. Build the HPS executable with
`make arm ZIG=/path/to/zig`, or use the included ARM Linux executable at
`ethernet/build/arm-linux/n3_udp_sender`.

## Mac versus FPGA build host

The Mac can edit and simulate the code, SSH into the DE10, receive Ethernet
packets, and decode logs. Quartus runs on supported Windows/Linux hosts, so
use one of those machines for the FPGA build and initial Quartus programming.
The DE10's HPS runs its own ARM Linux system; it does not run macOS.

Upstream N3 source and vendor notices are retained in the project. See the
[Terasic reference provenance](N3-Codes-Ethernet/ethernet/board/terasic/SOURCE.json)
for the included board configuration references.

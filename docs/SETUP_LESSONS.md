# DE10 setup notes and lessons — 2026-11-16

**Verified:** the DE10-Standard boots Linux, accepts SSH over Ethernet, and runs
our freshly cross-built ARM sender. The Mac received and decoded its five
simulated records with an exact byte match.

**Still outstanding:** Quartus build/fitting/timing, custom N3 HPS handoff and
UIO integration, physical N3 acquisition, and sustained-load testing. No N3
daughtercard was attached. This was an HPS/network smoke test, not an FPGA/DUT
acquisition test. Windows/Linux host operation is documented but has not been
physically tested in this session.

## What we learned

| Observation | Resolution / reusable lesson |
|---|---|
| The old 4 GB card had boot files but no Linux root partition. | Inspect partition layout before assuming an SD card boots Linux. Use an exact-board official whole-card image when reimaging is justified. |
| macOS administrator authentication still produced EPERM on the raw SD device. | Root access and macOS privacy access are distinct. Prepare the operation and use an authorized Terminal; do not repeatedly change tools to evade the denial. |
| The stock image did not give eth0 an IP address. | For a headless direct link, provision static addressing and SSH before first boot. A cable alone supplies no DHCP service. |
| Ethernet showed 1 Gbit/s before we could log in. | Carrier, IP, ping, TCP, SSH and application data are separate verification stages. |
| The UART device did not enumerate on the Mac. | Check power, correct port, USB data cable and accessory permissions; do not assume a driver is the cause. UART is optional when Ethernet-only access can be provisioned. |
| The first SSH greeting timed out, but a longer bounded retry worked. | Allow first-boot initialization time. Host-key generation is a plausible explanation here, not a confirmed root cause. |
| The FPGA build tools were unavailable natively on macOS. | Do local HDL/software validation on the Mac and compile/program the FPGA through a supported Quartus host. |
| The HPS ARM executable worked even though the host was Apple Silicon. | Keep host and board architectures distinct. The receiver runs on the laptop; the ARM Linux sender runs on the DE10. |
| Five records arrived exactly over the physical link. | Record the tested payload/count and scope. This proves the HPS-to-Mac path for this smoke test, not UIO or real N3 acquisition. |

## Verified direct-link settings

| Item | Value in this run |
|---|---|
| Laptop Ethernet | 192.168.50.1/24 |
| DE10 HPS eth0 | 192.168.50.2/24 |
| Link | 1000baseT full duplex |
| SSH | root with a dedicated ECDSA client key; password login disabled |
| Board OS | Linux 4.5.0-00200-g1ec9f95, ARMv7 |
| Receiver | UDP 5000; standard-library Python 3.10+ |
| Test payload | 5 simulated records, 140 bytes, 1 datagram |
| Result | exact payload match, correct source IP, no sequence gaps in this run |

The example addresses are a local convention, not firmware or FPGA constants.
The [direct-link receiver config](../N3-Codes-Ethernet/ethernet/multi_fpga_receiver/config/direct_link_192_168_50.json)
is separate from the original 192.168.1.x twelve-board configuration.

See the [DE10 reference](../skills/fpga-board-setup/references/de10-standard.md)
for the inspected image details, static-network file, SSH provisioning and
bounded first-boot troubleshooting. The [portable evidence report](evidence/de10_hps_ethernet_2026-11-16.json)
contains the observed smoke-test counts and binary hashes without machine paths
or SSH credentials.

## Move the board to Windows or Linux

For the full copy-and-paste Windows procedure without Codex, use the
[Windows README](../README_WINDOWS.md), including the one-time new-key
bootstrap through the trusted Mac or UART.

Yes: keep the same DE10 SD card and ARM sender. Changing the host OS does not
require recompiling the FPGA design or converting the ARM executable into a
Windows/Linux host binary. The new host runs the Python receiver/decoder.

1. Generate a dedicated client key on the new host and authorize its **public**
   key through the still-working trusted Mac connection before moving the board.
   Keep the board host-key verification information. Private keys are not in Git.
2. Configure the new wired NIC as 192.168.50.1/24 if retaining the board's
   192.168.50.2 address. Avoid duplicate host IPs. Keep Wi-Fi/default routes intact.
3. Install Python 3.10+ and an SSH client; allow incoming UDP 5000 for the
   acquisition interface. No extra Python packages are needed for this receiver.
4. Use the direct-link config and a new log directory. On Linux use `python3`;
   on Windows use the installed launcher, commonly `py -3`.
5. Start the sender through SSH with `--dest` set to the new host's actual IP.
   Check exact fixture bytes before proceeding to real acquisition.

Host-specific procedures:
[macOS](../skills/fpga-board-setup/references/macos.md),
[Windows](../skills/fpga-board-setup/references/windows.md),
[Linux](../skills/fpga-board-setup/references/linux.md).

For FPGA generation/programming, check the exact Quartus version's
[official OS support matrix](https://www.altera.com/developers/software/os-support).
The project currently specifies Quartus 23.1 with Cyclone V support. Native
Windows/Linux hardware and drivers still need their own setup; Windows on ARM
or an arbitrary Linux architecture is not automatically supported.

## Reusable setup skill

The versioned [fpga-board-setup skill](../skills/fpga-board-setup/SKILL.md)
starts by identifying and announcing the laptop OS/architecture, then selects
its macOS, Windows or Linux setup section. Board-specific details are separate
so these DE10 lessons do not become incorrect defaults for another FPGA.

The skill is also installed locally under `~/.codex/skills/fpga-board-setup`.
On another machine, install/copy the entire `skills/fpga-board-setup` directory
into that machine's Codex skills directory. Invoke it as `$fpga-board-setup`.
Add future observed lessons to the relevant OS/board reference and distinguish
verification from inference. Publishing subsequent updates requires authorization.

SD backups/images, private keys, known_hosts snapshots and the original
machine-specific raw-write scripts stay local. Those scripts contain target
identities and host paths that must not become generic flashing instructions.

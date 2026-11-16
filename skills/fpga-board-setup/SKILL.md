---
name: fpga-board-setup
description: Bring up physical FPGA development boards, prepare matching boot media, and verify serial, SSH, or Ethernet access from macOS, Windows, or Linux. Use for first-board setup, headless access, and moving an existing board between host computers.
---

# FPGA board setup

Bring up the requested board and demonstrate the required data path. Distinguish
host software, board operating system, programmable logic, and daughtercard/DUT.
An Ethernet carrier or a successful software replay does not verify FPGA logic.

## Select the laptop operating system first

Detect the OS and CPU architecture of the computer actually attached to the
board. Use local system information (`uname` on Unix; `$PSVersionTable` and
`[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture` on Windows). If the user describes a different or
remote computer, identify which computer will build, program, and receive data.

State the selection before setup: **“Host: <macOS/Windows/Linux>, <architecture>.
Board: <model>; board OS: <known/unknown>. I’m using the <OS> setup section.”**
Do not infer the board OS from the laptop OS. Follow only the applicable host
section below and read its linked reference. On another laptop, detect again;
do not carry over interface names, disk identifiers, addresses, or credentials.

### macOS host

Read [macos.md](references/macos.md). Use `diskutil` to inspect removable media,
`networksetup`/`ifconfig` to identify the actual wired NIC, and `/dev/cu.*` plus
USB enumeration to distinguish a missing cable/device from a missing driver.
Quartus has no native macOS build; route that stage to a supported build host.
If raw disk access returns EPERM even as administrator, prepare and verify the
operation, then hand it to an authorized Terminal with the required macOS
privacy access. Never change security controls to bypass the denial.

### Windows host

Read [windows.md](references/windows.md). Use PowerShell disk/NIC inventory and
Device Manager/COM ports. Verify the CPU and exact Quartus release support;
Windows on ARM is not interchangeable with a supported x64 installation.
Use native Windows Python for a directly attached Ethernet receiver unless a
WSL network path has actually been checked. Apply firewall access to the
specific receiver/port/interface, rather than disabling the firewall.

### Linux host

Read [linux.md](references/linux.md). Identify media with `lsblk`, wired NICs
with `ip`, and console devices with `/dev/serial/by-id` or `ttyUSB`/`ttyACM`.
Use the distribution's active network manager and its privilege mechanism.
Match Quartus version, architecture, device support and programmer permissions.
Use fresh disk inventory before writes; disk names may change after reinsertion.

## Identify the board and reuse relevant evidence

Confirm exact model/revision/FPGA, whether it has an HPS/CPU, available boot
media, power, cables and required daughtercard. A DE10-Standard, DE10-Nano and
DE10-Lite are different targets. Prefer project files and official board
sources over guessed pinouts, images, boot switches or physical addresses.

For DE10-Standard/N3, read [de10-standard.md](references/de10-standard.md).
Its addresses and filenames describe a verified example, not universal FPGA
settings. Do not apply an ARM Linux workflow to a board without an HPS/CPU.

## Prepare and operate within the authorized scope

- Inventory media and read current contents before selecting an image. For an
  authorized destructive write, identify external/removable status, capacity,
  partition layout and hardware identity; revalidate immediately before writing.
  Never embed this session's `disk4`, `en10`, or USB identifier in a reusable
  destructive command.
- Prepare a concrete operation before requesting any necessary OS interaction.
  Back up existing data when feasible; verify the backup, image capacity and
  source/integrity, then verify the written bytes. Do not claim completion after
  preparing a script or starting an imager. Preserve a result report and eject.
- Use a matching official boot image to establish CPU/Linux/network operation.
  Custom FPGA/HPS peripherals can also require matching handoff, bootloader,
  device tree and enabled bridges. Stock Linux is not a complete custom design.
- For Ethernet-only access, prepare addressing and remote login before first
  boot if the image does not configure them. UART is a useful fallback, not a
  universal prerequisite. Keep console login and remote SSH authentication
  distinct; a blank local root password is not an SSH provisioning strategy.
- Generate keys locally and install only public authorization on the board.
  Keep private keys, host private keys, disk images, backups and user-specific
  machine snapshots out of repositories and skills. Authorize a new laptop's
  public key through an existing trusted connection before moving the board.

## Verify in stages and record the boundary

Check carrier -> IP/ARP -> ping -> TCP port -> SSH greeting -> host identity ->
login. A missing USB device is not repaired by installing a serial driver;
check power, connector, data cable and accessory permission first. An initial
SSH greeting timeout can be first-boot key generation: make a bounded retry
before changing configuration or declaring the network broken.

Run a known replay through the actual board CPU sender and host receiver; verify
source IP, packet validation, sequence accounting, complete binary payload and
decoding. Label fixture records as simulated. Use a fresh receiver/log session
for sender sequence resets. Then test FPGA MMIO/UIO and DUT acquisition only
when the new bitstream/boot artifacts and required hardware exist.

Report separately what passed, what was inferred, and what remains untested.
Record new observed lessons in the relevant OS or board reference, with date,
trigger, resolution and verification limits. Avoid turning one board's workaround
into a requirement for all boards. Publishing updates requires user authorization.

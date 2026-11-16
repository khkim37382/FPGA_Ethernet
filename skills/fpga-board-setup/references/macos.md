# macOS laptop setup

Announce the host OS/architecture selection from SKILL.md before acting.

## Inventory and tools

- `uname -m` and `sw_vers`: identify Apple Silicon versus Intel and macOS version.
- `diskutil list external physical`, then `diskutil info -plist <device>`:
  identify card, size, external/removable status and hardware path. Inspect
  partitions; visible FAT boot files alone do not establish a Linux rootfs.
- `networksetup -listallhardwareports`, `networksetup -getinfo <service>`, and
  `ifconfig <actual-interface>`: identify the wired adapter, carrier and IP.
- `ls /dev/cu.*` and targeted USB inventory: verify a serial device enumerates.
  On DE10-Standard the FT232R console uses Mini-B UART TO USB, distinct from
  USB-Blaster and USB host ports. Check accessory prompts and a data cable.

Use available Python 3.10+, a C compiler and Verilator for this N3 project's
software checks; GHDL with synthesis support is required for its VHDL checks.
A host-native sender executable cannot run on the ARM HPS. Cross-build for the
board CPU or use a verified matching binary. Quartus requires a supported
Windows/Linux host; do not claim that an ARM VM resolves tool/driver support.
Check official release support before installing toolchains.

## SD write and privacy permission

Observed 2026-11-16: root obtained through administrator authentication could
unmount the SD card but opening its raw device still returned EPERM. This was
an OS privacy/access boundary, not evidence of a corrupt image. No bytes had
been written. The prepared operation succeeded when the user ran it with sudo
from an authorized Terminal. If needed, the user can grant Terminal Full Disk
Access in Privacy & Security and reopen it. Never request their password in chat.
Do not repeatedly switch tools or alter security controls to bypass the denial.

A write helper must rediscover/validate the current device and partitions,
back up before writing, stop on errors, verify readback, and eject. The original
session used disk4; that name must not become a reusable default. Prefer a
partition-only offline update when changing Linux configuration and preserving
bootloader/FAT partitions. `debugfs`/`e2fsck` can inspect and update a copied
ext filesystem on macOS; do not run filesystem repair against mounted media.

Homebrew's GHDL cask was disabled during this session. A project-local official
GHDL release archive was checked against its published SHA256 and ran without
changing Gatekeeper settings. This is an observed option, not a requirement to
bypass any current OS block. Check release architecture/dependencies afresh.

## Ethernet and SSH

The verified direct-link example uses host 192.168.50.1/24 and board
192.168.50.2/24, with no gateway needed. Preserve Wi-Fi and its default route.
Do not assume a direct cable supplies DHCP. Inspect current configuration and
provision the board's address plus SSH authorization when needed.

Use the host's actual address in receiver bind configuration and sender
`--dest`. Allow incoming UDP 5000 for the receiver if macOS prompts/blocks it.
A physical 1000baseT link alone does not establish Linux boot or an IP address.

For a new Mac, generate its own key and authorize the public key through an
existing trusted board login. Use a per-board known_hosts entry verified against
its expected host public key; do not disable host-key checking globally.

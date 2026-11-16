# DE10-Standard / N3 example

Use these details only after confirming a Cyclone V SoC DE10-Standard. They are
not images, pinouts or defaults for DE10-Nano, DE10-Lite or arbitrary FPGA boards.
Read the selected host-OS reference as well.

## Observed setup and verification — 2026-11-16

- Host: Apple Silicon macOS; DE10-Standard with no N3 daughtercard attached.
- Official source: [Terasic Linux Console archive](https://download.terasic.com/downloads/cd-rom/de10-standard/Linux/DE10-Standard_Linux_Console.zip).
  [Board resources](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=205&No=1081&PartNo=4)
  identify the console BSP as kernel 4.5 and support 4 GB media.
- The 4,026,531,840-byte card initially had A2 and FAT partitions, some boot
  artifacts and free space, but no Linux root partition. Reimaging was justified
  by inspection, not by an assumption that every old card needs erasure.
- Official image size: 1,600,126,976 bytes. Layout: A2 preloader partition at
  sector 2048, FAT at sector 4096, Linux root at sector 1028096. Sector size is
  512 bytes. These are this image's values; re-read any new image/card metadata.
- ZIP SHA256: `9bfffcdcc62475b7f0c709ede5d9f3708c70846b2fb13f27ca9d415a7b0e2e9d`.
  Unmodified image SHA256: `9755a127cdc9e7f6f526eb132a0e5d720e5155dfcbaf56e19b6f473eb8c3abf8`.
  These were measured locally after HTTPS download and ZIP CRC validation, not
  verified against an independent vendor-published SHA256.
- Backups and complete write readbacks were verified. N3 tools and an explicitly
  labeled simulated fixture were staged in FAT. A later partition-only update
  backed up and modified Linux without rewriting A2/FAT boot partitions.
- USB UART never enumerated on this Mac during bring-up. Ethernet-only access
  subsequently worked, so a console cable was not a prerequisite for this run.
- Physical carrier was 1000baseT full duplex. Mac: 192.168.50.1/24, DE10:
  192.168.50.2/24. Linux boot and public-key-authenticated root SSH succeeded.
- Board reported Linux `4.5.0-00200-g1ec9f95`, `armv7l`, hostname `socfpga`.
- A fresh ARMv7/Cortex-A9 static sender build ran on the actual HPS and sent five
  simulated RTL-fixture records in one UDP datagram to host port 5000. All 140
  payload bytes matched exactly, source IP matched, decoding succeeded and no
  sequence gaps occurred in this smoke test. No throughput claim follows.
- Not tested: the new N3 FPGA/HPS system, Quartus generation/fitting/timing,
  matching custom handoff/UIO/bridge access, daughtercard acquisition or sustained
  throughput. The stock BSP boot does not validate the new DDR/RGMII configuration.

## Headless Linux network configuration

The inspected stock image had systemd-networkd and sshd.socket enabled, but an
empty `/etc/systemd/network/` directory. ConnMan's service explicitly excluded
eth0 (`connmand ... -I eth0`). A direct cable supplied no DHCP server. This
explains why carrier appeared before a usable board address.

After verifying these services in the actual image, place this example at
`/etc/systemd/network/10-n3-eth0.network` (root-owned, mode 644):

```ini
[Match]
Name=eth0

[Network]
Address=192.168.50.2/24
DHCP=no
LinkLocalAddressing=no
```

Confirm the real board interface name before reuse. Use another private subnet
if this one conflicts with the host's existing network. No default gateway is
needed for the isolated direct link.

For the observed image, root's home is `/home/root`. Provision a dedicated
client public key in `/home/root/.ssh/authorized_keys` with root ownership,
`.ssh` mode 700 and authorized_keys mode 600. We used ECDSA nistp256, supported
by this older OpenSSH and the modern host. A board ECDSA host key was provisioned
locally and its public key pinned in a per-board host known_hosts file. No
private keys belong in a repository, skill or published image.

The SSH configuration explicitly selected the host key and public-key auth:

```text
HostKey /etc/ssh/ssh_host_ecdsa_key
PermitRootLogin without-password
PubkeyAuthentication yes
AuthorizedKeysFile /home/root/.ssh/authorized_keys
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
```

Retain needed vendor settings, validate options against the actual sshd version,
and preserve other authorized users/keys. These directives describe the tested
image; they are not a universal policy for every board or lab. Terasic's blank
root console password did not provide our configured remote key authentication.

For offline edits, copy/backup the current root partition, verify the backup,
check/repair the offline copied filesystem as appropriate, apply changes, inspect
file contents/ownership/modes and run a read-only filesystem check. Revalidate
the physical partition identity before writing, then verify its full readback.
Do not reuse the original session's hard-coded flash scripts for another card.

## Reconnect and test

Check carrier, the host's wired address, ARP/ping, then SSH separately. First
SSH contact timed out during the greeting; a bounded retry with a 30-second
connection timeout succeeded. The image's `sshdgenkeys.service` runs
`ssh-keygen -A` when host key files are missing, so first-boot key generation
was a plausible cause, not a proven diagnosis. A greeting timeout is distinct
from connection refused, an unknown host key or failed authentication.

On a trusted SSH connection, inspect `uname -a`, `ip -4 addr show eth0`,
`ip route`, `lsblk` and the actual `/dev/uio*` devices. Do not access an arbitrary
UIO node merely because one exists.

The staged tools in this run were copied from the FAT partition to
`/home/root/n3-tools`. After confirming the actual boot partition, mount FAT
read-only for copying and unmount it afterward. The original packet fixture
was named `SIMULATED_records.bin` to avoid implying DUT measurements.

In the N3 repository, the checked-in receiver config
`multi_fpga_receiver/config/direct_link_192_168_50.json` matches this direct link.
From `N3-Codes-Ethernet/ethernet/multi_fpga_receiver`, start the receiver:

```sh
python3 receiver.py --config config/direct_link_192_168_50.json --log-dir ../logs/new_session
```

Then, on this configured DE10:

```sh
/home/root/n3-tools/n3_udp_sender --input /home/root/n3-tools/SIMULATED_records.bin --id 1 --dest 192.168.50.1
```

Stop and use a fresh receiver/log directory before replaying again. Verify exact
fixture bytes, source IP, packet validation and record decoding. Real N3 data
must wait for the correct FPGA revision and UIO mapping. The bridge's relative
Qsys offset 0x10000 is not a Linux physical address; derive the resource from
fresh generated metadata. Never use the stock FPGA image as evidence that the
new `N3_Ethernet` project is programmed.

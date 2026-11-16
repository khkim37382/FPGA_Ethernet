# Linux laptop setup

Announce Linux distribution and architecture before acting. The workflow below
is a portability recipe; this session's physical host run was on macOS.

## Inventory and tools

Use `uname -m` and `/etc/os-release` for host information. Inspect removable
media using `lsblk -o NAME,SIZE,MODEL,TRAN,RM,MOUNTPOINTS` and, where available,
`/dev/disk/by-id`. Inspect wired interfaces with `ip -br link`/`ip -br addr` and
routes with `ip route`. Serial consoles may appear under `/dev/serial/by-id`,
`ttyUSB*`, or `ttyACM*`; access groups/udev rules depend on the distribution.

Before an authorized image write, identify the whole disk and its partitions,
unmount the target partitions, verify capacity/source and backup/readback.
Never guess `/dev/sdX` from the earlier Mac's disk number. Use Linux-native
imaging/ext-filesystem tools with appropriate privileges; the Mac raw-device
script and device paths are not portable.

Install Python 3.10+ and an OpenSSH client when needed. The N3 receiver/decoder
use the standard library. FPGA compilation/programming additionally needs the
project's Quartus edition/version, a supported CPU/distribution, device support,
USB-Blaster permissions and any required host libraries. Verify the exact
release matrix rather than assuming all Linux/ARM systems run Quartus.

## Reuse an already-provisioned DE10

The DE10 keeps its own ARM Linux SD image and FPGA configuration. Moving from
macOS to Linux does not require reimaging or rebuilding board software.

1. Generate a dedicated client key for login, for example:

   ```sh
   ssh-keygen -t ecdsa -b 256 -f ~/.ssh/de10_n3
   ```

2. While the previous trusted host still connects, append this new `.pub` key
   to the board's `/home/root/.ssh/authorized_keys`. Preserve existing keys,
   root ownership and modes 700/600. Verify the board's host identity on the
   new laptop; do not distribute private keys in the repository or skill.
3. Use the distribution's active network manager to configure the actual
   wired NIC as 192.168.50.1/24 for the example DE10 at 192.168.50.2. Do not
   run NetworkManager and systemd-networkd against the same NIC accidentally.
   Keep the Internet/default route on its existing adapter; no gateway or DNS
   is needed for this direct link. Disconnect another host using the same IP.
4. Verify carrier, ping and `ssh -i ~/.ssh/de10_n3 root@192.168.50.2`. A first
   greeting timeout can be key generation; use a bounded retry. Authorize the
   new key before moving the board if its SSH policy is already key-only.
5. Allow incoming UDP 5000 on the acquisition NIC with the distribution's
   actual firewall manager if required. Do not disable the firewall globally.
6. From `N3-Codes-Ethernet/ethernet/multi_fpga_receiver`, start:

   ```sh
   python3 receiver.py --config config/direct_link_192_168_50.json --log-dir ../logs/linux_run_001
   ```

7. On the DE10, use the receiver's actual address. For the staged replay:

   ```sh
   /home/root/n3-tools/n3_udp_sender --input /home/root/n3-tools/SIMULATED_records.bin --id 1 --dest 192.168.50.1
   ```

Use a new receiver/log directory when replaying again. Check packet accounting
and exact payloads, then decode using the same Python decoder and actual variant.
The board ARM executable runs on the DE10, not on an x86 Linux laptop.

Official Quartus host matrix:
https://www.altera.com/developers/software/os-support

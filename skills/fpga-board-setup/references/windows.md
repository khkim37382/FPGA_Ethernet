# Windows laptop setup

Announce Windows and CPU architecture before acting. The workflow below is a
portability recipe; this session's physical run was performed from macOS.

## Inventory and tools

Use `$PSVersionTable` and
`[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture` for host
information. A process architecture environment variable alone can describe an
emulated shell rather than the actual OS architecture.
Inspect disks with `Get-Disk`/`Get-Partition`, wired NICs with `Get-NetAdapter`
and `Get-NetIPConfiguration`, and console ports in Device Manager. Reidentify
media immediately before an authorized image write; preserve a backup and
verify readback. Do not translate a Mac disk number into a Windows disk number.
Use an appropriate Windows imager for the selected official whole-card image;
the Mac raw-device scripts and debugfs installation paths are not portable.

Use Python 3.10+ and OpenSSH Client if available; check `py -3 --version` and
`ssh -V`, installing missing tools through the user's normal setup process.
The N3 receiver/decoder use Python's standard library. Run the receiver with
native Windows Python for a direct cable unless WSL networking has been verified.

For Quartus builds/programming, check the exact Windows release, CPU architecture,
Quartus edition/version, Cyclone V support and USB-Blaster driver. Supported
Windows x64 and Windows on ARM are different cases. The N3 project targets
Quartus 23.1; do not silently replace it with the newest release.

## Reuse an already-provisioned DE10

The DE10 keeps its own ARM Linux SD image and FPGA configuration when moving
hosts. Neither becomes a Windows executable. Do not rebuild or reimage solely
because the laptop changed.

1. On the new PC, generate a dedicated supported SSH key, for example:

   ```powershell
   ssh-keygen -t ecdsa -b 256 -f "$env:USERPROFILE\.ssh\de10_n3"
   ```

2. Before disconnecting the trusted old host, append the new `.pub` key to
   `/home/root/.ssh/authorized_keys` on this DE10. Preserve authorized keys,
   root ownership, directory mode 700 and file mode 600. Verify the expected
   board host public key/fingerprint on the new host. Never publish private keys.
3. Configure the actual wired adapter as 192.168.50.1/24 if reusing the example
   board at 192.168.50.2. Do not assign 192.168.50.1 to two active hosts on the
   same network. No gateway/DNS is needed for the direct board link; keep the
   Internet route on its existing adapter.
4. Check `ping 192.168.50.2`, then
   `Test-NetConnection 192.168.50.2 -Port 22`, and log in with the new key:
   `ssh -i "$env:USERPROFILE\.ssh\de10_n3" root@192.168.50.2`.
   A blank console password does not override the board's key-only SSH policy.
5. Permit inbound UDP 5000 for the Python receiver on the acquisition interface/
   appropriate network profile. Keep the firewall enabled. Administrative
   adapter/firewall changes require the host's normal privilege mechanism.
6. From `N3-Codes-Ethernet/ethernet/multi_fpga_receiver`, run:

   ```powershell
   py -3 receiver.py --config config/direct_link_192_168_50.json --log-dir ../logs/windows_run_001
   ```

7. On the DE10, point the ARM sender at the new receiver's actual address. For
   the already-installed simulated replay example:

   ```sh
   /home/root/n3-tools/n3_udp_sender --input /home/root/n3-tools/SIMULATED_records.bin --id 1 --dest 192.168.50.1
   ```

Stop and use a fresh receiver/log directory for the next replay. The sender
restarts its packet sequence at zero. Decode on Windows with `py -3` using the
same decoder arguments; choose the actual board variant for real acquisition.

Official Quartus host matrix:
https://www.altera.com/developers/software/os-support

# Windows setup, Ethernet test, and Quartus guide — DE10-Standard / N3

This guide works **without Codex**. Use Windows PowerShell/Windows Terminal,
SSH, Python, and Quartus. Commands are labeled by the computer where they run.
Do not paste Linux board commands into a local PowerShell prompt.

**Target:** Terasic **DE10-Standard**, Cyclone V SoC `5CSXFC6D6F31C6`.
DE10-Lite and DE10-Nano are different boards and are not drop-in substitutes.

## What you can complete

| Stage | What it proves | Current status |
|---|---|---|
| A: existing SD + Windows receiver + board replay | Linux boot, SSH, ARM sender, Ethernet, capture and decode | Same path passed from macOS; Windows steps below are not yet physically tested |
| B: Quartus generation, compilation and programming | A newly built `N3_Ethernet` FPGA image | Workflow prepared; actual Quartus build/timing still outstanding |
| C: matching HPS boot/UIO + real N3 daughtercard | Live FPGA/DUT acquisition | Requires target-matched boot integration and physical validation; no ready-made custom SD image is supplied |

Start with **Stage A**. You do not need Quartus, USB-Blaster or the daughtercard
for the simulated Ethernet replay. Moving the board from Mac to Windows does
not require erasing its working SD card. The board continues running ARM Linux;
Windows runs the receiver, SSH client and FPGA build tools.

Contents: [prerequisites](#1-hardware-and-windows-tools),
[network](#3-configure-the-direct-ethernet-link),
[SSH authorization](#4-authorize-this-windows-computer-for-ssh),
[replay](#5-stage-a--test-physical-ethernet-with-simulated-records),
[Quartus](#6-stage-b--install-and-build-with-quartus),
[programming](#7-program-the-fpga-through-usb-blaster),
[live acquisition](#8-stage-c--matching-hps-boot-and-uio-integration),
[troubleshooting](#10-troubleshooting),
[new SD/UART recovery](#11-optional-new-sd-card-or-uart-recovery).

## 1. Hardware and Windows tools

Have the DE10-Standard's normal power supply, prepared microSD card, Ethernet
cable, and a Windows wired NIC or USB-to-Ethernet adapter. For FPGA programming,
add a USB data cable to the **USB-Blaster** port. The separate **UART TO USB
Mini-B** port is an optional Linux console, useful for recovery. Neither USB
connection replaces the board power supply.

Prefer a supported **Windows x64** machine for Quartus 23.1. Check your system:

**Windows — normal PowerShell:**

```powershell
$PSVersionTable.PSVersion
[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version
```

Windows on ARM may run the Python client, but do not assume it supports the
Quartus/USB-Blaster installation below. Verify the exact release against the
[official Quartus OS support matrix](https://www.altera.com/developers/software/os-support).

Check for Git, Python 3.10+ and the OpenSSH client:

```powershell
git --version
py -3 --version
ssh -V
```

If Git/Python are missing and WinGet is available, install them and then open
a **new PowerShell** so PATH changes take effect:

```powershell
winget install --exact --id Git.Git
winget install --exact --id Python.Python.3.13
```

Python 3.13 is a suitable example, not a requirement; any supported 3.10+
installation works. This receiver needs **no pip packages**.

If `ssh` is missing, install the Windows OpenSSH Client optional feature:

**Windows — Administrator PowerShell:**

```powershell
Get-WindowsCapability -Online | Where-Object Name -Like 'OpenSSH.Client*'
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

This installs the **client**; no Windows SSH server is needed. See
[Microsoft's OpenSSH installation instructions](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).

## 2. Clone the repository

Use a short, writable local path outside OneDrive/network folders. The examples
use `C:\FPGA\FPGA_Ethernet`; change it consistently if needed.

**Windows — normal PowerShell:**

```powershell
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force C:\FPGA | Out-Null
Set-Location C:\FPGA
git clone https://github.com/khkim37382/FPGA_Ethernet.git
Set-Location C:\FPGA\FPGA_Ethernet
$Repo = (Get-Location).Path
py -3 tools\replay_fixture.py --help
```

If the repository is private, authenticate Git with your GitHub account using
its normal credential flow. Never put a token in a command saved in this README.
If already cloned, use `git pull --ff-only` after checking for your local edits.

Every **new PowerShell window** used below should initialize:

```powershell
$ErrorActionPreference = 'Stop'
$Repo = 'C:\FPGA\FPGA_Ethernet'
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
Set-Location $Repo
```

## 3. Configure the direct Ethernet link

Power off the DE10 before inserting its SD card, insert the **already-prepared
card**, connect Ethernet directly to the Windows NIC, and power it on. Give
Linux time to boot. Disconnect the Mac's direct board cable before using the
same host IP on Windows.

| Device | IPv4 address | Prefix |
|---|---|---|
| Windows acquisition NIC | `192.168.50.1` | `/24` (255.255.255.0) |
| Prepared DE10 `eth0` | `192.168.50.2` | `/24` |
| Receiver | UDP `5000` | board ID `1` |

A direct cable supplies no DHCP server. Keep your Internet connection on Wi-Fi
or another NIC. No gateway/DNS is needed for this isolated board link. If an
existing VPN/LAN uses this subnet, stop and choose a nonconflicting subnet,
updating board, Windows, receiver config and sender destination together.

**Windows — Administrator PowerShell:**

```powershell
$ErrorActionPreference = 'Stop'
Get-NetAdapter -Physical | Format-Table ifIndex, Name, Status, LinkSpeed
$IfIndex = [int](Read-Host 'Enter the ifIndex of the WIRED adapter connected to the DE10')
$Nic = Get-NetAdapter | Where-Object ifIndex -eq $IfIndex
if (@($Nic).Count -ne 1) { throw 'Select exactly one wired adapter.' }
$Nic | Format-Table ifIndex, Name, Status, LinkSpeed
Get-NetIPConfiguration -InterfaceIndex $IfIndex
Get-NetIPAddress -InterfaceIndex $IfIndex -AddressFamily IPv4
```

Confirm the selection is the dedicated board adapter, **not Wi-Fi**. Save its
current settings before modifying it. The next block replaces IPv4 address/
gateway configuration on this selected dedicated adapter. If it already has
another static setup you need, review that setup before proceeding:

```powershell
$NicBackup = Join-Path ([Environment]::GetFolderPath('Desktop')) 'de10-nic-before.txt'
Get-NetIPConfiguration -InterfaceIndex $IfIndex |
    Format-List * | Out-File $NicBackup
Get-NetIPInterface -InterfaceIndex $IfIndex -AddressFamily IPv4 |
    Format-List * | Out-File $NicBackup -Append
netsh interface ipv4 set address "name=$($Nic.Name)" source=static address=192.168.50.1 mask=255.255.255.0 gateway=none store=persistent
if ($LASTEXITCODE -ne 0) { throw 'Static Ethernet configuration failed. Stop and inspect the error.' }
Get-NetIPInterface -InterfaceIndex $IfIndex -AddressFamily IPv4 |
    Format-Table InterfaceIndex, InterfaceAlias, Dhcp, ConnectionState
Get-NetIPAddress -InterfaceIndex $IfIndex -AddressFamily IPv4
if ((Get-NetIPInterface -InterfaceIndex $IfIndex -AddressFamily IPv4).Dhcp -ne 'Disabled') {
    throw 'DHCP is still enabled; do not proceed until this is resolved.'
}
```

If this adapter already had another static address or a default route, review
and restore/reconfigure those settings deliberately; do not delete settings
from unrelated interfaces. See Microsoft's
[New-NetIPAddress](https://learn.microsoft.com/en-us/powershell/module/nettcpip/new-netipaddress)
and [Set-NetIPInterface](https://learn.microsoft.com/en-us/powershell/module/nettcpip/set-netipinterface)
reference for the PowerShell inspection commands. Address configuration above
uses Microsoft's documented
[`netsh interface ipv4 set address`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-interface)
to select static addressing and set the address in one operation.

If an older copy of this guide produced `Inconsistent parameters PolicyStore
PersistentStore and Dhcp Enabled` from `New-NetIPAddress`, use the `netsh` block
above instead. Re-select/confirm the correct NIC if using a new window. Microsoft
notes that `Set-NetIPInterface -Dhcp` changes the active policy store; setting
DHCP on PersistentStore is not a fix. Verify `Dhcp` is Disabled and the address
is 192.168.50.1/24 before testing the board. This fallback is documented, but
its success on the reporting Windows machine still needs confirmation.

Allow the receiver's UDP traffic only on this direct link. The rule uses `Any`
profile because an isolated wired connection may be classified as Public, but
is restricted by interface, local address, remote board address and port:

```powershell
if (-not (Get-NetFirewallRule -DisplayName 'N3 DE10 direct UDP 5000' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'N3 DE10 direct UDP 5000' -Direction Inbound `
        -Action Allow -Protocol UDP -LocalPort 5000 -LocalAddress 192.168.50.1 `
        -RemoteAddress 192.168.50.2 -InterfaceAlias $Nic.Name -Profile Any
}
```

If a matching rule already exists for a different adapter, inspect it and
update that rule; do not disable the firewall. Organizational policy may require
an administrator to permit it. See
[New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule).

**Windows — normal PowerShell:**

```powershell
ping 192.168.50.2
Test-NetConnection 192.168.50.2 -Port 22
```

Expected: ping replies and `TcpTestSucceeded : True`. An active cable without
an IP/SSH response does not establish Linux boot. If the board is unreachable,
use [troubleshooting](#10-troubleshooting) or the UART recovery section.

## 4. Authorize this Windows computer for SSH

The current SD card allows **key-based root SSH**, not password login. Your
Mac key is not in GitHub. A new Windows key must be authorized on the board.
Do this before relying exclusively on the new computer.

### 4.1 Generate the Windows client key

**Windows — normal PowerShell:**

```powershell
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
New-Item -ItemType Directory -Force (Split-Path $Key) | Out-Null
if (-not (Test-Path $Key)) {
    ssh-keygen -t ecdsa -b 256 -f $Key -C 'de10-windows-client'
    if ($LASTEXITCODE -ne 0) { throw 'Key generation failed.' }
}
Get-Content "$Key.pub"
```

Choose a passphrase when prompted if desired. Keep the private file `$Key` on
Windows; copy only **`de10_n3.pub`** to the trusted Mac, for example via a USB
stick, saving it as `~/Downloads/de10_windows.pub`. The public key must be one
complete line. Do not replace the board's existing authorized keys.

### 4.2 Add it through the trusted Mac (one-time)

Temporarily reconnect the board Ethernet cable to the Mac, whose wired IP is
still `192.168.50.1`. No Codex is needed. The following path is the SSH setup
created in this session; adjust it if that folder moved.

**Mac Terminal — not Windows PowerShell:**

```sh
scp -F "$HOME/ISDE/de10-sd-prep/ssh/config" \
    "$HOME/Downloads/de10_windows.pub" de10-n3:/tmp/de10_windows.pub
ssh -F "$HOME/ISDE/de10-sd-prep/ssh/config" de10-n3
```

Now at the **DE10 Linux prompt**:

```sh
mkdir -p /home/root/.ssh
chmod 700 /home/root/.ssh
tr -d '\r' < /tmp/de10_windows.pub > /tmp/de10_windows.clean.pub
ssh-keygen -lf /tmp/de10_windows.clean.pub
cat /tmp/de10_windows.clean.pub >> /home/root/.ssh/authorized_keys
chown -R root:root /home/root/.ssh
chmod 600 /home/root/.ssh/authorized_keys
exit
```

On the **Mac**, display the already-trusted board host fingerprint:

```sh
ssh-keygen -lf "$HOME/ISDE/de10-sd-prep/ssh/known_hosts"
```

Keep that fingerprint for the Windows first-connection check. If the old Mac
cannot connect, use UART and append the same public key from its Linux console
instead; see [section 11](#11-optional-new-sd-card-or-uart-recovery). Generating a
new key on Windows alone does not authorize it on the board.

### 4.3 Connect from Windows

Move the Ethernet cable back to Windows and, in **normal PowerShell**, run:

```powershell
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
ssh -i $Key -o IdentitiesOnly=yes -o ConnectTimeout=30 root@192.168.50.2
```

Compare the first host-key fingerprint with the trusted fingerprint before
answering `yes`. Do not turn off host-key checking globally. Enter the Windows
key's passphrase if you chose one; this is not the board's root password.

At the **DE10 Linux prompt**, inspect:

```sh
uname -a
ip -4 addr show eth0
ip route
lsblk
ls -l /home/root/n3-tools
```

Expected: ARM Linux, `eth0` at `192.168.50.2/24`, and `/` mounted from the SD
Linux partition. Type `exit` to return to PowerShell. An initial SSH greeting
timeout can occur during first-boot key generation; make a bounded retry with
30 seconds before treating it as a failure.

## 5. Stage A — test physical Ethernet with simulated records

This tests **DE10 HPS CPU -> Ethernet -> Windows receiver -> CSV**. It does
not access UIO, require a daughtercard, or prove that the N3 bitstream is loaded.

### 5.1 Generate and transfer a known fixture

**Windows — normal PowerShell, repository root:**

```powershell
$Repo = 'C:\FPGA\FPGA_Ethernet'
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
Set-Location $Repo
py -3 tools\replay_fixture.py create N3-Codes-Ethernet\ethernet\build\windows\SIMULATED_records.bin
ssh -i $Key -o IdentitiesOnly=yes root@192.168.50.2 'mkdir -p /home/root/n3-tools'
scp -i $Key N3-Codes-Ethernet\ethernet\build\windows\SIMULATED_records.bin root@192.168.50.2:/home/root/n3-tools/
```

The helper creates five synthetic SR-counter records, indices 0..4, counts
10..14, totaling 140 bytes. This fixture is deliberately labeled simulated;
it is different from the earlier five-record RTL fixture in the evidence report.
The new generated fixture SHA256 is
`e7dd539a3389af5a5b0f13adc61df84bd7fba8bd434be0ae16d302a25516ef19`.

The current board already has the freshly built and physically tested sender
at `/home/root/n3-tools/n3_udp_sender`. Check it:

```powershell
ssh -i $Key -o IdentitiesOnly=yes root@192.168.50.2 'ls -l /home/root/n3-tools/n3_udp_sender; sha256sum /home/root/n3-tools/n3_udp_sender'
```

The sender used in our physical run had SHA256
`f8807f49bce5abe00c2bd931d83b016fddad1c157ff3e3cbb90b30a6eafeee5e`.
If the sender is absent, copy the repository's **ARM** binary, not a Mac/Windows
host executable:

```powershell
scp -i $Key N3-Codes-Ethernet\ethernet\build\arm-linux\n3_udp_sender root@192.168.50.2:/home/root/n3-tools/
ssh -i $Key -o IdentitiesOnly=yes root@192.168.50.2 'chmod 755 /home/root/n3-tools/n3_udp_sender'
```

That tracked prebuilt binary has separate provenance in
`N3-Codes-Ethernet/ethernet/build/arm-linux/BUILD.json`; it was not the fresh
binary used in the earlier physical run. The replay test below validates the
binary actually installed. Do not replace the existing working sender merely
to make its hash match a different build.

### 5.2 Start the receiver in PowerShell window A

Use a **new log directory every run**. The receiver appends to existing logs;
it does not create a new sequence session automatically.

```powershell
$Repo = 'C:\FPGA\FPGA_Ethernet'
Set-Location "$Repo\N3-Codes-Ethernet\ethernet\multi_fpga_receiver"
if (Test-Path ..\logs\windows_run_001) { throw 'Use a new run name: this log directory already exists.' }
py -3 receiver.py --config config/direct_link_192_168_50.json --log-dir ../logs/windows_run_001
```

The config binds to Windows `192.168.50.1:5000` and expects board 1 at
`192.168.50.2`. Unconnected boards 2..12 appearing OFFLINE is normal. Do not
use the default 192.168.1.x config for this direct-link test. If the dashboard
looks wrong in an older console, add `--quiet`; logging still works. The
`--decode-samples` option is for type-1 samples, not N3 type-2 records.

### 5.3 Send once from PowerShell window B

```powershell
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
ssh -i $Key -o IdentitiesOnly=yes root@192.168.50.2 '/home/root/n3-tools/n3_udp_sender --input /home/root/n3-tools/SIMULATED_records.bin --id 1 --dest 192.168.50.1 --port 5000 --batch 50'
```

Expected sender summary: `fpga=1 packets=1 records=5 next_sequence=1`.
Window A should show board 1 receiving one packet. After two seconds it may
show OFFLINE again because this is a one-shot replay, not a continuous stream.
Stop the receiver with **Ctrl+C** after that packet arrives so logs are flushed.

### 5.4 Verify and decode on Windows

**Windows — normal PowerShell, repository root:**

```powershell
$Repo = 'C:\FPGA\FPGA_Ethernet'
Set-Location $Repo
py -3 tools\replay_fixture.py verify --expected N3-Codes-Ethernet/ethernet/build/windows/SIMULATED_records.bin --capture N3-Codes-Ethernet/ethernet/logs/windows_run_001/fpga_01.bin --metadata N3-Codes-Ethernet/ethernet/logs/windows_run_001/fpga_01_metadata.csv
py -3 N3-Codes-Ethernet\ethernet\decode_n3_log.py N3-Codes-Ethernet/ethernet/logs/windows_run_001/fpga_01.bin N3-Codes-Ethernet/ethernet/logs/windows_run_001/fpga_01.csv --variant Athena_DE10_LSB
Import-Csv N3-Codes-Ethernet\ethernet\logs\windows_run_001\fpga_01.csv | Format-Table kind, sr_index, count
Get-FileHash N3-Codes-Ethernet\ethernet\build\windows\SIMULATED_records.bin -Algorithm SHA256
Get-FileHash N3-Codes-Ethernet\ethernet\logs\windows_run_001\fpga_01.bin -Algorithm SHA256
```

Pass: exact 140-byte match, one datagram from `192.168.50.2`, sequence 0,
reported gaps 0, and decoded indices 0..4/counts 10..14. One datagram proves a
smoke test only, not sustained throughput or loss performance.

For another run, restart the receiver in `windows_run_002` and update all
verification paths. Each new sender process starts packet sequence at zero.

## 6. Stage B — install and build with Quartus

This stage requires no Codex. Install the project's **Quartus Prime Lite 23.1
(or licensed Standard 23.1)** with **Cyclone V device support**. Do not select
Quartus Pro or substitute a different FPGA family merely because it is newer.
The source revisions identify Quartus 23.1std; an upgrade should be a separate,
reviewed change.

Download the installer and matching Cyclone V device package from the
[official Quartus Lite 23.1 Windows page](https://www.altera.com/downloads/fpga-development-tools/quartus-prime-lite-edition-design-software-version-23-1-windows).
Keep the installer/device package together and select Cyclone V during setup.
Allow the installer's disk-space requirements and use the vendor's supported
Windows version/architecture. A Microsoft account/GitHub account does not
provide a paid Standard license; choose the edition you can legitimately run.

### 6.1 Make command-line tools available

**Windows — normal PowerShell:**

```powershell
$Repo = 'C:\FPGA\FPGA_Ethernet'
$QuartusRoot = Read-Host 'Enter the installed quartus folder, for example C:\intelFPGA_lite\23.1std\quartus'
if (-not (Test-Path "$QuartusRoot\bin64\quartus_sh.exe")) {
    throw 'That folder does not contain bin64\quartus_sh.exe. Check the installation path.'
}
$env:QUARTUS_ROOTDIR = $QuartusRoot
$env:Path = "$QuartusRoot\bin64;$QuartusRoot\sopc_builder\bin;$env:Path"
Get-Command quartus_sh, qsys-generate, quartus_pgm, jtagconfig
quartus_sh --version
qsys-generate --help
```

These PATH changes affect this PowerShell window only. Repeat them in a new
window, or use the Quartus-provided command shell with the equivalent tools
available. If `qsys-generate` is absent, check the Platform Designer installation
and `quartus\sopc_builder\bin`; don't continue using a historical `loan_io` QIP.

### 6.2 Generate HPS IP and compile Athena LSB

The checked-in generated acquisition sources are already prepared. You do not
need `make` on Windows to use this Python build script.

```powershell
Set-Location "$Repo\N3-Codes-Ethernet\ethernet"
py -3 build_quartus.py --variant Athena_DE10_LSB --dry-run
py -3 build_quartus.py --variant Athena_DE10_LSB
if ($LASTEXITCODE -ne 0) { throw 'Build failed. Inspect build\quartus\step_*.log.' }
Get-Content build\quartus\build_report.json
Get-Content board\generated\n3-uio-address.json
Get-ChildItem ..\FPGA_DE10\Athena_DE10_LSB\output_files\ethernet
```

The script performs three dependent operations:

1. Generate `board/n3_hps.qsys` with the shared custom bridge component.
2. Derive UIO metadata from the **fresh** `board/n3_hps.sopcinfo`.
3. Compile the selected `N3_Ethernet` Quartus revision.

Build logs are `build/quartus/step_00.log`, `step_01.log`, `step_02.log` for a
one-variant build. Open a failed step with `notepad <path>`. A Python dry-run
only lists commands; it is not a successful Quartus generation or compilation.

Expected FPGA output:

```text
N3-Codes-Ethernet/FPGA_DE10/Athena_DE10_LSB/output_files/ethernet/N3_Ethernet.sof
```

Generated Linux fragments:

```text
N3-Codes-Ethernet/ethernet/board/generated/n3-uio.dtsi
N3-Codes-Ethernet/ethernet/board/generated/n3-uio.dtso
N3-Codes-Ethernet/ethernet/board/generated/n3-uio-address.json
```

Other selections are `Athena_DE10_FFMCU`, `Athena_DE10_PUF`, and
`Zeus_DE10_LSB`. Omitting `--variant` builds all four. Start with Athena LSB.
FFMCU/PUF inherit undriven DUT controls `clk_piso`, `clr_ctr` and `load_b` that
must be resolved for those modes; Zeus inherits a reported TCAM issue. Passing
transport tests does not resolve those DUT issues.

If intentionally regenerating the source revisions after edits, use:

```powershell
py -3 prepare_projects.py
py -3 board/prepare_deployment.py
```

That regenerates the prepared source files and twelve-board templates. Review
the resulting Git diff; the generated files are not the primary edit location.
Those templates use the original 192.168.1.x deployment, not this direct link.

### 6.3 Quartus GUI path and timing review

For Platform Designer inspection, open
`N3-Codes-Ethernet\ethernet\board\n3_hps.qsys`. Its custom IP is under
`ethernet\rtl`; the scripted generation supplies this IP search path. If the
GUI reports the bridge missing, add that directory to its IP catalog search
paths and refresh; do not remove the component to make generation pass.

For the FPGA project:

1. Start Quartus and choose **File -> Open Project**.
2. Open `N3-Codes-Ethernet\FPGA_DE10\Athena_DE10_LSB\N3_Ethernet.qpf`.
3. Confirm revision `N3_Ethernet`, top `DE10_TOP`, and the Cyclone V SoC device
   matching this DE10-Standard. Do not open the historical `2_5M_SRAM_SR.qpf`.
4. After shared HPS IP generation, use **Processing -> Start Compilation** if
   compiling from the GUI instead of the script.
5. Inspect the Compilation Report, fitter results and TimeQuest setup/hold
   summaries. Review unconstrained paths, reset/CDC warnings, HPS DDR/RGMII and
   daughtercard I/O timing. Do not treat “0 errors” alone as timing closure.

The repository does not supply guessed daughtercard I/O delays or blanket false
paths. Obtain actual interface timing before declaring the board ready for
acquisition. Preserve the full reports and `build_report.json` with the image.

## 7. Program the FPGA through USB-Blaster

This is distinct from SSH and does not happen over the ordinary Ethernet
connection. Prepare the matching HPS boot/configuration plan in section 8
before live use. Stop any active sender before resetting/reconfiguring hardware.
Keep the daughtercard disconnected for baseline transport testing; power off
before connecting it for later DUT tests.

### 7.1 Driver and JTAG detection

Connect board power and its **USB-Blaster programming** port to Windows with
a data cable. The UART Mini-B connection is a different device/driver.

If USB-Blaster II is unrecognized, use **Device Manager -> device -> Update
driver -> Browse my computer**, selecting the installed Quartus directory's
`drivers\usb-blaster-ii` folder. Terasic's
[official driver instructions](https://www.terasic.com.tw/wiki/Intel_USB_Blaster_II_Driver_Installation_Instructions)
show the expected JTAG interface. Use the driver's matching supported installer;
do not use the old ARM driver files from this repository for an x64 Windows PC.

**Windows — PowerShell with the Quartus PATH from section 6:**

```powershell
jtagconfig
quartus_pgm --list
```

Expected: a programming cable and the Cyclone V SoC chain. Use the actual
listed cable/device order; the HPS and FPGA may appear as separate chain entries.

### 7.2 Recommended GUI programming

1. In Quartus, choose **Tools -> Programmer**.
2. Select the detected USB-Blaster in **Hardware Setup** and JTAG mode.
3. Use **Auto Detect** to inspect the chain.
4. Assign the **newly built** `output_files\ethernet\N3_Ethernet.sof` to the
   FPGA entry, not the HPS entry. Verify the FPGA/device matches the board.
5. Select **Program/Configure** for that image and start. Record the result.

A `.sof` programs volatile FPGA configuration; power cycling does not make it
persist. Automatic SD/flash configuration requires the separate supported
boot flow. Do not overwrite QSPI/boot flash or install a `.jic` merely to test
this revision.

### 7.3 Optional programming CLI

Only after inspecting `jtagconfig`, choose the actual cable and FPGA chain
position. Do not assume that the FPGA is always device 1.

```powershell
$Sof = "$Repo\N3-Codes-Ethernet\FPGA_DE10\Athena_DE10_LSB\output_files\ethernet\N3_Ethernet.sof"
if (-not (Test-Path $Sof)) { throw 'The newly compiled SOF is missing.' }
$Cable = Read-Host 'Enter the cable name or number shown by jtagconfig'
$FpgaPosition = [int](Read-Host 'Enter the confirmed FPGA JTAG position (1-based)')
quartus_pgm -c $Cable -m JTAG -o "p;${Sof}@${FpgaPosition}"
if ($LASTEXITCODE -ne 0) { throw 'FPGA programming failed.' }
```

Keep a known-good recovery image and use the correct board boot-switch settings
for the chosen configuration method. Refer to the board manual rather than
changing MSEL switches based on an unrelated DE10 model/tutorial.

## 8. Stage C — matching HPS boot and UIO integration

**This is the remaining engineering gate.** The stock card currently proves
Linux/SSH/Ethernet only. Loading an SOF, copying a `.dtsi`, or finding a random
`/dev/uio0` does not by itself establish this design's HPS data path.

There is **no validated, ready-to-flash N3 custom boot image or one-command
handoff/preloader installation in this repository yet**. The exact commands
depend on the selected Cyclone V bootloader/SoC toolchain and kernel. Do not
copy historical `loan_io` handoff files, invent a physical address, or overwrite
the working boot partition with guessed artifacts. The Windows Quartus build
can be completed first; full live acquisition must wait for this gate.

The required deliverables are:

1. Fresh Qsys-generated HPS handoff from **this** `n3_hps` system, reviewed for
   the actual DE10-Standard revision. Find generated handoff artifacts with:

   **Windows PowerShell, from `N3-Codes-Ethernet\ethernet`:**

   ```powershell
   Get-ChildItem board -Recurse -Directory | Where-Object Name -Like '*hps_isw_handoff*'
   Get-ChildItem board -Recurse -Filter hps.xml
   ```

2. A matching preloader/SPL/U-Boot and device tree using a Cyclone V-compatible
   SoC boot toolchain that accepts those generated artifacts. Install this on
   separately backed-up/test media and keep the working console SD recoverable.
   A Linux build host/VM/WSL may be useful for the boot tools; Windows Quartus
   availability does not imply that every SoC boot tool runs natively there.
3. The generated `n3-uio.dtsi` included in the board DTS, or the `.dtso` only
   if the actual bootloader/kernel supports overlays. The fragment assumes
   one root address cell and one size cell; verify against the actual DTS.
4. Kernel UIO and `uio_pdrv_genirq`, matched to `generic-uio`, with polling
   supported. Do not invent an interrupt; the component uses polling.
5. The correct FPGA configuration loaded and the lightweight HPS-to-FPGA bridge
   enabled through that boot image's supported FPGA-manager/bridge mechanism
   **before** accessing the UIO memory map.

The stock kernel is an older Linux 4.5 BSP. Do not assume modern configfs
FPGA overlays, `/sys/class/fpga_manager` commands, or a particular `boot.scr`
layout work unchanged on it. Consult the selected toolchain's board-specific
boot documentation and verify the resulting files against the actual kernel.

Once the matching boot system is installed, inspect it through **DE10 SSH**:

```sh
uname -a
cat /proc/cmdline
ls -l /sys/class/uio
ls -l /sys/class/fpga /sys/class/fpga_manager /sys/class/fpga_bridge 2>/dev/null
if test -r /proc/config.gz; then
    zcat /proc/config.gz | grep -E 'CONFIG_(UIO|UIO_PDRV_GENIRQ|FPGA|OF_OVERLAY)'
fi
```

If the kernel provides `uio_pdrv_genirq` as a module and its DT node is already
correct, the image may use:

```sh
modprobe uio_pdrv_genirq of_id=generic-uio
```

If built into the kernel, use its documented boot parameter instead. A missing
module/config option requires a matching kernel build; copying an unrelated
`.ko` is not a solution. Loading a driver does not configure the FPGA or bridge.

Inspect the actual UIO resources:

```sh
for d in /sys/class/uio/uio*; do
    test -d "$d" || continue
    echo "$d"
    cat "$d/name"
    cat "$d/maps/map0/addr"
    cat "$d/maps/map0/size"
    cat "$d/maps/map0/offset"
done
```

Compare map0 with **your fresh** `board/generated/n3-uio-address.json`. Span
must cover at least `0x80` bytes and map offset must be zero. `0x10000` is the
component's **relative Qsys offset**, not its Linux physical address.

Only with the right image, boot setup, bridges and resource mapping is it
appropriate to run `--uio`. The sender then checks ID `0x4e334531`, version
`0x00010000` and timestamp frequency `50000000`. Access to an unconfigured bus
can hang/fault before a software ID check, so do not use this as an arbitrary
MMIO probe.

## 9. Live N3 acquisition after Stage C passes

Power off before connecting the correct daughtercard/expansion cables. Follow
[the N3 wiring notes](N3-Codes-Ethernet/README.md) and the actual schematic,
including rails/current limits and Athena/Zeus selection. Legacy DE2 switch
numbers do not map directly onto the DE10; inspect `DE10_TOP_Ethernet.v` for
this revision. Bring up Athena LSB first and resolve the mode-specific issues
listed in section 6 before using other variants.

**Windows receiver window — use another fresh directory:**

```powershell
Set-Location C:\FPGA\FPGA_Ethernet\N3-Codes-Ethernet\ethernet\multi_fpga_receiver
py -3 receiver.py --config config/direct_link_192_168_50.json --log-dir ../logs/live_001
```

**DE10 Linux SSH window — replace the example with the verified UIO node:**

```sh
N3_UIO=/dev/uio0
/home/root/n3-tools/n3_udp_sender --uio "$N3_UIO" --id 1 --dest 192.168.50.1 --port 5000 --batch 50
```

`/dev/uio0` above is an example, not an instruction to assume the first node.
Use one sender per component. Ctrl+C stops it, disables acceptance, and prints
accepted/consumed/stall/queued counters. Queued data may remain; stopping does
not guarantee the FIFO drained. Do not reset/reprogram the FPGA while a sender
is accessing UIO.

After stopping the sender, let the receiver finish incoming traffic, then stop
it with Ctrl+C. **Windows PowerShell:**

```powershell
Set-Location C:\FPGA\FPGA_Ethernet
py -3 N3-Codes-Ethernet\ethernet\decode_n3_log.py N3-Codes-Ethernet/ethernet/logs/live_001/fpga_01.bin N3-Codes-Ethernet/ethernet/logs/live_001/fpga_01.csv --variant Athena_DE10_LSB
```

Verify correct variant interpretation, all 60 LSB channels, valid/full SRAM
scans, plausible baseline data and response to a controlled DUT stimulus/error
injection. PUF SRAM data are raw power-on words; other listed modes use XOR
error masks. Check gaps, stalls and remaining FIFO data before interpreting
counts. FPGA acceptance timestamps are board-local and not synchronized by
Ethernet. UDP has no retransmission in this design.

Begin manually at low rate. Only consider the optional systemd service after
correctness is established. Its checked-in environment templates use the old
192.168.1.x network, and it deliberately does not auto-restart into reused
packet sequence histories. For twelve boards, allocate unique IDs/IPs and
update receiver/source checks consistently before scaling up.

## 10. Troubleshooting

| Symptom | Check / action |
|---|---|
| `New-NetIPAddress` reports PersistentStore / DHCP Enabled (error 87) | Use the updated section 3 `netsh ... source=static` block on the confirmed wired NIC, in Administrator PowerShell. Verify DHCP Disabled and 192.168.50.1/24. Do not try to disable DHCP by writing PersistentStore. |
| No link/adapter | Verify board power, RJ45 cable, adapter driver, and `Get-NetAdapter`. Link LEDs or 1 Gbit/s only establish physical carrier. |
| Link works, no ping | Check Windows is 192.168.50.1/24 and board uses the provisioned SD/IP. A stock unconfigured SD needs section 11. Check subnet conflicts and duplicate IPs. |
| TCP 22 fails | Linux/SSH may not have booted, or addressing differs. Inspect through UART if available; do not keep guessing passwords. |
| SSH greeting timeout | Retry with `-o ConnectTimeout=30` after first boot. Key generation can delay SSH startup; this is distinct from bad authentication. |
| `Permission denied (publickey)` | The Windows public key was not appended, the wrong private key was selected, or root ownership/modes differ. Return to section 4. |
| Host-key changed warning | Verify which board/image is connected and its fingerprint using the trusted Mac/UART. Only after verification, remove the stale entry with `ssh-keygen -R 192.168.50.2`, then reconnect. |
| `scp` reports an SFTP subsystem problem | Inspect the board's configured SFTP server. With a client that supports it, `scp -O ...` requests legacy SCP; do not change the SSH authentication policy just for copying. |
| Receiver cannot bind address | The selected Windows NIC does not own 192.168.50.1. Check `Get-NetIPAddress`; use native Windows Python, not an unverified WSL network. |
| UDP port busy | `Get-NetUDPEndpoint -LocalPort 5000` identifies the owner. Stop your previous receiver normally; do not kill an unknown process blindly. |
| SSH works, receiver gets nothing | Start receiver first, confirm `--dest 192.168.50.1`, port 5000, correct config and the scoped firewall rule. An SSH connection alone does not verify inbound UDP. |
| Zero-byte binary log while running | Stop receiver cleanly with Ctrl+C so buffered files flush, then inspect. |
| Replay verify fails on second attempt | Each sender restarts at sequence zero. Start a new receiver/log session, transfer the exact generated fixture, and send once. |
| Source-IP warning | Use the direct-link config; board 1 must source from 192.168.50.2 for this recipe. |
| No `/dev/uio*` | This is expected before custom FPGA/DT/kernel integration. Stage A can still pass. |
| UIO sender ID/version error or bus fault | Stop. Recheck actual bitstream, boot artifacts, enabled lightweight bridge and generated resource. Do not force a guessed map/address. |
| Quartus cannot find Cyclone V | Install the matching 23.1 Cyclone V device package. Verify the exact target board/device. |
| Quartus custom IP missing | Check `ethernet/rtl/n3_ethernet_bridge_hw.tcl`, the generation search path and selected Qsys file. Do not substitute stale `loan_io` IP. |
| USB-Blaster absent | Check programming port/data cable/power, Device Manager and the matching Quartus driver. A UART COM port is not a JTAG cable. |
| Fits but timing fails | Inspect TimeQuest and actual board/DUT timing. Programming success is not a timing pass. |

Useful **Windows PowerShell** diagnostics:

```powershell
Get-NetAdapter -Physical | Format-Table ifIndex, Name, Status, LinkSpeed
Get-NetIPAddress -AddressFamily IPv4
Get-NetNeighbor -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.50.2'
Test-NetConnection 192.168.50.2 -Port 22
Get-NetUDPEndpoint -LocalPort 5000 -ErrorAction SilentlyContinue
```

For a Quartus failure, save the command/version, `build/quartus/step_*.log`,
`build_report.json`, and fitter/TimeQuest reports. Do not include private SSH
keys, SD backups or passwords when sharing logs. This is enough to investigate
without Codex installed on the Windows machine.

## 11. Optional new SD card or UART recovery

**Skip this for the already-prepared working SD card.** The Mac's raw-device
scripts contained this session's disk identity and paths; they are not Windows
setup tools and are not included as reusable flash scripts.

### 11.1 If a replacement SD image is actually needed

Inventory removable media in **Windows PowerShell**:

```powershell
Get-Disk | Format-Table Number, FriendlyName, BusType, Size, PartitionStyle
Get-Partition | Format-Table DiskNumber, PartitionNumber, DriveLetter, Size
```

Identify the exact external card by size/model and inspection. Do not select a
Windows system disk or infer its number from the earlier Mac `disk4` name.
Back up any data before an explicitly intended overwrite. Use a whole-card
imager such as the board-manual's Win32 Disk Imager, obtaining it from its
[official project](https://sourceforge.net/projects/win32diskimager/); use its
read/backup function before writing and its available readback verification.
A Windows drive letter alone does not describe the card's Linux partitions.

The board's stock console image is available from
[Terasic's official DE10-Standard Linux directory](https://download.terasic.com/downloads/cd-rom/de10-standard/Linux/).
For the console image:

```powershell
$Download = Join-Path $env:USERPROFILE 'Downloads\DE10-Standard-Linux'
New-Item -ItemType Directory -Force $Download | Out-Null
Invoke-WebRequest -Uri 'https://download.terasic.com/downloads/cd-rom/de10-standard/Linux/DE10-Standard_Linux_Console.zip' -OutFile "$Download\DE10-Standard_Linux_Console.zip"
Get-FileHash "$Download\DE10-Standard_Linux_Console.zip" -Algorithm SHA256
Expand-Archive "$Download\DE10-Standard_Linux_Console.zip" -DestinationPath $Download
Get-ChildItem $Download
```

Extract the `.img` and write it as a **whole-card image**, not as a file copied
onto FAT. Recheck the selected card immediately before writing; verify readback
and eject. The observed official image is 1,600,126,976 bytes, while Terasic
specifies at least 4 GB media. Recheck the actual download/card before reuse.
Its previously measured archive hash is recorded in the
[setup reference](skills/fpga-board-setup/references/de10-standard.md); that
measurement is not an independently published vendor checksum.

A fresh **stock** card does not contain our static eth0 profile, Windows SSH
key, N3 tools or modified FPGA design. Configure its Linux filesystem through
UART or an authorized Linux/offline provisioning workflow before expecting
Ethernet-only access. Windows Explorer cannot edit the Linux root partition.
Do not erase a working card just because the laptop OS changed.

### 11.2 Find and open UART

Connect the board's **UART TO USB Mini-B** port using a USB data cable, with
board power connected. This port uses the onboard FTDI bridge. On Windows:

```powershell
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Name
```

Also check Device Manager -> Ports (COM & LPT) or the enumerated USB device.
If no USB device appears, check connector/data cable/power/accessory approval
before changing drivers. If enumerated but no COM driver binds, obtain the
matching driver through Windows Update or the official vendor.

Use a serial terminal such as [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html):
Serial connection, the actual COM number, **115200 baud, 8 data bits, no parity,
1 stop bit, no flow control**. Power-cycle the board to capture boot output if
necessary. For this stock Terasic image, console username is `root` and no
password is required. This console policy is different from key-only SSH.

### 11.3 Provision networking and the Windows public key from UART

The commands below target the **stock Terasic console BSP with systemd**, not
an arbitrary Linux image. First confirm `uname -a`, interface `eth0`, and
`command -v systemctl`. From the **DE10 UART Linux prompt**:

```sh
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-n3-eth0.network <<'NETWORK'
[Match]
Name=eth0

[Network]
Address=192.168.50.2/24
DHCP=no
LinkLocalAddressing=no
NETWORK
chown root:root /etc/systemd/network/10-n3-eth0.network
chmod 644 /etc/systemd/network/10-n3-eth0.network
mkdir -p /home/root/.ssh
chmod 700 /home/root/.ssh
```

On **Windows PowerShell**, copy the generated public key to the clipboard:

```powershell
$Key = Join-Path $env:USERPROFILE '.ssh\de10_n3'
Get-Content "$Key.pub" -Raw | Set-Clipboard
```

At the **UART Linux prompt**, run:

```sh
cat >> /home/root/.ssh/authorized_keys
```

Paste the **one complete public key line**, press Enter, then **Ctrl+D** to
finish `cat`. Do not paste a private key. Continue at the Linux prompt:

```sh
chown -R root:root /home/root/.ssh
chmod 600 /home/root/.ssh/authorized_keys
ssh-keygen -A
```

For a fresh stock BSP, back up its SSH config and explicitly enable key-only
remote login. Preserve existing keys/host identity; do not regenerate working
host keys just to move laptops.

```sh
test -e /etc/ssh/sshd_config.before-windows || cp -p /etc/ssh/sshd_config /etc/ssh/sshd_config.before-windows
cat > /etc/ssh/sshd_config <<'SSHCONFIG'
Protocol 2
Port 22
HostKey /etc/ssh/ssh_host_ecdsa_key
PermitRootLogin without-password
PubkeyAuthentication yes
AuthorizedKeysFile /home/root/.ssh/authorized_keys
PasswordAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
UsePrivilegeSeparation yes
UseDNS no
Subsystem sftp /usr/lib/openssh/sftp-server
SSHCONFIG
/usr/sbin/sshd -t
```

Only if that validation succeeds:

```sh
systemctl enable systemd-networkd sshd.socket
systemctl restart systemd-networkd
systemctl restart sshd.socket
ip -4 addr show eth0
ssh-keygen -lf /etc/ssh/ssh_host_ecdsa_key.pub
```

Verify the displayed host fingerprint when connecting from Windows. If the old
board ssh-keygen displays a different fingerprint algorithm, securely copy its
public host key to Windows and run the Windows `ssh-keygen -lf` on that public
file to compare in the same algorithm. No private host key needs to leave the
board.

Return to section 4.3, then section 5. If UART also fails and no trusted SSH
connection is available, stop and use an authorized offline Linux/rootfs edit
with backup and verification; do not work around key-only SSH by password
brute force or blindly reflashing unrelated firmware.

## 12. Optional software-only regression tests

Stage A does not require Make, Verilator, GHDL or WSL. For a fuller local
simulation/synthesis check on Windows, an Ubuntu WSL environment is one option.
Use it for offline software checks; keep the direct Ethernet receiver and
Quartus/JTAG on the native Windows path described above unless you separately
validate WSL networking/USB forwarding.

**Windows — Administrator PowerShell, only if choosing WSL:**

```powershell
wsl --install -d Ubuntu-24.04
```

Follow any restart/account-creation prompts. In **Ubuntu/WSL Bash**:

```sh
sudo apt update
sudo apt install -y git python3 build-essential verilator ghdl device-tree-compiler
git clone https://github.com/khkim37382/FPGA_Ethernet.git
cd FPGA_Ethernet/N3-Codes-Ethernet/ethernet
verilator --version
ghdl --version
make test
make hdl-check
```

Use a GHDL build with synthesis/Verilog output support and a Verilator version
supporting `--binary --timing`. If the distribution's tools cannot satisfy the
project, use matching official releases instead of skipping the HDL checks.
These commands do not generate a Quartus bitstream, train HPS DDR, configure
UIO, or test the physical daughtercard.

## 13. Restore the Windows acquisition adapter when finished

Stop the receiver and sender first. If the selected adapter **originally used
DHCP**, remove only the address this guide added and restore DHCP:

**Windows — Administrator PowerShell:**

```powershell
Get-NetAdapter -Physical | Format-Table ifIndex, Name, Status, LinkSpeed
$IfIndex = [int](Read-Host 'Enter the dedicated DE10 adapter ifIndex to restore')
Get-NetIPAddress -InterfaceIndex $IfIndex -IPAddress 192.168.50.1 -ErrorAction SilentlyContinue |
    Remove-NetIPAddress -Confirm
Set-NetIPInterface -InterfaceIndex $IfIndex -AddressFamily IPv4 -Dhcp Enabled
Get-NetFirewallRule -DisplayName 'N3 DE10 direct UDP 5000' -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
```

If it originally had a static setup, restore the settings saved in
`de10-nic-before.txt` instead. Do not change Wi-Fi or another user's adapter.
The board can remain configured at 192.168.50.2 for its next direct-link test.

## Completion record

Record the Windows version/architecture, board model, repository commit
(`git rev-parse HEAD`), stage reached, receiver log directory, sender binary
hash, and any Quartus reports. Clearly label simulated records. Publish results
only after running the relevant stage: this README's existence is not a claim
that Windows, Quartus or the custom HPS/UIO integration has passed.

### Checks performed while writing this guide

The fixture helper was executed against the real C sender and Python receiver
on macOS: deterministic creation, exact capture verification, decoded channel/
count fields, wrong-source rejection, corrupted-payload rejection, and refusal
to overwrite an unrelated file all passed. Local Markdown links, Python syntax,
and the Quartus build dry-run were checked. PowerShell commands were reviewed
against their vendor documentation; they have not been run on a Windows host.
No Quartus generation/fitting/programming success is claimed by these checks.

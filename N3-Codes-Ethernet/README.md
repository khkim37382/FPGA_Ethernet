See the repository's [FPGA testing and Mac workflow](../docs/FPGA_TESTING.md)
for a first-board walkthrough and [import scope](../docs/IMPORT_NOTES.md)
for excluded local datasets/build outputs.

# Local N3 Ethernet adaptation

This standalone copy excludes `.git` and `.github`. The original repository
is untouched. All four DE10 variants now have independent Ethernet revisions:
Athena LSB, Athena FFMCU, Athena PUF, and Zeus LSB.

Open each variant's `N3_Ethernet.qpf`. Start with
[ethernet/README.md](ethernet/README.md) for the shared HPS configuration,
local tests, deployment files, receiver and decoder commands, and the remaining
Quartus/physical bring-up steps. See [validation](ethernet/VALIDATION.md) for
what was actually tested. No hardware-validated bitstream is supplied yet.

The original README follows.

---

# N3- Codes
## Cable Connections
1) Connect FPGA GPIO to SRAM GPIO on PCB    
2) Connect EXT_CARD Middle GPIO to SR36-59 GPIO on PCB   
3) Connect EXT_CARD Rightmost GPIO to SR0-35 GPIO on PCB   
4) Power all VDD jumpers, except when using HF code   
5) EXT_CLK to FPGA_CLK:
    * If using proto-boards, do not jump EXT_CLK to FPGA_CLK, manual soldering of buffers are done
    * Otherwise, jump EXT_CLK to FPGA_CLK for all these codes

6) Board Selection Jumper:  
    - Athena is left-aligned   
    - Zeus is right-aligned  

7) No jumpers on:   
    - Select_Data_In
    - Data_In
    - SELECT_SR_PISO
8) Nominal VDD is 0.75V, set current limit to 100 mA unless using high frequency operation. The 2.5 MHz current should be around 18 mA
9) Nominal VDDPST is 1.2 V, set current limit to 500 mA. The current will likely never exceed 80 mA

## Switch Controls
SW[0] = SELECT_DATA_IN   
SW[1] = DATA_IN  
SW[2] = SRAM_DATA_SELECT_0  
SW[3] = SRAM_DATA_SELECT_1  
SW[5] = RO_ENABLE  
SW[6] = S0_DIV  
SW[7] = S1_DIV  
SW[8] = S0_RO  
SW[9] = S1_RO  
SW[12] = SELECT_SR_PISO   
SW[13] = SRAM ADDR SELECT (LOW = SW 2,3, HIGH = ADDR)

## Code Structure
### [Athena_FFMCU](https://github.com/npieper17/N3-Codes/tree/main/Athena_FFMCU)
Only can be ran on RPI using EX_IO6 pins on FPGA connected to RPI UART.  
### [Athena_HF](https://github.com/npieper17/N3-Codes/tree/main/Athena_HF)
SW[12] must be high
Disconnect the VDD_SR_16_to_1 power jumper in order to prevent interference from SRAMs
### [Athena_LSB](https://github.com/npieper17/N3-Codes/tree/main/Athena_LSB)
SW[12] must be low
### [Zeus_HF](https://github.com/npieper17/N3-Codes/tree/main/Zeus_HF)
SW[12] must be high  
TCAM doesn't work, disabled SRAM0 for now  
Needs to be updated to match athena and verify error injection
### [Zeus_LSB](https://github.com/npieper17/N3-Codes/tree/main/Zeus_LSB)
SW[12] must be low  
TCAM doesn't work, disabled SRAM0 for now

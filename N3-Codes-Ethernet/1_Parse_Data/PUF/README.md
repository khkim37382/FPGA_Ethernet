# PUF Research Project Repository

---

Overview: This repository holds the raw data, processed data, and data analysis scripts for my research on physically unclonable functions in advanced node semiconductors.

### Repository structure:
- Data folder contains all the raw data and processed data. The subdirectories specify the IC being tested and the testing conditions
- main.py is the master script that can initiate all other scripts. All of these scripts may be found individually within the FPGA Scripts and Data Analytics folders:
  - FPGA and power supply controller
  - SRAM analysis script
  - SRAM visualization script
  - Signature identification script
  - Signature comparison script
 
---

### How does the new FPGA code work:
- Broadly the VHDL is the same, the program is unchanged
- In the DE2_115.v file I set the write enable pin low permanently (previously attached to GPIO)
- Ideally I would just disable WE in the SRAM code but this caused FSM instability
- Data output is not xor’d with the stored data (we want raw data)
- Now instead of a “wait time” in the SRAM code we have a signal coming from the ffmcu code (called clk_sr at the top level DE2 file) which is passed to the SRAM code, synchronized and latched (since the original signal is only high for 1 cycle). It is reset after it is read.

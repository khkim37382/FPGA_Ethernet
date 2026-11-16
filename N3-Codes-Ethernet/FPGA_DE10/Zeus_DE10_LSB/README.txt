project: 2_5M_SRAM_SR
Author: Nicholas Pieper

TODO:
add SRAM test once control signals come in. 
add variable frequency code
add direct output of SRs to be stored
create python script for parsing data
add external data switch

This project is designed for an DE2_115 board to count and capture soft errors on 5nm IC test boards

my_arrays.vhd 
	package defining constants and data structures required for lsb_main

DE2_115.v 
	dependencies: lsb_main
	
	this maps FPGA pins to next level entities, lsb_main and _____ (SRAM test)
	
lsb_main
	dependencies: lsb_counter, main_controller
	
	maps board inputs to counters in lsb_counter and lsb_counter outputs to main_controller
	and main controller to serial transmission entities
	
SRAM_main
	dependencies: none
	
	initializes SRAM memory and subsequently polls all addresses after counter is reached. stores
	address and error locations for transmit to pc
	
IVT main
	dependencies: i2c_master
	
	controls current, voltage, and temperature sensor circuit on the board

xmit_mux
	dependencies: u_xmit.v		Clk115200.vhd
	
	recieves data from all 3 test modules, ensures that only data from one test is sent at a time
	
	
	
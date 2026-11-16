--Author: Nick Atkinson
--File: controller.vhd
--Entity: controller_main
--
--Description:  This entity controls the LSB counters from the shift registers, as well as encoding them in ascii and sending them to 
--the xmit module in a 6-byte word


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;

entity main_controller is 

generic (

	constant tag_length : integer range 0 to 1023 := 24
);

port (

	sys_clk					:	in std_logic; --keep process sequential with 50MHz clock
	reset						:	in std_logic; --active low

	--Ports for interfacing with XmitData (middle-man between controller and UART)
	xmit_Ready				:	out std_logic := '0';  --send_data begins transmission
	data_block				:	out std_logic_vector((serial_size - 1) downto 0); --data from SET measurement module
	xmit_ack					:	in std_logic; --handshake from XmitData

	set_hex 					:	in srcount_arr;

	set_clear				: 	out std_logic;
	LED_rst 					: 	out std_logic
	
);
end main_controller;

architecture behavior of main_controller is

	type state_type is (reset_state, idle, reading, sending, sending2, sending3);	--states for xmit_SET process
	signal set_hex_sig : srcount_arr; --this is the indexable version of the SET hex
	
	constant delay_val : integer := 500000000; --delay time contrls been data reads
	signal delay_time : integer range 0 to delay_val; --delays up to delay_val
	signal delay_trig : std_logic;	--triggers delay counter to start between reads

	signal state : state_type := reset_state;
	signal data_buf : counter_buffer;
	signal data_ready: std_logic := '0';
	signal set_index : integer range 0 to 100 := 0;	--indexes for SET entities
	signal xmit_ready_sig : std_logic;
	constant buffer_sig : std_logic_vector(serial_size-20 downto 0) := "00100000"  & std_logic_vector(resize(to_unsigned(0, 1), serial_size-19-8));

begin
	
	set_hex_sig <= set_hex;
	LED_rst <= xmit_ready_sig;

	
	poll_SET: --synchronously checks all input counters
	process(sys_clk, delay_trig, xmit_ack) is 
		variable count : integer := 0;
			constant count_lim : integer := 10;
			
				variable xmit_index : integer range 0 to 100 := 2;

	begin 
		if(rising_edge(sys_clk)) then	--each clock cycle checks a single SET entity
			if (reset  = '0') then
				state <= reset_state;
				
			else
				case state is 
					when reset_state =>
						set_index <= 0; --point to first circui to poll
						set_clear <= '1'; --turn off reset signal, active low to other circuits
						state <= reading;
						xmit_ready_sig <= '0';
						
					when idle =>
						if (delay_trig = '1') then
							state <= reading;
							set_index <= 0;
							set_clear <= '1';
							xmit_index := 0;
						end if;

					when reading => --delay time between poll has passed or currently polling circuits
						if ((set_index < NUM_SR)) then --poll next circuit and place in buffer	
							data_buf(set_index) <= buffer_sig & std_logic_vector(to_unsigned(set_index, 7)) & set_hex_sig(set_index);	
							set_index <= set_index + 1; 
						else --set_index out of range, go to reset state
							state <= sending;
							set_clear <= '0';
						end if; --if reading = 0
						
					when sending => --after each counter is checked, transmit each one
--						if (xmit_index < NUM_SR) then
							set_clear <= '1';
							data_block <= data_buf(xmit_index);
							xmit_index := xmit_index + 1;

							xmit_ready_sig <= '1';
							state <= sending2;
--						end if; --if in num_counter range
						
					when sending2 =>
						if (xmit_ack = '1') then
					
							xmit_ready_sig <= '0';
							state <= sending3;
						
						end if;
						
					when sending3 =>

						if (xmit_ack = '0') then
							if (xmit_index > NUM_SR - 1) then
								state <= idle;
							else
								state <= sending;
							end if;
						end if;
					
					
					
					
				end case; 
			end if; -- if not resetting
		end if;	--rising edge of clk	



	
	
	xmit_ready <= xmit_ready_sig;

end process; 
	--delay_timer count
process(sys_clk)
	begin
		if(rising_edge(sys_clk)) then
			if(reset = '0') then
				delay_time <= 0;
				delay_trig <= '0';
			else
				if(delay_time > delay_val) then
					delay_time <= 0;
					delay_trig <= '1';
				else
					delay_trig <= '0';
					delay_time <= delay_time + 1;
				end if; --if delay_time = delay_val
			end if; --if reset=0
		end if; --if rising edge sys_clk
end process;


			
	
end behavior;
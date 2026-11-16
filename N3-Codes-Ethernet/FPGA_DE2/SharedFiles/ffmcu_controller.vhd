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

entity ffmcu_controller is 

generic (

	constant tag_length : integer range 0 to 1023 := 24
);

port (

	sys_clk					:	in std_logic; --keep process sequential with 50MHz clock
	reset						:	in std_logic; --active low
	manual_readout_trig 	:	in std_logic;
	empty_trig : in std_logic;

	--Ports for interfacing with XmitData (middle-man between controller and UART)
	xmit_Ready				:	out std_logic := '0';  --send_data begins transmission
	data_block				:	out std_logic_vector((serial_size - 1) downto 0); --data from SET measurement module
	xmit_ack					:	in std_logic; --handshake from XmitData

	
 	set_hex		:	in std_logic_vector(num_sr-1 downto 0);

	set_clear				: 	out std_logic;
	LED_rst 					: 	out std_logic;
	sr_clk 					:  out std_logic
	
);
end ffmcu_controller;

architecture behavior of ffmcu_controller is

	type state_type is (reset_state, idle, so_sr_clk_up, so_sr_clk_down, sending_clk_down, sending, sending2, sending3, idle0, dummy_clk_down);	--states for xmit_SET process
	signal set_hex_sig : std_logic_vector(num_sr-1 downto 0); --this is the indexable version of the SET hex
	
	signal delay_trig : std_logic;	--triggers delay counter to start between reads

	signal state : state_type := reset_state;
	signal data_buf : counter_buffer;
	signal data_ready: std_logic := '0';
	signal set_index : integer range 0 to 100 := 0;	--indexes for SET entities
	signal xmit_ready_sig : std_logic;
	constant buffer_sig : std_logic_vector(7 downto 0) := "01100000";
	signal dram_addr_num : unsigned(24 downto 0) := to_unsigned(0, 25);
	signal sr_clk_sig : std_logic;
	signal hz_clk : std_logic;
	signal emptydata1, emptydata0, emptydata_dyn : std_logic_vector(num_sr-1 downto 0);
	
	component ffmcu_trigger_clk is 
		port(clk_out : out STD_LOGIC;
			clk1 : out STD_LOGIC;
			clk2 : out STD_logic;
			clk_in : in STD_LOGIC
			  );
	end component;
	
	
begin
	
	set_hex_sig <= set_hex;
	LED_rst <= hz_clk;
	sr_clk <= sr_clk_sig;
	emptydata0 <= 	std_logic_vector(resize(to_signed(0, 1), num_sr));
	emptydata1 <= 	std_logic_vector(resize(to_signed(1, 1), num_sr));
	
	poll_SET: --synchronously checks all input counters
	process(sys_clk, delay_trig, xmit_ack) is 
		variable count : integer := 0;
			constant count_lim : integer := 10;
			
				variable xmit_index : integer range 0 to 100 := 2;

	begin 
		if(falling_edge(sys_clk)) then	--each clock cycle checks a single SET entity
			if (reset  = '0') then
				state <= reset_state;
			elsif (empty_trig = '0') then
				emptydata_dyn <= set_hex;
			else
				case state is 
					when reset_state =>
--						set_index <= 0; --point to first circui to poll
						set_clear <= '1'; --turn off reset signal, active low to other circuits
						state <= sending_clk_down;
						xmit_ready_sig <= '0';
						dram_addr_num <= to_unsigned(0, 25);
						
					when idle0 =>
						sr_clk_sig <= '0';
						dram_addr_num <= to_unsigned(0, 25);
						if (delay_trig = '0') then
							state <= idle;
--							set_index <= 0;
							set_clear <= '0';
						end if;	
	
					when idle =>
						sr_clk_sig <= '0';
						dram_addr_num <= to_unsigned(0, 25);
						if (delay_trig = '1' or manual_readout_trig = '0') then
							state <= sending_clk_down;
--							set_index <= 0;
							set_clear <= '1';
						end if;				
						
					when so_sr_clk_up =>
						sr_clk_sig <= '1';
						state <= so_sr_clk_down;
						
					when so_sr_clk_down =>
						sr_clk_sig <= '0';
						state <= dummy_clk_down;
						
					when dummy_clk_down =>
						sr_clk_sig <= '0';
						state <= sending_clk_down;
						
					when sending_clk_down =>
						sr_clk_sig <= '0';
						if (dram_addr_num = 0) then 
							state <= sending;
						elsif (dram_addr_num = 49150) then 
							state <= sending;
						else
							if (set_hex = emptydata0) then
								state <= sending3;
							elsif (set_hex = emptydata1) then
								state <= sending3;
							elsif (set_hex = emptydata_dyn) then
								state <= sending3;
							else
								state <= sending;
							end if;
						end if;
						set_clear <= '0';
						data_block <= buffer_sig & std_logic_vector(to_unsigned(0, serial_size-num_sr-8-25-4))& std_logic_vector(dram_addr_num) & "0000" & set_hex;	
						
					when sending => --after each counter is checked, transmit each one
						set_clear <= '1';
						xmit_ready_sig <= '1';
						state <= sending2;
						sr_clk_sig <= '0';

--						end if; --if in num_counter range
						
					when sending2 =>
						sr_clk_sig <= '0';

						if (xmit_ack = '1') then
							xmit_ready_sig <= '0';
							state <= sending3;
						end if;
						
					when sending3 =>
						sr_clk_sig <= '0';

						if (xmit_ack = '0') then
							if (dram_addr_num = 49151) then
								sr_clk_sig <= '1';
								state <= idle0;
							else
								dram_addr_num <= unsigned(dram_addr_num) + to_unsigned(1,25);
								state <= so_sr_clk_up;
							end if;
						end if;
				end case; 
			end if; -- if not resetting
		end if;	--rising edge of clk	



	
	
	xmit_ready <= xmit_ready_sig;

end process; 

sr_clk_gen : ffmcu_trigger_clk --this handles sending the counts to the xmit mux
	port map
	(
		clk_out => delay_trig,
		clk1 => hz_clk,
	   clk_in =>sys_clk
	);


			
	
end behavior;
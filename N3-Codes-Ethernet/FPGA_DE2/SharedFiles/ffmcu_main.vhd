library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_arith.all;
use work.my_arrays.all;

entity ffmcu_main is
	generic
	(
	constant tag_length : integer range 0 to 1023 := 24
	);

	port --reset, clk, serial in, and 27 in bits of counter
	(
		-- Input ports
		reset	: in  std_logic; --active low
		sys_clk : in std_logic; --fpga_oscillator clk input
		counter_inmain	: in  std_logic_vector((NUM_SR - 1) downto 0); --data lsb from test chip will connect here

--		
		-- Output ports
		data_out : out std_logic_vector((serial_size-1) downto 0);
		xmit_ready : out std_logic := '0';
		xmit_ack  : in std_logic;
		sr_clk : 	out std_logic;
		manual_readout_trig : in std_logic;
		empty_trig : in std_logic;
		
		SR_reset_LED : out std_logic
		
	);
end ffmcu_main;


architecture behave of ffmcu_main is


	signal cnt_wire : std_logic_vector((num_sr-1)downto 0);
	signal reset_wire, reset_main : std_logic;
	signal XmitData_done : std_logic;
	type state_type is (idle, reading, add);



component ffmcu_controller
		generic (
			constant tag_length : integer range 0 to 1023 := 24
		);
		
		port ( 
		
			sys_clk				:	in std_logic; --keep process sequential with 50MHz clock
			manual_readout_trig : in std_logic;
			empty_trig : in std_logic;

		
			--Ports for interfacing with XmitData (middle-man between controller and UART)
			xmit_ready	:	out std_logic;  --send_data begins transmission
			data_block				:	out std_logic_vector((serial_size - 1) downto 0); --data from SET measurement module
			xmit_ack					:	in std_logic; --handshake from XmitData
			reset						:	in std_logic;
		
			set_hex : in std_logic_vector((num_sr-1)downto 0);
			set_clear	: 	out std_logic; --each of these bits is tied to a single SET measurment module
			LED_rst : out std_logic;
			sr_clk : out std_logic
			
		);
	
	end component;


begin



main_controller1 : ffmcu_controller --this handles sending the counts to the xmit mux
	port map
	(
		sys_clk => sys_clk,
		data_block => data_out,
		xmit_Ready => xmit_ready,
		xmit_ack => xmit_ack,
		set_clear => reset_main,
		reset => reset,
		manual_readout_trig => manual_readout_trig,
		empty_trig => empty_trig,
		
		set_hex => counter_inmain,
		LED_rst => SR_RESET_LED,
		sr_clk => sr_clk
	);

	reset_wire <= reset_main and reset;
	
	
end behave;

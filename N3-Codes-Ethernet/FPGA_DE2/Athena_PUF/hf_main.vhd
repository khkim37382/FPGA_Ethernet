library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_arith.all;
use work.my_arrays.all;

entity hf_main is
	generic
	(
	constant tag_length : integer range 0 to 1023 := 24
	);

	port --reset, clk, serial in, and 27 in bits of counter
	(
		-- Input ports
		reset				: in  std_logic; --active low
		sys_clk 			: in std_logic; --fpga_oscillator clk input
		counter_in		: in  std_logic_vector((NUM_SR - 1) downto 0); --data lsb from test chip will connect here
	
		-- Output ports
		data_out 		: out std_logic_vector((serial_size-1) downto 0);
		xmit_ready 		: out std_logic := '0';
		xmit_ack  		: in std_logic;
		
		clr_ctr 			: out std_logic := '0';
		load_b 			: out std_logic := '0'; 
		clk_piso 		: out std_logic;		
		SR_reset_LED 	: out std_logic := '0';
		reg_led			: out std_logic_vector(3 downto 0)
	);
end hf_main;


architecture behave of hf_main is

	signal cnt_wire 							: srerror_arr;
	signal reset_wire, set_clear 			: std_logic;	
	type state_type2 is (idle, readingup, readingdown);
	signal state : state_type2 			:= idle;
	signal idx : integer range -1 to 5 := 4;
	signal enable 								:std_logic;
	signal reset_ctr							:std_logic;
	signal clear 								:std_logic;
	signal piso_enable 						:std_logic;

component main_controller

		generic (
			constant tag_length : integer range 0 to 1023 := 24
		);
		
		port ( 
			sys_clk		:	in std_logic; --keep process sequential with 50MHz clock
			xmit_ready	:	out std_logic;  --send_data begins transmission
			data_block	:	out std_logic_vector((serial_size - 1) downto 0); --data from SET measurement module
			xmit_ack		:	in std_logic; --handshake from XmitData
			reset			:	in std_logic;
			set_hex 		: 	in srerror_arr;
			set_clear	: 	out std_logic;
			LED_rst 		: 	out std_logic
			
		);
	
	end component;
	
component gen_SR is
    generic(
        LENGTH: natural := 4
    );
    port(
        reg       : out std_logic_vector(LENGTH-1 downto 0);
		  enable 	: in std_logic;
        SI       	: in  std_logic;
		  clear 		: in std_logic;
        clk      	: in  std_logic
    );
end component;
begin

-- load B is synchronous
clk_piso <= sys_clk and (piso_enable);
reg_led <= cnt_wire(0);
clear <= '0';

process (sys_clk) is
begin
		if(falling_edge(sys_clk)) then
			case state is
				when idle =>
					idx <= 3; 						-- start at 3
					clr_ctr <= '0';				-- not clearing counter on chip
					if (set_clear = '0') then 	-- when done transmitting
						piso_enable <= '1';		-- enable the PISO clock
						enable <= '1';				-- shift into FPGA counter
						load_b <= '1';				-- load the PISO counters
						state <= readingup;		-- go to next state
					else
						enable <= '0'; 			-- not shifting FPGA counter
						piso_enable <= '0';		-- do not enable the PISO 
						load_b <= '0'; 			-- PISO is not loading counter
					end if;
				when readingup =>
					idx <= 3; 						-- start at 3
					load_b <= '0';					-- end of pulse for load
					clr_ctr <= '1';				-- clearing the counters on chip
					enable <= '1';					-- shift into FPGA counter
					piso_enable <= '1';			-- still enabling piso clock
					state <= readingdown;

				when readingdown => 
					load_b <= '0';					-- not loading the piso
					clr_ctr <= '0';				-- not clearing the counters on chip
					if (idx = 0) then	
						piso_enable <= '0';		-- not enabling piso clock			
						enable <= '0';				-- not shifting into gen_SR anymore
						state <= idle;
					else
						idx <= idx-1;				-- decrements until 0 (3,2,1,0)
						piso_enable <= '1';		-- enabling piso clock
						enable <= '1';				-- shift into the gen_sr
						state <= readingdown; 	-- repeat
					end if;
			end case;
		end if;
	
end process;

counters: for N in 0 to (NUM_SR - 1) generate
	count : gen_SR 
		port map
		(
		clk => sys_clk,
		SI => counter_in(N),
		reg => cnt_wire(N),
		enable => enable,
		clear => clear
		);
		
end generate;


main_controller1 : main_controller --this handles sending the counts to the xmit mux
	port map
	(
		sys_clk => sys_clk,
		data_block => data_out,
		xmit_Ready => xmit_ready,
		xmit_ack => xmit_ack,
		set_clear => set_clear,
		reset => reset,
		set_hex => cnt_wire
	);
	
end behave;

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

	port 
	(
		-- Input ports
		reset			: in  std_logic; --active low
		sys_clk 		: in std_logic; --fpga_oscillator clk input
		counter_in		: in  std_logic_vector((NUM_SR - 1) downto 0); --data lsb from test chip will connect here
		-- Output ports
		data_out 		: out std_logic_vector((serial_size-1) downto 0);
		xmit_ready 		: out std_logic := '0';
		xmit_ack  		: in std_logic;
		clr_ctr 		: out std_logic := '0';
		load_b 			: out std_logic := '0'; 
		clk_piso 		: out std_logic;		
		SR_reset_LED 	: out std_logic := '0';
		reg_led			: out std_logic_vector(3 downto 0)
	);
end hf_main;

architecture behave of hf_main is
	signal cnt_wire 	: 	srerror_arr;
	signal set_clear 	: 	std_logic;	
	type state_type2 is (waiting_stage,ready_state,bit3_state,bit2_state,bit1_state,bit0_state,reset_state);
	signal state: state_type2 := waiting_stage;
	signal shift 		: std_logic := '0';
	signal piso_enable 	: std_logic := '0';
	signal reset_SR 	: std_logic := '0';
	signal idx 			: integer := 3; -- Initialize idx to 3
	signal loaded : std_logic;

component hf_controller
		generic (
			constant tag_length : integer range 0 to 1023 := 24
		);
		
		port ( 
			sys_clk		:in std_logic; --keep process sequential with 50MHz clock
			xmit_ready	:out std_logic;  --send_data begins transmission
			data_block	:out std_logic_vector((serial_size - 1) downto 0); --data from SET measurement module
			xmit_ack	:in std_logic; --handshake from XmitData
			reset		:in std_logic;
			set_hex 	:in srerror_arr;
			set_clear	:out std_logic;
			LED_rst 	:out std_logic;
			loaded : in std_logic
		);
	
	end component;
	
component ShiftRegister is
    generic(
    	WIDTH : integer := 4  -- Width of the shift register
    );
    port(
		clk     : in STD_LOGIC;         -- Clock input
		reset   : in STD_LOGIC;         -- Reset input
		shift_in: in STD_LOGIC; -- Input data
		shift   : in STD_LOGIC;         -- Shift control input (rising edge triggered)
		q       : out STD_LOGIC_VECTOR(WIDTH-1 downto 0) -- Output data
    );
end component;
begin

clk_piso <= sys_clk and (piso_enable);
reg_led <= cnt_wire(0);

process (sys_clk,set_clear) is
begin
		if set_clear = '0' then
			state <= ready_state;
		elsif(falling_edge(sys_clk)) then
			case state is
				when waiting_stage =>
					loaded <= '0';
					clr_ctr <= '0';			-- not clearing counter on chip
					shift <= '0'; 			-- not shifting FPGA counter
					piso_enable <= '0';		-- do not enable the PISO 
					load_b <= '0'; 			-- PISO is not loading counter
					reset_SR <= '0';

				when ready_state =>
					loaded <= '0';
					piso_enable <= '1';		-- enable the PISO clock
					shift <= '0'; 			-- not shifting FPGA counter
					load_b <= '1';			-- load the PISO counters
					reset_SR <= '1';
					state <= bit3_state;	-- go to next state

				when bit3_state =>
					idx <= 3; 				-- start at 3
					shift <= '1';			-- shift into FPGA counter
					state <= bit2_state;
					reset_SR <= '0';

					piso_enable <= '1';		-- still enabling piso clock
					load_b <= '0';			-- end of pulse for load
					clr_ctr <= '1';			-- clearing the counters on chip

				when bit2_state =>
					idx <= 2;				-- next bit
					shift <= '1';			-- shift into the ShiftRegister
					state <= bit1_state;

					piso_enable <= '1';		-- still enabling piso clock
					load_b <= '0';			-- not loading the piso
					clr_ctr <= '0';			-- not clearing the counters on chip

				when bit1_state =>
					idx <= 1;				-- next bit
					shift <= '1';			-- shift into the ShiftRegister
					state <= bit0_state;

					piso_enable <= '1';		-- still enabling piso clock
					load_b <= '0';			-- not loading the piso
					clr_ctr <= '0';			-- not clearing the counters on chip

				when bit0_state =>
					idx <= 0;				-- next bit
					shift <= '1';			-- shift into the ShiftRegister
					state <= reset_state;

					piso_enable <= '1';		-- still enabling piso clock
					load_b <= '0';			-- not loading the piso
					clr_ctr <= '0';			-- not clearing the counters on chip

				when reset_state =>
					shift <= '0';			-- stop shifting into the ShiftRegister
					reset_SR <= '0';		-- clear internal ShiftRegister 

					piso_enable <= '0';		-- stop enabling piso clock
					load_b <= '0';			-- not loading the piso
					clr_ctr <= '0';			-- not clearing the counters on chip
					loaded <= '1';
					
					state<= waiting_stage;
			end case;
		else
			state <= state;
		end if;
end process;

counters: for N in 0 to (NUM_SR - 1) generate
	count : ShiftRegister 
		port map
		(
			clk => sys_clk,
			reset => reset_SR,
			shift => shift,
			shift_in => counter_in(N),
			q => cnt_wire(N)
		);
		
end generate;


main_controller1 : hf_controller --this handles sending the counts to the xmit mux
	port map
	(
		sys_clk => sys_clk,
		data_block => data_out,
		xmit_Ready => xmit_ready,
		xmit_ack => xmit_ack,
		set_clear => set_clear,
		loaded => loaded,
		reset => reset,
		set_hex => cnt_wire
	);
	
end behave;

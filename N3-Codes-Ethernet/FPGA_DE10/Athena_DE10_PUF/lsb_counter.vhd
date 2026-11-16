library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;

entity lsb_counter is
	port
	(
		-- Input ports
		reset	: in  std_logic; --reset all vhdl counters
		sys_clk : in std_logic; --fpga_oscillator clk input
		counter_in	: in  std_logic_vector((NUM_SR - 1) downto 0); --data lsb from test chip will connect here
		
		counter_out : out SRcount_arr	
	);
end lsb_counter;


architecture behave of lsb_counter is

	signal trigger	: std_logic_vector((NUM_SR - 1) downto 0); -- input to counter module to trigger count


	component count_12bit
		port
		(
			clk		: in std_logic;
			reset	: in std_logic; --active low
			enable 	: in std_logic; --active high
			q		: out std_logic_vector((NUM_COUNTER_BITS - 1) downto 0)
		);
	end component;

	
begin



counters: for N in 0 to (NUM_SR - 1) generate
	count : count_12bit port map
		(
		clk => sys_clk, 
		reset => reset,
		enable => trigger(N),
		q => counter_out(N)
		);
		
	process (sys_clk, reset) is 
		variable count : integer range 0 to 2; -- allow signal to settle for each SR
		variable lsb_prev : std_logic;
	begin
		if (rising_edge(sys_clk)) then 
			if (lsb_prev /= counter_in(N)) then
				trigger(N) <= '1';
			elsif (trigger(N) = '1') then
				trigger(N) <= '0';
			end if;
			lsb_prev := counter_in(N);
		end if;
	end process;
end generate;
end behave;


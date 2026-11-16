
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;

entity count_12bit is
	port
	(
		clk		: in std_logic;
		red		: in std_logic;
		enable 	: in std_logic; --active high
		q		: out std_logic_vector((NUM_COUNTER_BITS - 1) downto 0);
		index : in integer range -1 to 4
	);
end entity;

architecture rtl of count_12bit is
		signal q_buff : std_logic_vector((NUM_COUNTER_BITS - 1) downto 0) := "000000000000";

begin
	process (clk)

	begin
		if (rising_edge(clk)) then
				-- Increment the counter if counting is enabled
			if (red = '1') then
				q_buff(index) <= enable;
			end if;
		end if;
		
		-- Output the current count

	end process;
q <= q_buff and "000000001111";
end rtl;

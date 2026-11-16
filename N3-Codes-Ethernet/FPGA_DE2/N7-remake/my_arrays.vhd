library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package my_arrays is 
	constant NUM_SR : integer := 60;
	constant NUM_COUNTER_BITS : integer := 12;
	
--	type counter_vec is std_logic_vector((NUM_COUNTER_BITS - 1) downto 0);
--	type sr_vec is std_logic_vector((NUM_SR -1) downto 0);
	type SRcount_arr is array((NUM_SR - 1) downto 0) of std_logic_vector((NUM_COUNTER_BITS - 1) downto 0);
	type SRerror_arr is array((NUM_SR - 1) downto 0) of std_logic_vector(3 downto 0);
	
	
	
	constant SERIAL_SIZE : integer := 160; --size of data packets in bits to be sent from SRAM/SR/IVT test to computer
	
	
	--how many errors/datapackets to be stored per SRAM/SR test
	constant buff_size : integer := 64;
	type serial_buffer is array((buff_size - 1) downto 0) of std_logic_vector((SERIAL_SIZE - 1) downto 0);
	type counter_buffer is array((Num_Sr - 1) downto 0) of std_logic_vector((serial_size - 1) downto 0);

end package;
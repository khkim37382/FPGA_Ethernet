library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.STD_LOGIC_ARITH.all;
use ieee.std_logic_unsigned.all;
--use ieee.numeric_std.all;

entity chbpulse is 
	port(pulse : out STD_LOGIC;
	     clk_in : in STD_LOGIC);
end chbpulse;

--**************************************************************************--
--This brings the BAUD RATE to 2.5MHz
architecture CD_Arch of chbpulse is
signal clk_buff : std_logic;
begin
--clk2_5MHz <= clk_buff;
	PROCESS (clk_in) 
		variable count : integer := 0;
	BEGIN
		if(falling_edge(clk_in)) then
			if(count<2999990) then
				pulse<='0';
				count:=count+1;
			elsif (count < 3000000) then -- make closer together
				pulse<='1';
				count := count +1;
			else
				pulse <= '0';
				count:=0;
			end if;

		end if;
	end process;	
end CD_Arch;
--
--begin
--	clk_buff <= not clk_buff after 400ns;
--	end process;
--end CD_Arch;

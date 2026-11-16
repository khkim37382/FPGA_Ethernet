library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.STD_LOGIC_ARITH.all;
use ieee.std_logic_unsigned.all;
--use ieee.numeric_std.all;

entity Clock2_5MHz is 
	port(clk2_5MHz : out STD_LOGIC;
	     clk_in : in STD_LOGIC);
end Clock2_5MHz;

--**************************************************************************--
--This brings the BAUD RATE to 2.5MHz
architecture CD_Arch of Clock2_5MHz is
signal clk_buff : std_logic;
begin
--clk2_5MHz <= clk_buff;
	PROCESS (clk_in) 
		variable count : integer := 0;
	BEGIN
		if(rising_edge(clk_in)) then
			if(count<10) then
				clk2_5MHz<='0';
				count:=count+1;
			else
				clk2_5MHz<='1';
				count:=count+1;
			end if;
			if(count>20) then
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

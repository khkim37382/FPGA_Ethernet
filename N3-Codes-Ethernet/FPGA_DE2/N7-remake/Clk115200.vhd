library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.STD_LOGIC_ARITH.all;
use ieee.std_logic_unsigned.all;
--use ieee.numeric_std.all;

entity Clk115200 is 
	port(clk115200 : out STD_LOGIC;
	     clk_in : in STD_LOGIC);
end Clk115200;

--**************************************************************************--
--This brings the BAUD RATE to 115200
architecture CD_Arch of Clk115200 is
	signal clk_buff : std_logic;
begin
--	PROCESS (clk_in) 
--		variable count : integer := 0;
--	BEGIN
--		if(rising_edge(clk_in)) then
--			if(count<217) then
--				clk115200<='0';
--				count:=count+1;
--			else
--				clk115200<='1';
--				count:=count+1;
--			end if;
--			if(count>434) then
--				count:=0;
--			end if;
--		end if;
--	end process;
clk115200 <= clk_buff;
clk_buff <= not clk_buff after 2320ns;
end CD_Arch;

--begin
--clk115200 <= not clk115200 after 8681ns;
--end CD_Arch;

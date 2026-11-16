library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.STD_LOGIC_ARITH.all;
use ieee.std_logic_unsigned.all;
--use ieee.numeric_std.all;

entity ffmcu_clk is 
	port(ffmcu_clk : out STD_LOGIC;
	     clk_in : in STD_LOGIC);
end ffmcu_clk;

--**************************************************************************--
--This brings the BAUD RATE to 115200
architecture CD_Arch of ffmcu_clk is
	signal clk_buff : std_logic;
begin
	PROCESS (clk_in) 
		variable count : integer := 0;
	BEGIN
		if(rising_edge(clk_in)) then
			if(count<5) then
				ffmcu_clk<='0';
				count:=count+1;
			else
				ffmcu_clk<='1';
				count:=count+1;
			end if;
			if(count>10) then
				count:=0;
			end if;
		end if;
	end process;
--ffmcu_clk <= clk_buff;
--clk_buff <= not clk_buff after 2320ns;
--end CD_Arch;

--begin
--ffmcu_clk <= not ffmcu_clk after 8681ns;
end CD_Arch;

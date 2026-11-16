library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.STD_LOGIC_ARITH.all;
use ieee.std_logic_unsigned.all;
--use ieee.numeric_std.all;

entity ffmcu_trigger_clk is 
	port(clk_out : out STD_LOGIC;
			clk1 : out STD_LOGIC;
			clk2 : out STD_logic;
	     clk_in : in STD_LOGIC
		  
		  );
end ffmcu_trigger_clk;

--**************************************************************************--
--This brings the BAUD RATE to 2.5MHz
architecture CD_Arch of ffmcu_trigger_clk is
signal clk_buff, clk_enable : std_logic;
signal clk_buff_1, clk_buff_2: std_logic;



begin

clk_out <=(clk_enable); -- put a 'not' in front here to change to clk high

	PROCESS (clk_buff_2) 
		variable count : integer range -1 to 20000 := 0;
	BEGIN
		if(rising_edge(clk_buff_2)) then
			if(count=1) then
				clk_enable<='1';
				count:=count+1;
			else
				clk_enable<='0';
				count:=count+1;
			end if;
			if(count>200) then --# of 50 MHz cycles that the static mode active
				count:=0;
			end if;
		end if;
	end process;
	
	PROCESS (clk_buff_1) 
		variable count : integer range -1 to 20000 := 0;
	BEGIN
		if(rising_edge(clk_buff_1)) then
			if(count>5000) then
				clk_buff_2<='1';
				count:=count+1;
			else
				clk_buff_2<='0';
				count:=count+1;
			end if;
			if(count>10000) then --# of 50 MHz cycles that the static mode active
				count:=0;
			end if;
		end if;
	end process;
	
PROCESS (clk_in) 
		variable count : integer range -1 to 20000 := 0;
	BEGIN
		if(rising_edge(clk_in)) then
			if(count>2500) then
				clk_buff_1<='1';
				count:=count+1;
			else
				clk_buff_1<='0';
				count:=count+1;
			end if;
			if(count>5000) then --# of 50 MHz cycles that the static mode active
				count:=0;
			end if;
		end if;
	end process;


--
--PROCESS (clk_in) 
--		variable count : integer range -1 to 20000 := 0;
--	BEGIN
--		if(rising_edge(clk_in)) then
--			if(count<10) then
--				clk_buff<='0';
--				count:=count+1;
--			else
--				clk_buff<='1';
--				count:=count+1;
--			end if;
--			if(count>20) then
--				count:=0;
--			end if;
--		end if;
--	end process;	
	
	
clk1 <= clk_buff_2;
end CD_Arch;




--
--begin
--	clk_buff <= not clk_buff after 400ns;
--	end process;
--end CD_Arch;

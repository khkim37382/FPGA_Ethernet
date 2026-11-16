library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_arith.all;
use work.my_arrays.all;


entity gen_SR is
    generic(
        LENGTH: natural := 4
    );
    port(
        reg       : out std_logic_vector(LENGTH-1 downto 0);
		  enable 	: in 	std_logic;
        SI       	: in  std_logic;
		  clear		: in 	std_logic;
        clk      	: in  std_logic
    );
end entity gen_SR;

architecture Behavioral of gen_SR is
signal reg_sig : std_logic_vector(LENGTH downto 0) := "00000";
begin
	 reg <= reg_sig(LENGTH-1 downto 0);
    main_process : process(clk) is
    begin
        if rising_edge(clk) then
					if (clear = '1') then
						reg_sig <= "00000";
					else
						if (enable = '1') then
							reg_sig <= reg_sig(LENGTH-1 downto 0) & SI;
						end if;
					end if;
        end if;
    end process main_process;
end architecture Behavioral;
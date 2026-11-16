-- Generated Ethernet compatibility/reset fixes; see prepare_projects.py.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;
entity count_12bit is
    port(clk, reset, enable : in std_logic;
         q : out std_logic_vector(NUM_COUNTER_BITS-1 downto 0));
end entity;
architecture rtl of count_12bit is
    signal count : unsigned(NUM_COUNTER_BITS-1 downto 0) := (others => '0');
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if reset = '0' then count <= (others => '0');
            elsif enable = '1' then count <= count + 1;
            end if;
        end if;
    end process;
    q <= std_logic_vector(count);
end architecture;

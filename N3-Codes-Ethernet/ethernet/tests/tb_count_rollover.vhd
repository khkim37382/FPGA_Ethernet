library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;
entity tb_count_rollover is end;
architecture test of tb_count_rollover is
    signal clk : std_logic := '0';
    signal reset_n, enable : std_logic := '0';
    signal q : std_logic_vector(11 downto 0);
begin
    clk <= not clk after 10 ns;
    dut : entity work.count_12bit port map(clk, reset_n, enable, q);
    process
    begin
        wait until rising_edge(clk); wait for 1 ns;
        assert unsigned(q) = 0 severity failure;
        reset_n <= '1'; enable <= '1';
        for count in 1 to 4100 loop
            wait until rising_edge(clk); wait for 1 ns;
            assert unsigned(q) = count mod 4096 report "counter did not wrap at 12 bits" severity failure;
        end loop;
        enable <= '0';
        wait until rising_edge(clk); wait for 1 ns;
        assert unsigned(q) = 4 report "disabled counter changed" severity failure;
        reset_n <= '0';
        wait until rising_edge(clk); wait for 1 ns;
        assert unsigned(q) = 0 report "counter reset failed" severity failure;
        report "PASS: 12-bit counter interface, enable, rollover and reset";
        finish;
    end process;
end architecture;

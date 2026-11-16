library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity ShiftRegister is
  generic (
    WIDTH : integer := 4  -- Width of the shift register
  );
  port (
    clk     : in STD_LOGIC;         -- Clock input
    reset   : in STD_LOGIC;         -- Reset input
    shift_in: in STD_LOGIC; -- Input data
    shift   : in STD_LOGIC;         -- Shift control input (rising edge triggered)
    q       : out STD_LOGIC_VECTOR(WIDTH-1 downto 0) -- Output data
  );
end entity ShiftRegister;

architecture Behavioral of ShiftRegister is
  signal reg_data : STD_LOGIC_VECTOR(WIDTH-1 downto 0) := (others => '0');
begin
  process (clk, reset)
  begin
    if reset = '1' then
      reg_data <= (others => '0');
    elsif rising_edge(clk) then
      if shift = '1' then
        reg_data <= reg_data(WIDTH-2 downto 0) & shift_in;
      end if;
    end if;
  end process;

  q <= reg_data;
end architecture Behavioral;

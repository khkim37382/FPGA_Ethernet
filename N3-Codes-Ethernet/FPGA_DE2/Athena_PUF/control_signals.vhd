library IEEE;
use IEEE.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;



entity control_signals is
	port (
		ENABLE, S0RO, S1RO, S0_DIV, S1_DIV : out std_logic := '0';
		sw1, sw2, sw3, sw4, sw5, sw6 : in std_logic
	
	);
	
end control_signals;

architecture behave of control_signals is

begin				
ENABLE		<= sw1;							
S0_DIV		<= sw2;					
S1_DIV		<= sw3;							
S0RO			<= sw4;							
S1RO			<= sw5;	
end architecture;
			
			
		
		
	

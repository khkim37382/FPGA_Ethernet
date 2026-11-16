-- multiplexer for SR and SRAM serial transmission to computer
--Author: Nicholas Pieper
--npieper17@gmail.com
library ieee;
use ieee.numeric_std.all;
use ieee.std_logic_1164.all;
use work.my_arrays.all;

entity xmit_mux is
	port (
		SRAM_DATA1 : in std_logic_vector((SERIAL_SIZE - 1) downto 0);
		SRAM_READY1 : in std_logic;
		SRAM_ACK1 : out std_logic;
		SRAM_DATA2 : in std_logic_vector((SERIAL_SIZE - 1) downto 0);
		SRAM_READY2 : in std_logic;
		SRAM_ACK2 : out std_logic;
		COUNTER_DATA : in std_logic_vector((SERIAL_SIZE - 1) downto 0);
		COUNTER_READY : in std_logic;
		COUNTER_ACK : out std_logic;
		IVT_DATA : in std_logic_vector((SERIAL_SIZE -1 ) downto 0);
		IVT_READY : in std_logic;
		IVT_ACK : out std_logic;
		
		write_not_LED, write_LED : out std_logic;
		
		
		clk : in std_logic;
		reset : in std_logic;
		
		serial_out : out std_logic

		);
		
end xmit_mux;

architecture mux of xmit_mux is
	signal outval : std_logic_vector(7 downto 0);			--byte sent to uart
	signal write_mode : std_logic;								--tells whether writing or not
	signal tempin : std_logic_vector((SERIAL_SIZE - 1) downto 0); --6 byte word from SRAM or SR errors
	constant numbytes : integer := (Serial_size / 8);		--limit for iterator
	signal ack_high : std_logic;									--signals if an ack signal to lsb_main or SRAM_main is high
	
		signal loc : integer := 0;
	
	signal XMIT_READY:  std_logic;
	signal XMIT_DONE :  std_logic;
	signal write_start, write_start_prev : std_logic;
	
	constant working_sig : std_logic_vector(47 downto 0) := "010101110100111101010010010010110100100101001110";
	constant working_lim : integer := 250000000;
	signal working_count : integer := 0;
		signal count : integer := 0;
		
		signal slow_clk : std_logic;
		signal slower_clk : std_logic;
		signal counter_ack_sig, SRAM_ack_sig1,SRAM_ack_sig2, IVT_ack_sig : std_logic;
		

	
	
component u_xmit
--This is the uart transmitting module
   port(
	   sys_clk        : in std_logic;
	   sys_rst_l    : in std_logic;
	   uart_xmitH    : out std_logic;
	   xmitH        : in std_logic;
	   xmit_dataH    : in std_logic_vector(7 downto 0);
	   xmit_doneH    : out std_logic
   );
end component;

	
begin 


	counter_ack <= counter_ack_sig;
	sram_ack1 <= sram_ack_sig1;
	sram_ack2 <= sram_ack_sig2;

	ivt_ack <= ivt_ack_sig;
	write_LED <= IVT_ACK_SIG;
	write_not_LED <= ivt_ready;
	
	process(slow_clk, reset)

	variable count : integer := 0;
	constant count_lim : integer := 3;
	begin

			
		if(rising_edge(slow_clk)) then
			if (reset = '0') then
				tempin <= std_logic_vector(resize(to_signed(0, 1), serial_size));
				loc <= 0;
				write_mode <= '0';
			end if;
		
			if (write_mode = '0') then			--if we are not currently writing, waiting for input
				xmit_ready <= '0';
				if (COUNTER_READY = '1' and counter_ack_sig = '0') then	--same thing
					tempin <= COUNTER_DATA;
					write_mode<= '1';
					COUNTER_ACK_sig <= '1';
					ack_high <= '1';
				elsif (IVT_ready = '1' and ivt_ack_sig = '0') then
					tempin <= IVT_data;
					write_mode <= '1';
					IVT_ACK_sig <= '1';
					ack_high <= '1';
				elsif (SRAM_READY1 = '1' and SRAM_ack_sig1 = '0') then 	--if data here, store it and acknowledge, and start writing
					tempin <= SRAM_DATA1;
					write_mode <= '1';
					SRAM_ACK_sig1 <= '1';
					ack_high <= '1';
				elsif (SRAM_READY2 = '1' and SRAM_ack_sig2 = '0') then 	--if data here, store it and acknowledge, and start writing
					tempin <= SRAM_DATA2;
					write_mode <= '1';
					SRAM_ACK_sig2 <= '1';
					ack_high <= '1';
				end if;
			
			elsif (write_mode = '1') then	--if in the process of transmitting tempin

				if (xmit_done = '1' and xmit_ready = '0') then -- and uart is ready to accept another byte
					if (loc < NUMBYTES) then	--if more data to send, go through it
						outval <= tempin(((SERIAL_SIZE - 1) - (8 * loc)) downto ((SERIAL_SIZE - 8) - (8 * loc)));
						loc <= loc + 1;

					elsif (loc = numbytes) then	--else give carriage return
						outval <= "00001010";
						loc <= loc + 1;
					else 
						outval <= "00001101";		--then newline
						write_mode <= '0';				--tempin can now be updated
						loc <= 0;						--restart iterator
					end if;
					xmit_ready <= '1';				--signal that new byte is ready

				end if;
				
				if (xmit_ready = '1' and xmit_done = '0') then
					xmit_ready <= '0';
				end if;
			end if;

			
				if (counter_ready = '0') then
					COUNTER_ACK_sig <= '0';
				end if;
				if (sram_ready1 = '0') then
					SRAM_ACK_sig1 <= '0';
				end if;
				if (sram_ready2 = '0') then
					SRAM_ACK_sig2 <= '0';
				end if;
				if (IVT_ready = '0') then
					IVT_ACK_sig <= '0';
				end if;
		end if;

	end process;
	
	

	PROCESS (clk) 
		variable count : integer := 0;
	BEGIN
		if(rising_edge(clk)) then
			if(count<3) then
				slow_clk<='0';
				count:=count+1;
			else
				slow_clk<='1';
				count:=count+1;
			end if;
			if(count>6) then
				count:=0;
			end if;
		end if;
	end process;
	


	
xmit_mod : u_xmit 
	port map (
		sys_clk => slow_clk,
		sys_rst_l => reset,
		uart_xmitH => serial_out,
		xmitH => xmit_ready,
		xmit_dataH => outval,
		xmit_doneH => xmit_done
		);
		

	
		
	
end architecture;
			
			
		
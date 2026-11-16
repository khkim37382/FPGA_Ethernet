--This is a component for managing voltage, current, and temperature from the DUT board 
-- based on interfacing with ADS1119 ADC
-- 
library ieee;
use ieee.numeric_std.all;
use ieee.std_logic_1164.all;
use work.my_arrays.all;

entity powerdata is 
	port (	
		sda : inout std_logic;		--data line for i2c connection	
		scl : inout std_logic;		--clk line for i2c connection	
		
		clk : in std_logic;
		reset : in std_logic;
		
		DRDY : in std_logic;			--bit from ADC on DUT, goes low when there is a byte ready for reading
		
		data_out : out std_logic_vector((SERIAL_SIZE - 1) downto 0);	--data to be sent to xmit mux
		out_ready : out std_logic := '0';										--notifies xmit_mux when data is ready
		out_ack : in std_logic;														--returned from xmit_mux 
		
		LED_IVT_get : out std_logic := '1'
		
	
		);
end powerdata;

architecture behavioral of powerdata is


	signal ena : std_logic;									--signal to i2c master to latch a command to send
	signal addr : std_logic_vector(6 downto 0);		--7 bit address of i2c component on board
	signal rw : std_logic;									-- 1 for read, 0 for write command
	signal data_rw : std_logic_vector(7 downto 0);		--data to write on i2c
	signal data_rd : std_logic_vector(7 downto 0);		--data previously read in i2c module	
	signal busy : std_logic;					--'1' wheni2c_master is currently transmitting latched command
	signal ack_err : std_logic;				--goes '1' if problem with connection
	
	signal a1_reading : std_logic_vector(15 downto 0); --stores last 16-bit output from ADC 
	signal a2_reading : std_logic_vector(15 downto 0);
	signal a3_reading : std_logic_vector(15 downto 0);
	signal a4_reading : std_logic_vector(15 downto 0);
	
	
	type state_type is (rst, idle, a1_get, a2_get, a3_get, a4_get, xmittinga1a2, pause1, xmittinga3a4);
	
	
	signal state : state_type := rst;
	signal wait_cnt : integer range 0 to 500000000 := 0;

	
	signal bytes_sent : integer := 0;
	signal busy_prev : std_logic := '1';
	
	constant wait_limit : integer := 500000000; --10 seconds?
	
	constant RESET_SIG : std_logic_vector(7 downto 0) := "00000110"; --signals for specific commands to ADC, specified in datasheet
	constant START_SIG : std_logic_vector(7 downto 0) := "00001000";
	constant RDATA_SIG : std_logic_vector(7 downto 0) := "00010000";
	constant WREG_SIG : std_logic_vector(7 downto 0) := "01000000";





	
	component i2c_master 
		port (
		 clk       : IN     STD_LOGIC;                    --system clock
		 reset_n   : IN     STD_LOGIC;                    --active low reset
		 ena       : IN     STD_LOGIC;                    --latch in command
		 addr      : IN     STD_LOGIC_VECTOR(6 DOWNTO 0); --address of target slave
		 rw        : IN     STD_LOGIC;                    --'0' is write, '1' is read
		 data_wr   : IN     STD_LOGIC_VECTOR(7 DOWNTO 0); --data to write to slave
		 busy      : OUT    STD_LOGIC;                    --indicates transaction in progress
		 data_rd   : OUT    STD_LOGIC_VECTOR(7 DOWNTO 0); --data read from slave
		 ack_error : BUFFER STD_LOGIC;                    --flag if improper acknowledge from slave
		 sda       : INOUT  STD_LOGIC;                    --serial data output of i2c bus
		 scl       : INOUT  STD_LOGIC);                   --serial clock output of i2c bus
		 
	end component;
	
 begin
 
 i2c : i2c_master 
 port map (
 	clk => clk,
	reset_n => reset,
	ena => ena,
	addr => addr,
	rw => rw,
	data_wr => data_rw,
	data_rd => data_rd,
	busy => busy,
	ack_error => ack_err,
	sda => sda,
	scl => scl);

P1 : process(clk)
	
begin
if(rising_edge(clk)) then
	case state is 
		when rst => 	--reset state
			ena <= '0';
			addr <= "1000000";
			rw <= '0';
			data_rw <= "00000000";
			state <= idle;


		when idle =>
--			LED_ivt_get <= '1';
			out_ready <= '0';
			if (wait_cnt < wait_limit) then	--count for 10 seconds
				wait_cnt <= wait_cnt + 1;		
			else 
				wait_cnt <= 0;						--reset count and move to voltage reading mode
				state <= a1_get;
				bytes_sent <= 0;
			end if;
			
			
		when a1_get => 
--			LED_ivt_get <= '1';
			busy_prev <= busy;			--helpful for detecting the rising edge of 'busy'
			if(busy_prev = '0' and busy = '1') then
				bytes_sent <= bytes_sent + 1;			--when rising edge is detected, a new command is latched
			end if;
			case bytes_sent is
				when 0 =>		--fir st command, we want to write a register for checking voltage
					ena <= '1'; 
					addr <= addr;
					rw <= '0';
					data_rw <= WREG_SIG;
				when 1 => 
					data_rw <= "11000000";	--here is what goes into the register. Chooses adc input 1 and ref voltage of 2.048 V
				when 2 => 
					data_rw <= START_SIG;	--send signal to start adc conversion
				when 3 => 						--stop sending to DUT until the conversion is ready
					ena <= '0';
					if (DRDY = '0') then
						ena <= '1';
						data_rw <= RDATA_SIG;
					end if;
				when 4 => 					--we want to read the next byte
					rw <= '1';
				when 5 =>
					if (busy = '0') then
						a1_reading(15 downto 8) <= data_rd;	--store msb of conversion
					end if;
				when 6 =>
					if (busy = '0') then
						a1_reading(7 downto 0) <= data_rd;	--store lsb of conversion when the data is ready
						bytes_sent <= 0;
						state <= a2_get;
					end if;
					ena <= '0';
				when others => null;
			end case;
			
			
		when a2_get =>
			busy_prev <= busy;
			if(busy_prev = '0' and busy = '1') then
				bytes_sent <= bytes_sent + 1;
			end if;
			case bytes_sent is
				when 0 =>
					ena <= '1';
					addr <= addr;
					rw <= '0';
					data_rw <= WREG_SIG;
				when 1 => 
					data_rw <= "10100000";
				when 2 => 
					data_rw <= START_SIG;
				when 3 => 
					ena <= '0';
					if (DRDY = '0') then
						ena <= '1';
						data_rw <= RDATA_SIG;
					end if;
				when 4 => 
					rw <= '1';
				when 5 =>
					if (busy = '0') then
						a2_reading(15 downto 8) <= data_rd;
					end if;
				when 6 =>
					if (busy = '0') then
						a2_reading(7 downto 0) <= data_rd;
						bytes_sent <= 0;
						state <= a3_get;
					end if;
					ena <= '0';
				when others => null;
			end case;
			
			
		when a3_get =>
			busy_prev <= busy;
			if(busy_prev = '0' and busy = '1') then
				bytes_sent <= bytes_sent + 1;
			end if;
			case bytes_sent is
				when 0 =>
					ena <= '1';
					addr <= addr;
					rw <= '0';
					data_rw <= WREG_SIG;
				when 1 => 
					data_rw <= "11000000";					--%%%%% subject to change depending on reference voltage
				when 2 => 
					data_rw <= START_SIG;
				when 3 => 
					ena <= '0';
					if (DRDY = '0') then
						ena <= '1';
						data_rw <= RDATA_SIG;
					end if;
				when 4 => 
					rw <= '1';
				when 5 =>
					if (busy = '0') then
						a3_reading(15 downto 8) <= data_rd;
					end if;
				when 6 =>
					if (busy = '0') then
						a3_reading(7 downto 0) <= data_rd;
						bytes_sent <= 0;
						state <= a4_get;
					end if;
					ena <= '0';
				when others => null;
			end case;
			
			
			
		when a4_get =>
			busy_prev <= busy;
			if(busy_prev = '0' and busy = '1') then
				bytes_sent <= bytes_sent + 1;
			end if;
			case bytes_sent is
				when 0 =>
					ena <= '1';
					addr <= addr;
					rw <= '0';
					data_rw <= WREG_SIG;
				when 1 => 
					data_rw <= "11000000";					--%%%%% subject to change depending on reference voltage
				when 2 => 
					data_rw <= START_SIG;
				when 3 => 
					ena <= '0';
					if (DRDY = '0') then
						ena <= '1';
						data_rw <= RDATA_SIG;
					end if;
				when 4 => 
					rw <= '1';
				when 5 =>
					if (busy = '0') then
						a4_reading(15 downto 8) <= data_rd;
					end if;
				when 6 =>
					if (busy = '0') then
						a4_reading(7 downto 0) <= data_rd;
						bytes_sent <= 0;
						state <= xmittinga1a2;
					end if;
					ena <= '0';
				when others => null;
			end case;
			
			
			
		when xmittinga1a2 =>
			data_out <= "10000000" & std_logic_vector(resize(to_signed(0, 1), serial_size-40))& a1_reading & a2_reading;
			out_ready <= '1';
			if (out_ack = '1') then
				out_ready <= '0';
				state <= pause1;
			end if;
			
			
		when pause1 =>
			if out_ack = '0' then 
				state <= xmittinga3a4;
			end if;
		
		when xmittinga3a4 => 
			data_out <= "01000000" & std_logic_vector(resize(to_signed(0, 1), serial_size-40)) & a3_reading & a4_reading;
			out_ready <= '1';
			if (out_ack = '1') then
				out_ready <= '0';
				state <= idle;
			end if;
			
		end case;
	end if;
	end process;
	
end behavioral;
			
			
		
						
					
					
			
library IEEE;
use IEEE.std_logic_1164.all;
use ieee.numeric_std.all;
use work.my_arrays.all;

-- top level pins: 
--	top level pins: 
--	CLK - memory clock
--	 ME - memory ME
--	WE - memory WE
--	RCLK - shift clock shared by 3 shifters
--	SE_D, SE_ADR, SE_Q  - Shift enable for shifters
--	SI_D, SI_ADR, SI_Q - Shift input for shifters (SI_Q is for testing shift register)
--	SO_Q,SO_D, SO_ADR - shift output for shifters (SO_D and SO_ADR are for testing shift registers)
--	LOAD_Q - shift register load for Q segment (32 bits)

--5/28/2020: Changed from 1 single shifter to 3 separate ones for D, ADR and Q.



entity SRAM_main2 is

generic (

	constant num_addrbits : integer := 5;
	constant num_databits : integer := 10;
	constant num_rmbits: integer := 7;
	constant waitlimit : integer := 50000000;
	constant sram_number : std_logic_vector(3 downto 0) := "0000";
	constant read_margin : std_logic_vector(6 downto 0) := "0000000";
	constant am_i_tcam : std_logic_vector(0 downto 0) := "0"
		--constant read_margin_array : array (12 downto 0) of std_logic_vector(6 downto 0) := ("0000000", "0000100", "0001000","0001100","0010000","0010100","0011000","0011111","0100000","0110000","1000000","1100000","1111111")


);
	port (
		sys_clk	: 	in std_logic;	-- internal clock to run at 50MHz
		reset		:	in std_logic;
		enable 	: 	in std_logic;
		reading_status : out std_logic;
		
		data_select : in std_logic_vector(1 downto 0);
		sram_addr_select : in std_logic;
		--read_margin_select : in std_logic_vector(1 downto 0);
		en_alt_in : in std_logic := '0';
		rm_array : in std_logic;
		
		RCLK		: 	out std_logic := '0';	-- q/addr/data Shift register clock
		ME 		: 	out std_logic := '1'; 	-- memory enable
		RE 		: 	out std_logic := '1'; 	-- read enable
		WE 		: 	out std_logic := '0';	-- write enable
		MCLK		:	out std_logic := '0';	-- memory clock
		SE_D, SE_ADR, SE_Q, SE_RM, SI_D, SI_ADR, SI_Q, SI_RM	: out std_logic;
		SO_Q, SO_ADR, SO_D, SO_RM	: in std_logic := '0';
		
		
		serial_out : out std_logic_vector((SERIAL_SIZE - 1) downto 0); --data to be sent to XMIT data
		xmit_ready : out std_logic;
		xmit_ack : in std_logic;
		
		LED_err  : out std_logic;
		LED_read : out std_logic;
		LED_init : out std_logic;
		--LED_rm 	: out std_logic_vector(2 downto 0);
		
		load_q : out std_logic
		);
	
end SRAM_main2;

architecture behave of SRAM_main2 is
	
	component Clock2_5MHz is 
		port(clk2_5MHz : out STD_LOGIC;
			  clk_in : in STD_LOGIC);
	end component;
	
	type state_type is (wrbuf, LOAD1, set_si, si_rclk1, si_rclk2, so_rclk1, so_rclk2, compare, pull_so, mem_cyc, inc_addr, waiting, xmit, load2, load3, load_tcam1, load_tcam2, signal_cyc_end, wait_end, read_prep);
	signal state : state_type := set_si;
	
	type read_margin_array2 is array (0 to 9) of std_logic_vector(6 downto 0);
	signal read_margin_array : read_margin_array2  := ("0000000","0010000","0010001","0010010","0010011","0010100","0010101","0010111","0110000","1110000");
	
	signal addr : unsigned(num_addrbits-1 downto 0):=to_unsigned(0, num_addrbits);		--13 bits of address
	signal data, data_compare : std_logic_vector(num_databits-1 downto 0);	--32 bits of data input
	--signal read_margin : std_logic_vector(6 downto 0):= "0000000";
	signal Q : std_logic_vector(num_databits downto 0);	--holds the output from the SRAM CHANGE TO 75
	signal enable_prev : std_logic := '0';
	
	signal in_idx : integer range num_databits-1 downto 0 := num_databits-1;		--
	signal out_idx : integer range num_databits downto 0 := 0;
	signal waitcount : integer range 0 to waitlimit;	
	signal rm_idx : integer range 0 to 12 := 0;

	signal slow_clock : std_logic;
	signal RCLK_sig : std_logic := '0';
	signal MCLK_sig :std_logic := '0';
	signal WE_buff : std_logic := '0';
	
	signal xmit_ready_sig : std_logic := '0';
	signal addr_vec : std_logic_vector(num_addrbits - 1 downto 0);
	signal chb : std_logic_vector(num_databits -1 downto 0);


	constant read_prep_lim : integer := 4000000;
	signal read_prep_wait : integer range 0 to read_prep_lim;

	--------------- Read Cycle End Signal ----------------------
	--signal read_cycle_end: std_logic := '0';
	
	--------------- should wait signal ----------------------
	signal wait_state: state_type := set_si;

begin
	
	clockdown : Clock2_5MHz	
		port map (
		clk2_5MHz => slow_clock,
		clk_in => sys_clk
		);
		
		gen_chb: for ii in 0 to num_databits/2 -1 generate
			chb(ii*2+1 downto ii*2) <= "10";
		end generate;
		
	with sram_addr_select & data_select select 
		data <= 	std_logic_vector(resize(to_signed(0, 1), num_databits)) when "000",
					std_logic_vector(resize(to_signed(-1, 1), num_databits)) when "011",
					not chb 		when "001",
					chb 			when "010",
					std_logic_vector(resize(to_signed(0, 1), num_databits-num_addrbits-num_addrbits-num_addrbits)) & addr_vec & addr_vec & addr_vec when others;
	--with read_margin_select select 
		--read_margin <= "0000000" when "00",
			--				"0100000" when "01",
				--			"1000000" when "10", 
					--		"0000000" when others;
		
	MCLK <= MCLK_sig;
	RCLK <= RCLK_sig;
	WE <= WE_buff;
	me <= '1';
	xmit_ready <= xmit_ready_sig;
	ADDR_vec <= std_logic_vector(addr);
	--	errors <= Q(num_databits downto 1) xor data;
	RE <= not WE_buff;
	--LED_rm <= read_margin(6 downto 4);

	process (slow_clock, reset)
	begin
	
		if (reset = '0') then
			addr <= to_unsigned(2**num_addrbits, num_addrbits);		--beginning
			in_idx <= num_databits-1;	--start with MSB for both shifting in and out of shift register
			out_idx <= num_databits;
			state <= inc_addr;											
			waitcount <= 0;
			xmit_ready_sig <= '0';
			
		elsif (rising_edge(slow_clock)) then
		
			case state is 		
			
			when set_si => 
				wait_state <= set_si;
				if(en_alt_in = '1') then 
					if(addr = to_unsigned(2**0, num_addrbits)) then 
						SI_D <= not data(in_idx);
					elsif (addr = to_unsigned((2**num_addrbits)/2-1, num_addrbits)) then 
						SI_D <= not data(in_idx);
					elsif (addr >= 2**num_addrbits-1) then 
						SI_D <= not data(in_idx);
					else
						SI_D <= data(in_idx);
					end if;
				else 
					SI_D <= data(in_idx); 	--set shift register input
				end if;
				SE_D <= '1';
				if (in_idx < num_Addrbits) then
					SI_ADR <= addr_vec(in_idx); --ADR SR is 13 bits long
					SE_ADR <= '1';
				else 
					SE_ADR <= '0';
				end if;
				
				if (in_idx < num_rmbits) then
					SI_RM <= read_margin(in_idx); --ADR SR is 13 bits long
					SE_RM <= '1';
				else 
					SE_RM <= '0';
				end if;
								

				state <= si_rclk1;


			when si_rclk1 =>
				RCLk_sig <= '1';
				state <= si_rclk2;
			
			when si_rclk2 =>
				RCLk_sig <= '0';
				if in_idx <= 0 then
					state <= mem_cyc;
					SE_ADR <= '0';
					SE_RM <= '0';
				else
					in_idx <= in_idx - 1;	--otherwise, shift more out
					state <= set_si;
				end if;
				
			when so_rclk1 =>
				RCLK_sig <= '1';
				load_q <= '0';
				SE_Q <= '1';
				state <= so_rclk2;
				
			when so_rclk2 =>
				RCLK_sig <= '0';
				load_q <= '0';
				SE_Q <= '1';
				state <= pull_so;			
				
			when pull_so =>
				mclk_sig <= '0';
				WE_buff <= '0';
				Q(out_idx) <= SO_Q;		-- pull the output bit
				if (out_idx = 0) then				-- if all data out has been read
					out_idx <= num_databits;	--reset the index for reading out data 
					if(en_alt_in = '1') then 
						if(addr = to_unsigned(2**0, num_addrbits)) then 
							serial_out <= "1110" & sram_number & "0" & read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) & std_logic_vector(addr) & (Q(num_databits downto 1) xor (not data));
						elsif (addr = to_unsigned((2**num_addrbits)/2-1, num_addrbits)) then 
							serial_out <= "1110" & sram_number & "0" &  read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) & std_logic_vector(addr) & (Q(num_databits downto 1) xor (not data));
						elsif (addr >= 2**num_addrbits-1) then 
							serial_out <= "1110" & sram_number & "0" &  read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) & std_logic_vector(addr) & (Q(num_databits downto 1) xor (not data));
						else
							serial_out <= "1110" & sram_number &"0" &  read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) &  std_logic_vector(addr) & (Q(num_databits downto 1) xor data);
						end if;
					else
						serial_out <= "1110" & sram_number & "0" & read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) & std_logic_vector(addr) & (Q(num_databits downto 1) xor data);
					end if;
					state <= compare;				--go to next address
				else 
					state <= so_rclk1;
					out_idx <= out_idx - 1;			--otherwise, cycle again and get next value
				end if;
					
			when mem_cyc => 
				SE_D <= '0';
				RCLK_sig <= '0';
				MCLK_sig <= '1';								
				if (WE_buff = '0') then
					if (am_i_tcam = "1") then
						state <= load_tcam1;			--else (if we just read) begin shfiting out data
					--LOAD_q <= '1';
					else
						state <= load1;
					end if;
				elsif (WE_buff = '1') then
					state <= wrbuf;
				end if;	

			when wrbuf=>
				mclk_sig <= '0';
				WE_buff <= '0';
				state <= inc_addr;
				
			when load_tcam1 =>
				mclk_sig <= '0';
				RCLK_sig <= '0';
				load_q <= '0';
				state <= load_tcam2;
				
			when load_tcam2 =>
				mclk_sig <= '1';
				RCLK_sig <= '0';
				load_q <= '0';
				state <= load1;
	
			
			when load1 =>
				mclk_sig <= '0';
				RCLK_sig <= '0';
				load_q <= '1';
				state <= load2;
			
			when load2 => 
				rclk_sig <= '1';
				state <= load3;
				
			when load3 => 
				rclk_sig <= '0';
				load_q <= '0';
				se_q <= '1';
				state <= pull_so;
				
			when compare => 
				RCLK_sig <= '0';
				load_q <= '0';
				if(en_alt_in = '1') then 
					if(addr = to_unsigned(2**0, num_addrbits) or addr = to_unsigned((2**num_addrbits)/2-1, num_addrbits) or addr >= 2**num_addrbits-1) then
						if (Q(num_databits downto 1) /= not data) then
							xmit_ready_sig <= '1';
							if (xmit_ack = '1') then
								state <= xmit;
								xmit_ready_sig <= '0';
							end if;
						else
							state <= inc_addr;
							xmit_ready_sig <= '0';
						end if;
					else 
						if (Q(num_databits downto 1) /= data) then
							xmit_ready_sig <= '1';
							if (xmit_ack = '1') then
								state <= xmit;
								xmit_ready_sig <= '0';
							end if;
						else
							state <= inc_addr;
							xmit_ready_sig <= '0';
						end if;
					end if;
				else 
					if (Q(num_databits downto 1) /= data) then
						xmit_ready_sig <= '1';
						if (xmit_ack = '1') then
							state <= xmit;
							xmit_ready_sig <= '0';
						end if;
					else
						state <= inc_addr;
						xmit_ready_sig <= '0';
					end if;
				end if;
				
			when xmit =>
				if (xmit_ack = '0') then
					WE_buff <= '1';
					--state <= Mem_cyc;
					if (wait_state = signal_cyc_end) then
						state <= waiting;
					elsif (wait_state = wait_end) then
						state <= set_si;
						state <= read_prep;
					else 
						WE_buff <= '1';
						state <= Mem_cyc;
					end if;

				end if;
			
				
				
			when inc_addr =>
				SE_Q <= '0';
				if (addr >= 2**num_addrbits-1) then	--if read all addresses, reset to zero and wait n seconds
					--state <= waiting;
					addr <= to_unsigned(0, num_addrbits);
					--LED_err <= '1';
					state <= signal_cyc_end;
				else
					addr <= addr + to_unsigned(1, num_addrbits);	--else go to next address and start shifting that in
					state <= set_si;
					in_idx <= num_databits-1;	--start with MSB for both shifting in and out of shift register
					out_idx <= num_databits;
					SE_D <= '1';
					--LED_err <= '0';
				end if;
				 
 
			when waiting =>
				if (enable = '1' and enable_prev = '0') then			--if reached n seconds, check SRAM again
					reading_status <= '0';
					--LED_init <= '0';
					waitcount <= 0;		
					--state <= set_si;
					
--					if(rm_array = '1') then 
--						if(rm_idx >= 10) then 
--							rm_idx <= 0;
--							read_margin <= read_margin_array(rm_idx);
--						else
--							rm_idx <= rm_idx + 1;
--							read_margin <= read_margin_array(rm_idx);
--						end if;
--					else 
--						read_margin <= read_margin_array(0);
--					end if;
					
					state <= wait_end;
					in_idx <= num_databits-1;	--start with MSB for both shifting in and out of shift register
					out_idx <= num_databits;
					SE_D <= '1';
				else 
					reading_status <= '1';
					--LED_init <= '1';
					waitcount <= waitcount + 1;
				end if;
				enable_prev <= enable;
			when signal_cyc_end =>
				--transmit “0-0”
				serial_out <= "1110" & sram_number &"0" & read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits))  & std_logic_vector(to_unsigned(0, num_addrbits)) & std_logic_vector(to_unsigned(0, num_databits));
				xmit_ready_sig <= '1';
				wait_state <= signal_cyc_end; -- need to start waiting
				--LED_read <= '1';
				if (xmit_ack = '1') then
					state <= xmit;
					xmit_ready_sig <= '0';
				end if;
				
				
			--------------- signal laptop wait period ended ----------------------
			when wait_end =>
			-- transmit "1-0" (which is impossible otherwise)
				serial_out <= "1110" & sram_number &"0" & read_margin & std_logic_vector(resize(to_unsigned(0, 1), serial_size-16-num_addrbits-num_databits)) & std_logic_vector(to_unsigned(1, num_addrbits)) & std_logic_vector(to_unsigned(0, num_databits));
				xmit_ready_sig <= '1';
				wait_state <= wait_end; -- waiting period finished
				--LED_read <= '0';
				if (xmit_ack = '1') then
					state <= xmit;
					xmit_ready_sig <= '0';
				end if;
				
			--------------- buffer time after voltage raised back to 0.75 ----------------------
			when read_prep =>
				if (read_prep_wait > read_prep_lim) then			--if reached n seconds, start reading from SRAM
					read_prep_wait <= 0;
					state <= set_si;
				else
					read_prep_wait <= read_prep_wait + 1;
				end if;
				

			end case;
		end if;
		
	end process;
	

	

end architecture;
			
			
		
		
	
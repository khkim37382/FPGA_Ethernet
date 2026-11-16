--
-- DE2-115 top-level module (entity declaration)
--
-- Yoni Xiong
-- yoni.xiong@vanderbilt.edu
-- **do not contact me about this**

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-----------------------------------------------------------------------------------------------------------------------

entity RO_FREQ_CYCLE is

  port (
   
   CLOCK_50 	: in std_logic;                     -- 50 MHz
   CLOCK2_50 	: in std_logic;                     -- 50 MHz
   CLOCK3_50 	: in std_logic;                     -- 50 MHz
	 
   LEDG 			: out std_logic_vector(8 downto 0); -- Green LEDs (active high)
   LEDR 			: out std_logic_vector(17 downto 0);-- Red LEDs (active high)
  
   SW  			: in std_logic_vector(17 downto 0);	-- DPDT switches

	GPIO 			: inout std_logic_vector(35 downto 0); -- GPIO

	UART_CTS		: in std_logic;
	UART_RTS		: out std_logic;
	UART_RXD		: in std_logic;
	UART_TXD		: out std_logic;
	
	
	GPIO0_0		: in std_logic;
	GPIO0_2		: in std_logic;
	GPIO1_0		: in std_logic;
	GPIO1_2		: in std_logic;

	GPIO0_1		: inout std_logic;
	GPIO0_10		: inout std_logic;
	GPIO0_11		: inout std_logic;
	GPIO0_12		: inout std_logic;
	GPIO0_13		: inout std_logic;
	GPIO0_14		: inout std_logic;
	GPIO0_15		: inout std_logic;
	GPIO0_16		: inout std_logic;
	GPIO0_17		: inout std_logic;
	GPIO0_18		: inout std_logic;
	GPIO0_19		: inout std_logic;

	GPIO0_20		: inout std_logic;
	GPIO0_21		: inout std_logic;
	GPIO0_22		: inout std_logic;
	GPIO0_23		: inout std_logic;
	GPIO0_24		: inout std_logic;
	GPIO0_25		: inout std_logic;
	GPIO0_26		: inout std_logic;
	GPIO0_27		: inout std_logic;
	GPIO0_28		: inout std_logic;
	GPIO0_29		: inout std_logic;
	GPIO0_3		: inout std_logic;
	GPIO0_30		: inout std_logic;
	GPIO0_31		: inout std_logic;
	GPIO0_32		: inout std_logic;
	GPIO0_33		: inout std_logic;
	GPIO0_34		: inout std_logic;
	GPIO0_35		: inout std_logic;
	GPIO0_4		: inout std_logic;
	GPIO0_5		: inout std_logic;
	GPIO0_6		: inout std_logic;
	GPIO0_7		: inout std_logic;
	GPIO0_8		: inout std_logic;
	GPIO0_9		: inout std_logic;
		 
	GPIO1_1		: inout std_logic;
	GPIO1_10		: inout std_logic;
	GPIO1_11		: inout std_logic;
	GPIO1_12		: inout std_logic;
	GPIO1_13		: inout std_logic;
	GPIO1_14		: inout std_logic;
	GPIO1_15		: inout std_logic;
	GPIO1_16		: inout std_logic;
	GPIO1_17		: inout std_logic;
	GPIO1_18		: inout std_logic;
	GPIO1_19		: inout std_logic;

	GPIO1_20		: inout std_logic;
	GPIO1_21		: inout std_logic;
	GPIO1_22		: inout std_logic;
	GPIO1_23		: inout std_logic;
	GPIO1_24		: inout std_logic;
	GPIO1_25		: inout std_logic;
	GPIO1_26		: inout std_logic;
	GPIO1_27		: inout std_logic;
	GPIO1_28		: inout std_logic;
	GPIO1_29		: inout std_logic;
	GPIO1_3		: inout std_logic;
	GPIO1_30		: inout std_logic;
	GPIO1_31		: inout std_logic;
	GPIO1_32		: inout std_logic;
	GPIO1_33		: inout std_logic;
	GPIO1_34		: inout std_logic;
	GPIO1_35		: inout std_logic;
	GPIO1_4		: inout std_logic;
	GPIO1_5		: inout std_logic;
	GPIO1_6		: inout std_logic;
	GPIO1_7		: inout std_logic;
	GPIO1_8		: inout std_logic;
	GPIO1_9		: inout std_logic
	   
   );
  
end RO_FREQ_CYCLE;

-----------------------------------------------------------------------------------------------------------------------

architecture behave of RO_FREQ_CYCLE is

  component RO_CYCLER is 
  
  	port (
		i_Clk       : in  std_logic;
		i_Slow_Clk	: in 	std_logic; 
		i_Enable 	: in 	std_logic; 
		i_Reset		: in 	std_logic; 
		i_Message 	: in 	std_logic_vector (3 downto 0); 
		i_RX			: in 	std_logic; 
		i_TX			: out std_logic;
		o_done		: out std_logic;
		o_RO 			: out std_logic_vector (3 downto 0) 

		); 
	end  component RO_CYCLER; 

   
	type t_SM is (B0, B1, B2, B3);																		-- board state machine states	
	signal SM_Main : t_SM := B0;																			-- start with Board 0
	signal source_clk					: std_logic;														-- 50M
	signal slow_clk					: std_logic:= '0';												-- slow clock
	signal clk_counter				: unsigned(32 downto 0);										-- count 200000000
	signal message 					: std_logic_vector(3 downto 0) := x"3";					--	pass to sub-SM for transmission
	signal done 						: std_logic; 														-- signal from sub-SM to continue
	signal enable						: std_logic; 														-- enable cycling
	signal reset						: std_logic := '0';												-- reset cycling
	signal state						: std_logic_vector (2 downto 0):= "001"; 					-- board state
	signal active_RO 					: std_logic_vector (3 downto 0); 							-- RO state
	signal control						: std_logic_vector (4 downto 0);								-- current control signal
	signal brd_bus_0, brd_bus_1 	:std_logic_vector (5 downto 0);								-- GPIO bus to control 



-----------------------------------------------------------------------------------------------------------------------

begin


-- define our clock source as the first 50MHz clock
source_clk <= CLOCK_50;

-- light leftmost LED for done RO cycling 
LEDR(17) <= done;

-- light rightmost green LEDs to indicate current board 
LEDG(2 downto 0) <= state;

-- enable/disable cycling with SW(0)
enable <= SW(0);

-- Middle red LEDs show active RO key
LEDR(3 downto 0) <= active_RO;

-- VBIAS, ENABLE, S1 DIV, S0 DIV, S1 RO, S0 RO
(GPIO(30),GPIO(20),GPIO(26),GPIO(22),GPIO(28),GPIO(24)) <= brd_bus_0;		
(GPIO1_30,GPIO1_20,GPIO1_26,GPIO1_22,GPIO1_28,GPIO1_24) <= brd_bus_1;

wire [29:0] counter;//needs to be modified each time

wire clk2_5; 


wire internal_reset; //internal reset signal that reset set and data counters

wire [95:0] lsb_data;
wire lsb_xmit_ready;
wire lsb_xmit_ack1;

wire [95:0] sram_data;
wire sram_xmit_ready;
wire sram_xmit_ack;

wire [95:0] ivt_data;
wire ivt_xmit_ready;
wire ivt_xmit_ack;

wire [1:0] SRAM_data_select;

assign  GPIO[7] = SW[0]; //SR data select
assign 	GPIO[9] = SW[1];//DATA in

assign	SRAM_data_select[1] =  SW[3];
assign	SRAM_data_select[0] =  SW[2];

assign counter[0] = HSMC_CLKIN_N2;
assign counter[1]= HSMC_RX_D_N[16];
assign counter[2] = HSMC_CLKIN_P2;
assign counter[3] = HSMC_RX_D_P[16];
assign counter[4] = HSMC_TX_D_N[16];
assign counter[5] = HSMC_RX_D_N[15];
assign counter[6] = HSMC_TX_D_P[16];
assign counter[7] = HSMC_RX_D_P[15];
assign counter[8] = HSMC_TX_D_N[15];
assign counter[9] = HSMC_RX_D_N[14];
assign counter[10] = HSMC_TX_D_P[15];
assign counter[11] = HSMC_RX_D_P[14];
assign counter[12] = HSMC_TX_D_N[14];
assign counter[13] = HSMC_RX_D_N[13];
assign counter[14] = HSMC_TX_D_P[14];
assign counter[15] = HSMC_RX_D_P[13];
assign counter[16] = HSMC_CLKOUT_N2;
assign counter[17] = HSMC_RX_D_N[12];
assign counter[18] = HSMC_CLKOUT_P2;
assign counter[19] = HSMC_RX_D_P[12];
assign counter[20] = HSMC_TX_D_N[13];
assign counter[21] = HSMC_RX_D_N[11];
assign counter[22] = HSMC_TX_D_P[13];
assign counter[23] = HSMC_RX_D_P[11];
assign counter[24] = HSMC_TX_D_N[12];
assign counter[25] = HSMC_RX_D_N[10];
assign counter[26] = HSMC_TX_D_P[12];
assign counter[27] = HSMC_RX_D_P[10];
assign counter[28] = HSMC_TX_D_N[11];
assign counter[29] = HSMC_RX_D_N[9];


assign GPIO[23] = KEY[1]; //reset ADC
assign GPIO[13] = 0; //LOAD_B
assign GPIO[3] = 0; //CLR_CTR
assign GPIO[5] = clk2_5; //CLK_PISO
assign GPIO[1] = clk2_5;


//=======================================================
//  Structural coding
//=======================================================





//lsb_main sets up main_controller.vhd, lsb_counter.vhd, and xmit modules
lsb_main lsb_main_test 
(
.reset(KEY[0]),
.sys_clk(CLOCK_50),
.counter_inmain(counter),
//serial ports
.data_out(lsb_data),
.xmit_ready(lsb_xmit_ready),
.xmit_ack(lsb_xmit_ack1)
);


SRAM_main #(
.num_addrbits(16),
.num_databits(128),
.waitlimit(5000000),
.num_rmbits(7),
.sram_number("0000"),
.read_margin("0000000")
)sram_test1 
(
.sys_clk(CLOCK_50),
.reset(KEY[0]),
.data_select(SRAM_data_select),
.enable(1),
.reading_status(LEDR[9]),

.RCLK(GPIO[6]),
.ME(GPIO[4]),
.WE(GPIO[18]),
.MCLK(GPIO[0]),

.SE_D(GPIO[10]),
.SI_ADR(GPIO[14]),
.SE_Q(GPIO[12]),
.SI_D(HSMC_TX_D_P[11]),
.SE_ADR(GPIO[8]),
.SI_Q(GPIO[16]),
.SO_Q(HSMC_RX_D_P[9]),
.SO_ADR(HSMC_TX_D_N[10]),
.SO_D(HSMC_TX_D_P[10]),

.load_q(GPIO[2]),

//serial ports
.serial_out(sram_data),
.xmit_ready(sram_xmit_ready),
.xmit_ack(sram_xmit_ack), 

.LED_err(LEDR[0]),
.LED_init(LEDR[1]),
.LED_read(LEDR[2])
);



SRAM_main #(
.num_addrbits(16),
.num_databits(128),
.waitlimit(5000000),
.num_rmbits(7),
.sram_number("0000"),
.read_margin("0000000")
)sram_test2 
(
.sys_clk(CLOCK_50),
.reset(KEY[0]),
.data_select(SRAM_data_select),
.enable(1),
.reading_status(LEDR[9]),

.RCLK(GPIO[6]),
.ME(GPIO[4]),
.WE(GPIO[18]),
.MCLK(GPIO[0]),

.SE_D(GPIO[10]),
.SI_ADR(GPIO[14]),
.SE_Q(GPIO[12]),
.SI_D(HSMC_TX_D_P[11]),
.SE_ADR(GPIO[8]),
.SI_Q(GPIO[16]),
.SO_Q(HSMC_RX_D_P[9]),
.SO_ADR(HSMC_TX_D_N[10]),
.SO_D(HSMC_TX_D_P[10]),

.load_q(GPIO[2]),

//serial ports
.serial_out(sram_data),
.xmit_ready(sram_xmit_ready),
.xmit_ack(sram_xmit_ack), 

.LED_err(LEDR[0]),
.LED_init(LEDR[1]),
.LED_read(LEDR[2])
);

powerdata power //monitors voltage, current, and temperature of board
(
.sda(GPIO[27]),
.scl(GPIO[25]),

.clk(CLOCK_50),
.reset(KEY[0]),

.DRDY(GPIO[29]),

.data_out(ivt_data),
.out_ready(ivt_xmit_ready),
.out_ack(ivt_xmit_ack)
);



xmit_mux serial_xmit
(
.SRAM_DATA1(sram_data),
.SRAM_READY1(sram_xmit_ready),
.SRAM_ACK1(sram_xmit_ack),

.SRAM_DATA2(sram_data),
.SRAM_READY2(sram_xmit_ready),
.SRAM_ACK2(sram_xmit_ack),

.COUNTER_DATA(lsb_data),
.COUNTER_READY(lsb_xmit_ready),
.COUNTER_ACK(lsb_xmit_ack1),

.IVT_DATA(ivt_data),
.IVT_READY(ivt_xmit_ready),
.ivt_ACK(ivt_xmit_ack),
		
.clk(CLOCK_50),
.reset(KEY[0]),
		
.serial_out(UART_TXD)
);

control_signals control
(
		.ENABLE_001(GPIO[20]),
		.S0DIV_001(GPIO[22]),
		.S1DIV_001(GPIO[26]),
		.S0RO_001(GPIO[24]),
		.S1RO_001(GPIO[28]),
		.VBIAS_001(GPIO[30]),
		.ENABLE(GPIO[11]),
		.S0RO(GPIO[15]),
		.S1RO(GPIO[17]),
		.S0_DIV(GPIO[19]),
		.S1_DIV(GPIO[21]),
		.sw0(SW[4]), 
		.sw1(SW[5]),//enable
		.sw2(SW[6]),//S0DIV
		.sw3(SW[7]), //S1Div
		.sw4(SW[8]),//S0R0
		.sw5(SW[9]), //S1Ro
		.sw6(SW[10])//VBIAS_001
);

Clock2_5MHz slow_clock
(
.clk2_5MHz(clk2_5),
.clk_in(CLOCK_50)
);
-----------------------------------------------------------------------------------------------------------------------


-- instansiate a RO cycling state machine
CYCLE : RO_CYCLER
	port map (
		i_clk => CLOCK_50,
		i_Slow_Clk => slow_clk,
		i_Enable => enable, 
		i_Reset => reset,
		i_Message => message,
		i_RX => UART_RXD,
		i_TX => UART_TXD,
		o_done => done,
		o_RO => active_RO
	); 
	

-- make a slow clk on slow_clk node using 50M clock
div_counter: process (source_clk) begin 
	if (rising_edge(source_clk)) then 
		if (clk_counter >= 800000000) then 		--200000000
			clk_counter <= (others => '0'); 		-- reset counter to zero
			slow_clk <= '1';							-- pulse output high for 20ns
		else 
			clk_counter <= clk_counter + 1; 		-- increment counter;
 			slow_clk <= '0';
		end if;
	end if; 
end process div_counter;


-- cycle boards when all 16 ROs are measured on previous board
master_machine: process(enable, done, slow_clk)
begin
	if (rising_edge(slow_clk)) then  
		if done = '1' and enable = '1' then
			reset <= '1';
			case SM_Main is 
				when B0 =>
					state <= "010";
					SM_Main <= B1; 
					message <= x"4";
				when B1 => 
					state <= "001";
					SM_Main <= B0; 
					message <= x"3"; 
				when others => 
					state <= "001";
					message <= x"3";	
			end case; 
		else 
			reset <= '0';
		end if; 
	end if; 
end process master_machine;


-- create control signal based on current RO that is being sampled
decode_RO_ctrl: process(active_RO) 
begin 
	case(active_RO) is 
		when x"0" => control <= "10000";
		when x"1" => control <= "10001";	
		when x"2" => control <= "10010";	
		when x"3" => control <= "10011";	
		when x"4" => control <= "10100";
		when x"5" => control <= "10101";	
		when x"6" => control <= "10110";	
		when x"7" => control <= "10111";		
		when x"8" => control <= "11000";
		when x"9" => control <= "11001";	
		when x"a" => control <= "11010";	
		when x"b" => control <= "11011";	
		when x"c" => control <= "11100";
		when x"d" => control <= "11101";	
		when x"e" => control <= "11110";	
		when x"f" => control <= "11111";		
		when others => control <= "10000"; 
	end case; 
end process decode_RO_ctrl;

ctrl_RO: process(SM_Main)
begin 
	case (SM_Main) is
		when B0 => 
			brd_bus_0 <= '1' & control;
			brd_bus_1 <= '1' & "10001";
		
		when B1 => 
			brd_bus_1 <= '1' & control;
			brd_bus_0 <= '1' & "10001";

		when others => 
			brd_bus_0 <= '1' & "10001";
			brd_bus_1 <= '1' & "10001";	
		end case; 
end process ctrl_RO;

end behave;
 
 

module DE2_115(

	//////////// CLOCK //////////
	CLOCK_50,
	CLOCK2_50,
	CLOCK3_50,

	//////////// LED //////////
	LEDG,
	LEDR,

	//////////// KEY //////////
	KEY,

	//////////// SW //////////
	SW,

	//////////// SEG7 //////////
	HEX0,
	HEX1,
	HEX2,
	HEX3,
	HEX4,
	HEX5,
	HEX6,
	HEX7,

	//////////// RS232 //////////
	UART_CTS,
	UART_RTS,
	UART_RXD,
	UART_TXD,

	//////////// I2C for HSMC  //////////
	I2C_SCLK,
	I2C_SDAT,

	//////////// GPIO, GPIO connect to GPIO Default - 1.8V //////////
	GPIO,

	//////////// HSMC, HSMC connect to HSMC Default - 1.8V //////////
	HSMC_CLKIN_N1,
	HSMC_CLKIN_N2,
	HSMC_CLKIN_P1,
	HSMC_CLKIN_P2,
	HSMC_CLKIN0,
	HSMC_CLKOUT_N1,
	HSMC_CLKOUT_N2,
	HSMC_CLKOUT_P1,
	HSMC_CLKOUT_P2,
	HSMC_CLKOUT0,
	HSMC_D,
	HSMC_RX_D_N,
	HSMC_RX_D_P,
	HSMC_TX_D_N,
	HSMC_TX_D_P
);

//=======================================================
//  PARAMETER declarations
//=======================================================


//=======================================================
//  PORT declarations
//=======================================================

//////////// CLOCK //////////
input 		          		CLOCK_50;
input 		          		CLOCK2_50;
input 		          		CLOCK3_50;

//////////// LED //////////
output		     [8:0]		LEDG;
output		    [17:0]		LEDR;

//////////// KEY //////////
input 		     [3:0]		KEY;

//////////// SW //////////
input 		    [17:0]		SW;

//////////// SEG7 //////////
output		     [6:0]		HEX0;
output		     [6:0]		HEX1;
output		     [6:0]		HEX2;
output		     [6:0]		HEX3;
output		     [6:0]		HEX4;
output		     [6:0]		HEX5;
output		     [6:0]		HEX6;
output		     [6:0]		HEX7;

//////////// RS232 //////////
output		          		UART_CTS;
input 		          		UART_RTS;
input 		          		UART_RXD;
output		          		UART_TXD;

//////////// I2C for HSMC  //////////
output		          		I2C_SCLK;
inout 		          		I2C_SDAT;

//////////// GPIO, GPIO connect to GPIO Default - 1.8V //////////
inout 		    [35:0]		GPIO;

//////////// HSMC, HSMC connect to HSMC Default - 1.8V //////////
input 		          		HSMC_CLKIN_N1;
input 		          		HSMC_CLKIN_N2;
input 		          		HSMC_CLKIN_P1;
input 		          		HSMC_CLKIN_P2;
input 		          		HSMC_CLKIN0;
inout		          		HSMC_CLKOUT_N1;
inout		          		HSMC_CLKOUT_N2;
inout		          		HSMC_CLKOUT_P1;
inout		          		HSMC_CLKOUT_P2;
output		          		HSMC_CLKOUT0;
inout 		     [3:0]		HSMC_D;
inout 		    [16:0]		HSMC_RX_D_N;
inout 		    [16:0]		HSMC_RX_D_P;
inout 		    [16:0]		HSMC_TX_D_N;
inout 		    [16:0]		HSMC_TX_D_P;


//=======================================================
//  REG/WIRE declarations
//=======================================================

endmodule

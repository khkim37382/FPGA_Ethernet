from datetime import datetime
import serial.tools.list_ports
import time
import serial
import math
import sys
import os


class FPGAScript:
    # User specified path for folder
    PATH = "./"

    # Data stream tags for N3
    N3_SR_TAG = int('00100000', 2) 
    N3_SRAM_TAG_0 = int('11100000', 2)
    N3_SRAM_TAG_1 = int('11100001', 2)
    N3_FFMCU_TAG = int('01100000',2)
    N3_I2C1 = int('10000000', 2)
    N3_I2C2 = int('01000000', 2)

    # ADC Params
    N3_THERMISTORNOMINAL = 10000
    N3_THERMISTORBASELINE =  850 # tune this value!!
    N3_INTERNAL_VOLT_REF = 2.048 # internal voltage reference of ADC

    TEMPERATURENOMINAL = 25
    BCOEFFICIENT = 3950

    def __init__(self, mode, die):
        """
        Initializes the FPGA script, sets up serial port, sets the target address, and creates folders for output files
            mode: "USB" or "FTDI"
            die: "A" or "Z"
        """

        self.controller = None
        self.files = None
        self.runningSum = {}

        self.user_inputs = self.get_user_input(mode, die)

        # The purpose of this method is to know when to cycle the power supply for PUF testing 
        # (by knowing the last SRAM address and triggering the power cycle when the last address is read)
        self.set_target_addrHex() 

        self.user_inputs['folder_name'] = self.create_folders()

        start_time = time.asctime(time.localtime(time.time()))
        print("Start Time:", start_time)
        self.files = self.create_new_files(1)

        self.setup_serial_port(mode)

    def setup_serial_port(self, mode):
        """ 
        This method sets up the serial port for communication with the FPGA
            mode: "USB" or "FTDI"
            sets self.controller
        """

        ports = serial.tools.list_ports.comports()

        # This method displays available serial ports and prompts the user to select one
        for i, port in enumerate(sorted(ports), start=1):
            print(f"{i}. {port}")
        port_num = int(input("Enter the number of the port you want to use: "))
        
        port = ports[port_num - 1].device

        if mode == "FTDI":
            self.controller = serial.Serial(port, 434800,8,"N",1) #about 15% slower than FPGA)
        else:
            self.controller = serial.Serial(port, 115200)
        
        self.controller.reset_input_buffer()

    def create_folders(self):
        """ 
        This method creates the folders for the output files
            returns: list of folder names
        """

        folder_name = []
        if self.user_inputs['t_seu']:
            folder_name.append(self.user_inputs['file_name'] + '_SEU')
        if self.user_inputs['t_sram']:
            folder_name.append(self.user_inputs['file_name'] + '_SRAM0')
            folder_name.append(self.user_inputs['file_name'] + '_SRAM1')
        if self.user_inputs['t_sense']:
            folder_name.append(self.user_inputs['file_name'] + '_SENSE')
        if self.user_inputs['t_ffmcu']:
            folder_name.append(self.user_inputs['file_name'] + '_FFMCU')
        for name in folder_name:
            if not os.path.exists(self.PATH + name):
                os.makedirs(self.PATH + name)
        return folder_name

    def set_target_addrHex(self):
        """ 
        Sets the target address for the end of SRAM based on the die type
        """
        # Athena:
            # SRAM0 = 13x64
            # SRAM1 = 11x128
        # Zeus:
            # SRAM0 = 9x40
            # SRAM1 = 10x128

        if self.user_inputs['t_die'] == 'A':
            self.target_addrHex = "{0:x}".format(int("7FF", 16))
        
        elif self.user_inputs['t_die'] == 'Z':
            self.target_addrHex = "{0:x}".format(int("3FF", 16))        
        
    def get_user_input(self, mode, die):
        """
        This method collects information to properly parse the data and name the files for the output data
            mode: "USB" or "FTDI"
            die: "C20", "C21", "A", or "Z"
            returns: dictionary of user inputs for naming the files and parsing the data
        """
        vdd = input("Enter vdd (ex. 750): ").strip()
        particle = input("Enter particle (ex. alpha): ").strip().upper()
        freq = input("Enter freq (ex. 2.5): ").strip()
        degrees = input("Enter temp (ex. RT or 80C): ").strip().upper()
        board_num = input("Enter board id: ").strip().upper()
        board_num = die + "-" + board_num
        t_die = die
        

        if mode == "FTDI":
        #     t_ffmcu = input("FFMCU? (y/n): ").strip().lower() == "y"
            t_ffmcu = True
        else:
            t_ffmcu = False  
            
        # t_seu = input("SEU? (y/n): ").strip().lower() == "y"
        # t_sram = input("SRAM? (y/n): ").strip().lower() == "y"
        # t_sense = input("Sensors? (y/n): ").strip().lower() == "y"
             
        t_seu = True
        t_sram = True
        t_sense = True

        filename = f"{vdd}_{particle}_{freq}_{degrees}_{board_num}"
        
        return {
            "vdd": vdd,
            "particle": particle,
            "freq": freq,
            "degrees": degrees,
            "board_num": board_num,
            "t_ffmcu": t_ffmcu,
            "t_die": t_die,
            "t_seu": t_seu,
            "t_sram": t_sram,
            "t_sense": t_sense,
            "file_name": filename
        }
    
    def create_new_files(self, file_num):
        """
        Creates the files for the output data -- SRAM, SEU, SENSE, FFMCU
            file_num: number to append to the end of the file name
        """

        files = {}

        if self.user_inputs['t_seu']:
            f_seu = self.user_inputs['file_name'] + "_SEU_" + str(file_num) + ".csv"
            fpath_seu = self.PATH + self.user_inputs['folder_name'][0] + "/" + f_seu
            files['SEU'] = open(fpath_seu, "w+")
            files['SEU'].write("Time,SR,Error Count\n")

        if self.user_inputs['t_sram']:

            f_sram0 = self.user_inputs['file_name'] + "_SRAM0_" + str(file_num) + ".csv"
            fpath_sram0 = self.PATH + self.user_inputs['folder_name'][1] + "/" + f_sram0
            files['SRAM0'] = open(fpath_sram0, "w+")
            files['SRAM0'].write("Time,Address,Error Pattern\n")

            f_sram1 = self.user_inputs['file_name'] + "_SRAM1_" + str(file_num) + ".csv"
            fpath_sram1 = self.PATH + self.user_inputs['folder_name'][2] + "/" + f_sram1
            files['SRAM1'] = open(fpath_sram1, "w+")
            files['SRAM1'].write("Time,Address,Error Pattern\n")
            
        if self.user_inputs['t_sense']:
            f_sense = self.user_inputs['file_name'] + "_SENSE_" + str(file_num) + ".csv"
            fpath_sense = self.PATH + self.user_inputs['folder_name'][3] + "/" + f_sense

            files['SENSE'] = open(fpath_sense, "w+")
            files['SENSE'].write("Time,Data Stream ID,Data\n")

        if self.user_inputs['t_ffmcu']:
            f_ffmcu = self.user_inputs['file_name'] + "_FFMCU_" + str(file_num) + ".csv"
            fpath_ffmcu = self.PATH + self.user_inputs['folder_name'][4] + "/" + f_ffmcu
            
            files['FFMCU'] = open(fpath_ffmcu, "w+")
            files['FFMCU'].write("Time,SR,Error Count\n")

        return files

    def process_data_N3(self, data, type, output, die, flag):
        """
        * FOR N3 ONLY *
        This method processes the data stream coming from the FPGA and writes the data to the appropriate file
            data: data packet from FPGA
            type: data stream tag
            output: file to write data to
            die: "A" or "Z"
            flag: used to know when to cycle the power supply for PUF testing
        """
        
        now = datetime.now()
        current_time = now.strftime("%m/%d/%Y %H:%M:%S")
        
        if (type == self.N3_SRAM_TAG_0):
            
            #Athena 13 bit addr + 64 bit word 
            if(die == 'A'):
                # isolate 13 bit addr
                addr = data[8:11]
                # isolate 64 bit data
                datablock = data[11:20]
                output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
                print("%s-%s" % (addr.hex(), datablock.hex()))
            
            #Zeus
            elif (die == 'Z'):
                # isolate 9 bit addr
                addr = data[13:14]
                # isolate 40 bit data
                datablock = data[14:20]
                output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
                print("%s-%s" % (addr.hex(), datablock.hex()))
            
            else:
                raise Exception("Error: Invalid die specified for N3 node")
                    
        elif (type == self.N3_SRAM_TAG_1):
            
            #Athena 11 bit addr + 128 bit word
            if die == 'A':
                # isolate 11 bit addr
                addr = data[0:3]
                # isolate 128 bit data
                datablock = data[3:20]
                output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
                print("%s-%s" % (addr.hex(), datablock.hex()))
            
            #Zeus
            elif (die == 'Z'):
                # isolate 10 bit addr
                addr = data[0:3]
                # isolate 128 bit data
                datablock = data[3:20]
                output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
                print("%s-%s" % (addr.hex(), datablock.hex()))
            
            else:
                raise Exception("Error: Invalid die specified for N3 node")
                        
            # Check if the target address has been reached 
            addr = int.from_bytes(addr, "big")
            addrHex = "{0:x}".format(addr)
            
            if addrHex == self.target_addrHex:
                print("Target address reached, raising flag")
                if flag:
                    flag.send(1)

        elif (type == self.N3_SR_TAG):
            data = int.from_bytes(data, "big")
            dataPacket = (data << 133) >> 133
            idx = dataPacket >> 12
            count = dataPacket & 0b111111111111

            #TODO: Figure out what this running sum thing does
            if idx in self.runningSum:
                self.runningSum[idx] += count
            else:
                self.runningSum[idx] = count
            output.write("%s,%s,%s\n"%(current_time,str(idx),str(count)))
            print(str(idx) + "-" + str(count) + " (" + str(self.runningSum[idx]) + ") ")

        elif (type == self.N3_FFMCU_TAG):
            ### when using MCU codes
            data = int.from_bytes(data,"big")
            idx = data >> 64
            idx &= 0b1111111111111111111111111
            count = data & 0b111111111111111111111111111111111111111111111111111111111111111
            value = bin(count)[2:].zfill(60) #strip off the leading "0b" and pad with leading 0's
            output.write("%s,%s,%s\n"%(current_time,str(idx),str(value)))
            print(str(idx) + "\t" + str(value))
        
        elif (type == self.N3_I2C1):
            # Obtain 16 bit reading from ADC.
            data = int.from_bytes(data,"big")
            code = data & 0x0000FFFF
            voltage = self.N3_INTERNAL_VOLT_REF * (code / 2**(15))

            # Equation is according to Texas Instruments' ADS1119 Datasheet thermistor resistance measurement.
            # Is described on page 35. Calculate resistance according to ADC code using nominal resistance of 1250 ohms.
            # Multiply by 2 to account for voltage dividers.
            R = 2 * self.N3_THERMISTORBASELINE * (code / 2**15) / (1 - (code / 2**15))

            # For testing purposes. Used to observe variable resistance at temperature.
            # print("Resistor Value: ", R)
            # print("Code: ", voltage)

            # Use Steinhart-Hart's Beta parameter equation to compute the reciprocal of temperature in Kelvin.
            # Equation is described at the following: https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation
            temp_nominal_kelvin = self.TEMPERATURENOMINAL + 273.15
            reciprocal_temp_nominal = 1.0/temp_nominal_kelvin
            reciprocal_beta = 1.0/self.BCOEFFICIENT
            log_difference_R = math.log(R/self.N3_THERMISTORNOMINAL)
            reciprocal_temperature = (reciprocal_beta * log_difference_R + reciprocal_temp_nominal)
            degrees_C = (1.0/reciprocal_temperature) - 273.15

            # I2C1 data stream 1
            print ("I2C_1 Data Temperature 1 = ", degrees_C)
            output.write("%s,%s,%s\n"%(current_time, "I2C_1", degrees_C))

            # Capture upper half and shift right by 16 to obtain reading from ADC.
            code = data & 0xFFFF0000
            code = code >> 16

            # For testing purposes. Used to observe voltage.
            voltage = self.N3_INTERNAL_VOLT_REF * (code / 2**(15))

            # Equation is according to Texas Instruments' ADS1119 Datasheet thermistor resistance measurement.
            # Is described on page 35. Calculate resistance according to ADC code using nominal resistance of 1250 ohms.
            # Multiply by 2 to account for voltage dividers.
            R = 2 * self.N3_THERMISTORBASELINE * (code / 2**15) / (1 - (code / 2**15))

            # For testing purposes. Used to observe variable resistance at temperature.
            # print("Resistor Value: ", R)
            # print("Code: ", voltage)

            # Use Steinhart-Hart's Beta parameter equation to compute the reciprocal of temperature in Kelvin.
            # Equation is described at the following: https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation
            temp_nominal_kelvin = self.TEMPERATURENOMINAL + 273.15
            reciprocal_temp_nominal = 1.0/temp_nominal_kelvin
            reciprocal_beta = 1.0/self.BCOEFFICIENT
            log_difference_R = math.log(R/self.N3_THERMISTORNOMINAL)
            reciprocal_temperature = (reciprocal_beta * log_difference_R + reciprocal_temp_nominal)
            degrees_C = (1.0/reciprocal_temperature) - 273.15

            print ("I2C_1 Data Temperature 2 = ", degrees_C)
            output.write("%s,%s,%s\n"%(current_time, "I2C_1", degrees_C))

        elif (type == self.N3_I2C2):
            # Obtain 32 bit code.
            idx = int.from_bytes(data,"big")
            idx &= 0xFFFFFFFF

            # Print 32 bits to observe number. Not necessary. For testing purposes.
            #print("32 bit number: ", idx)

            # Obtain 16 bit reading from ADC.
            data = idx & 0x0000FFFF

            # Initialize voltages to zero.
            io_voltage = 0
            core_voltage = 0

            # Display ADC code. Not necessary. For testing purposes.
            # print("A4 Value: ", data)

            # Equation is according to Texas Instruments' ADS1119 Datasheet voltage measurement.
            # Is described on page 35. Calculate voltage according to ADC code with internal
            # reference voltage of 2.048. Multiply by 2 to account for voltage dividers.
            io_voltage = self.N3_INTERNAL_VOLT_REF * (data / 2**(15)) * 2

            # Print IO Voltage to display. Record.
            print ("I2C_2 Data Stream Voltage_IO = ", io_voltage)
            output.write("%s,%s,%s\n"%(current_time, "I2C_2", io_voltage))

            # Capture upper half and shift right by 16 to obtain reading from ADC.
            data = idx & 0xFFFF0000
            data = data >> 16

            # Display ADC code. Not necessary. For testing purposes.
            # print("A3 Value: ", data)

            # Equation is according to Texas Instruments' ADS1119 Datasheet voltage measurement.
            # Is described on page 35. Calculate voltage according to ADC code with internal
            # reference voltage of 2.048. Multiply by 2 to account for voltage dividers.
            core_voltage = self.N3_INTERNAL_VOLT_REF * (data / 2**(15)) * 2

            # Print Core Voltage to display. Record.
            print ("I2C_2 Data Stream Voltage_Core = ", core_voltage)
            output.write("%s,%s,%s\n"%(current_time, "I2C_2", core_voltage))
        
        else: # Unexpected tag
            print("Error: Unexpected data type")
            pass # Print error message in preprocess_N3 method


    def handle_data_stream(self, flag):
        """
        * FOR N3 ONLY *
        This method aligns the data coming from the FPGA and processes the data stream.

            flag: used to know when to cycle the power supply for PUF testing
        """

        while self.controller.in_waiting < 48:
            pass

        # Align packets read off serial bus 
        # Read more than of expected packet size (22*2 + 4)
        data = self.controller.read(48)
        
        # Find location of /n/r in packet (always ends in this)
        start = data.find(b'\r')
        stop = data.find(b'\r',start+1,len(data))
        
        # Complete the next packet by reading partial packet off buffer
        complete = data[start+1:stop+1]
        partial = data[stop+1:len(data)]
        need = 22 -(len(data)-stop-1)
        moredata = self.controller.read(need)
        nextData = partial + moredata

        # Process both packets
        self.preprocess_N3(complete, flag)
        self.preprocess_N3(nextData, flag)

        print(complete)
        print(nextData)

        # All subsequent reads are done with expected packet size (22)
        try:
            while True:
                while self.controller.in_waiting < 22 :
                    pass
                data = self.controller.read(22)
                self.preprocess_N3(data, flag)

        except KeyboardInterrupt:
            # realign data stream
            pass

        # Terminate all files
        for f in self.files.values():
            f.close()
        sys.exit()
    
    def preprocess_N3(self, data, flag):
        """
        * FOR N3 ONLY *
        This method determines the tag from the data stream and calls the appropriate method to process the data
            data: data packet from FPGA
        """
        dataTag = data[0]
        dataOnly = data[1:20]

        # Read SR Error Data
        if (dataTag == self.N3_SR_TAG) and self.user_inputs['t_seu']:
            self.process_data_N3(dataOnly, self.N3_SR_TAG, self.files['SEU'], self.user_inputs['t_die'], flag)
        
        # Read SRAM0 Data
        elif (dataTag == self.N3_SRAM_TAG_0) and self.user_inputs['t_sram']:
            self.process_data_N3(dataOnly, self.N3_SRAM_TAG_0, self.files['SRAM0'], self.user_inputs['t_die'], flag)
        
        # Read SRAM1 Data
        elif (dataTag == self.N3_SRAM_TAG_1) and self.user_inputs['t_sram']:
            self.process_data_N3(dataOnly, self.N3_SRAM_TAG_1, self.files['SRAM1'], self.user_inputs['t_die'], flag)
        
        # Read FFMCU Data
        elif (dataTag == self.N3_FFMCU_TAG) and self.user_inputs['t_ffmcu']:
            self.process_data_N3(dataOnly, self.N3_FFMCU_TAG, self.files['FFMCU'], self.user_inputs['t_die'], flag)
        
        # Read I2C1 Data
        elif (dataTag == self.N3_I2C1) and self.user_inputs['t_sense']:
            self.process_data_N3(dataOnly, self.N3_I2C1, self.files['SENSE'], self.user_inputs['t_die'], flag)
        
        # Read I2C2 Data
        elif (dataTag == self.N3_I2C2) and self.user_inputs['t_sense']:
            self.process_data_N3(dataOnly, self.N3_I2C2, self.files['SENSE'], self.user_inputs['t_die'], flag)
        
        # Unexpected data
        else:
            print("Invalid input... Unexpected tag: ", dataTag)
            print(dataOnly)
            
if __name__ == "__main__":
    print("\nWELCOME TO THE FPGA SCRIPT!\n")
    
    die = "A"

    #ftdi_en = input("Connecting to FPGA via USB or FTDI?").upper in ["FTDI"]
    ftdi_en = True
    #ffmcu_en = input("Collecting raw FF data?").upper() in ['Y', 'YES']
    ffmcu_en = True

    script = FPGAScript(ftdi_en, ffmcu_en, die=die)
    
    if die in ['A', 'Z']:    
        script.handle_data_stream(flag=None)
    else:
        raise Exception("Invalid die specified")


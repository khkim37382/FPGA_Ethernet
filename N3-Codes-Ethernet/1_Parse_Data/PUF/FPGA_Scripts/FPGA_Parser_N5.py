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

    # N5 Params
    N5_SR_NUM = 29
    N5_SR_VALID_NUM = 29
    N5_THRESHOLD = 4
    N5_LOOPLIMIT = 64800

    # Data stream tags for N5
    N5_FFMCU_TAG = int('011',2)
    N5_SRAM_TAG = int('111', 2)
    N5_SR_TAG = int('001', 2)
    N5_I2C1 = int('100', 2)
    N5_I2C2 = int('010', 2)

    # ADC Params
    N5_SERIESRESISTOR = 150000
    N5_THERMISTORNOMINAL = 1000    
    N5_CURRCONSTANT = 0.0015

    TEMPERATURENOMINAL = 25
    BCOEFFICIENT = 3950

    def __init__(self, ftdi_en, ffmcu_en, die):
        """
        Initializes the FPGA script, sets up serial port, sets the target address, and creates folders for output files
            ftdi_en: boolean representing "USB" or "FTDI"
            ffmcu_en: boolean representing whether to collect raw FF data
            die: "C20", "C21"
        """

        self.controller = None
        self.files = None
        self.runningSum = {}

        self.user_inputs = self.get_user_input(("FFMCU" if ffmcu_en else None), die)

        # The purpose of this method is to know when to cycle the power supply for PUF testing 
        # (by knowing the last SRAM address and triggering the power cycle when the last address is read)
        self.set_target_addrHex() 

        self.user_inputs['folder_name'] = self.create_folders()

        start_time = time.asctime(time.localtime(time.time()))
        print("Start Time:", start_time)
        self.files = self.create_new_files(1)

        self.setup_serial_port("FTDI" if ftdi_en else "USB")

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
            if self.user_inputs['t_die'] in ['A', 'Z']:
                folder_name.append(self.user_inputs['file_name'] + '_SRAM0')
                folder_name.append(self.user_inputs['file_name'] + '_SRAM1')
            else:    
                folder_name.append(self.user_inputs['file_name'] + '_SRAM')
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

        # C20 SRAM = 13x32? (i think)
        # C21 SRAM = 10x76? (i think)

        if self.user_inputs['t_die'] == 'C20':
            self.target_addrHex = "{0:x}".format(int("1FFF", 16))
        
        elif self.user_inputs['t_die'] == 'C21':
            self.target_addrHex = "{0:x}".format(int("3FF", 16))

    def get_user_input(self, mode, die):
        """
        This method collects information to properly parse the data and name the files for the output data
            mode: "FFMCU" or None
            die: "C20", "C21"
            returns: dictionary of user inputs for naming the files and parsing the data
        """
        vdd = input("Enter vdd (ex. 750): ").strip()
        particle = input("Enter particle (ex. alpha): ").strip().upper()
        freq = input("Enter freq (ex. 2.5): ").strip()
        degrees = input("Enter temp (ex. RT or 80C): ").strip().upper()
        board_num = input("Enter board id: ").strip().upper()
        board_num = die + "-" + board_num
        t_die = die
        
        if mode == "FFMCU":
        #     t_ffmcu = input("FFMCU? (y/n): ").strip().lower() == "y"
            t_ffmcu = True
        else:
            t_ffmcu = False
                
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
            f_sram = self.user_inputs['file_name'] + "_SRAM_" + str(file_num) + ".csv"
            fpath_sram = self.PATH + self.user_inputs['folder_name'][1] + "/" + f_sram

            files['SRAM'] = open(fpath_sram, "w+")
            files['SRAM'].write("Time,Address,Error Pattern\n")

        if self.user_inputs['t_sense']:
            f_sense = self.user_inputs['file_name'] + "_SENSE_" + str(file_num) + ".csv"
            fpath_sense = self.PATH + self.user_inputs['folder_name'][2] + "/" + f_sense

            files['SENSE'] = open(fpath_sense, "w+")
            files['SENSE'].write("Time,Data Stream ID,Data\n")

        if self.user_inputs['t_ffmcu']:
            f_ffmcu = self.user_inputs['file_name'] + "_FFMCU_" + str(file_num) + ".csv"
            fpath_ffmcu = self.PATH + self.user_inputs['folder_name'][3] + "/" + f_ffmcu

            files['FFMCU'] = open(fpath_ffmcu, "w+")
            files['FFMCU'].write("Time,SR,Error Count\n")

        return files


    def process_data_N5(self, data, type, output, die, flag):
        """
        This method processes the data stream coming from the FPGA and writes the data to the appropriate file
            data: data packet from FPGA
            type: data stream tag
            output: file to write data to
            die: "C20" or "C21"
            flag: used to know when to cycle the power supply for PUF testing
        """
        now = datetime.now()
        current_time = now.strftime("%m/%d/%Y %H:%M:%S")
        # remove newline and carriage 
        data = int.from_bytes(data[-11:],'big')
        dataBytes = data.to_bytes(11, 'big')
        data = int.from_bytes(dataBytes, 'big')

        if type == self.N5_SRAM_TAG: 
            if die == 'C20': # C20
                datablock = data & (0xFFFFFFFF)
                addr = data >> 32
                addr &= 0b1111111111111
            elif die == 'C21': # C21
                datablock = data & (0xFFFFFFFFFFFFFFFFFFF)
                addr = data >> 76
                addr &= 0b1111111111
            else:
                raise Exception("Error: Invalid die specified for N5 node")
            
            addrHex = "{0:x}".format(addr)
            dataHex = "{0:x}".format(datablock)
            output.write("%s,%s,%s\n"%(current_time, addrHex, dataHex))
            print("%s-%s" % (addrHex, dataHex))

            # Check if the target address has been reached 
            if addrHex == self.target_addrHex:
                print("Target address reached, raising flag")
                if flag:
                    flag.send(1)
                
        elif type == self.N5_SR_TAG:
            idx = data >> 12
            idx &= 127
            count = data & 0b111111111111
            output.write("%s,%s,%s\n"%(current_time, str(idx), str(count)))
            print(str(idx) + "-" + str(count))

        elif type == self.N5_I2C1:
            print("I2C_1 Data Stream = ", data)
            output.write("%s,%s,%s\n"%(current_time, "I2C_1", data))

        elif type == self.N5_I2C2: 
            print("I2C_2 Data Stream = ", data)
            output.write("%s,%s,%s\n"%(current_time, "I2C_2", data))

        elif type == self.N5_FFMCU_TAG:
            ### when using MCU codes
            idx = data >> 32
            idx &= 0xFFFFFFFF
            count = data & 0xFFFFFFFF
            value = bin(count)[2:].zfill(30) #strip off the leading "0b" and pad with leading 0's
            output.write("%s,%s,%s\n"%(current_time,str(idx),str(value)))
            print(str(idx) + "\t" + str(value))

        else:
            print("Error: Unexpected data type")


    def handle_data_stream(self, flag):
        """
        * FOR N5 ONLY *
        This method reads data coming from the FPGA and calls the appropriate method to process the data.
            flag: used to know when to cycle the power supply for PUF testing
        """
        loopCounter = 0
        try:
            while True:
                while self.controller.in_waiting < 14:
                    pass
                data = self.controller.read(14)
                data = data[:12]
                dataTogether = data
                data = int.from_bytes(data, 'big')
                dataTag = data >> 93
                if (dataTag == self.N5_SRAM_TAG) and self.user_inputs['t_sram']:
                    self.process_data_N5(dataTogether, self.N5_SRAM_TAG, self.files['SRAM'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.N5_SR_TAG) and self.user_inputs['t_seu']:
                    self.process_data_N5(dataTogether, self.N5_SR_TAG, self.files['SEU'], self.user_inputs['t_die'], flag)
                    loopCounter += 1
                    if loopCounter > self.N5_LOOPLIMIT:
                        fileNum += 1
                        loopCounter = 0
                        self.files = self.create_new_files(fileNum)
                elif (dataTag == self.N5_I2C1) and self.user_inputs['t_sense']:
                    self.process_data_N5(dataTogether, self.N5_I2C1, self.files['SENSE'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.N5_I2C2) and self.user_inputs['t_sense']:
                    self.process_data_N5(dataTogether, self.N5_I2C2, self.files['SENSE'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.N5_FFMCU_TAG) and self.user_inputs['t_ffmcu']:
                    self.process_data_N5(dataTogether, self.N5_FFMCU_TAG, self.files['FFMCU'], self.user_inputs['t_die'], flag)
                else:
                    print("Invalid input... Unexpected tag: ", dataTag)
        except KeyboardInterrupt:
            pass

        # Terminate all files
        for f in self.files.values():
            f.close()
        sys.exit()
    
if __name__ == "__main__":
    print("\nWELCOME TO THE FPGA SCRIPT!\n")
    
    die = "C21"

    ftdi_en = input("Connecting to FPGA via USB or FTDI?").upper in ["FTDI"]
    ffmcu_en = input("Collecting raw FF data?").upper() in ['Y', 'YES']

    script = FPGAScript(ftdi_en, ffmcu_en, die=die)
    
    if die in ['C20', 'C21']:
        script.handle_data_stream(flag=None)
    else:
        raise Exception("Invalid die specified")


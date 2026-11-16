from datetime import datetime
import serial.tools.list_ports
import time
import serial
import sys
import os


class FPGAScript:
    # Class attributes (constants)
    PATH = "./"
    SR_NUM = 29
    SR_VALID_NUM = 29
    THRESHOLD = 4
    LOOPLIMIT = 64800
    FFMCU_TAG = int('011',2) # FFMCU Tag
    SRAM_TAG = int('111', 2)
    SR_TAG = int('001', 2)
    I2C1 = int('100', 2)
    I2C2 = int('010', 2)
    SERIESRESISTOR = 150000
    THERMISTORNOMINAL = 1000
    TEMPERATURENOMINAL = 25
    BCOEFFICIENT = 3950
    CURRCONSTANT = 0.0015
    
    def __init__(self):
        self.controller = None
        self.files = None
        self.user_inputs = None
        self.target_addrHex = None

    def set_target_addrHex(self, val):
        # convert val to hex
        self.target_addrHex = "{0:x}".format(int(val, 16))

    def processData(self, data, type, output, die, flag):

        now = datetime.now()
        current_time = now.strftime("%m/%d/%Y %H:%M:%S")
        # remove newline and carriage 
        data = int.from_bytes(data[-11:],'big')
        dataBytes = data.to_bytes(11, 'big')
        data = int.from_bytes(dataBytes, 'big')

        if type == self.SRAM_TAG: 
            
            #print("SRAM Data: {0:x}".format(data))


            if die: # C20
                datablock = data & (0xFFFFFFFF)
                addr = data >> 32
                addr &= 0b1111111111111
            else: # C21
                datablock = data & (0xFFFFFFFFFFFFFFFFFFF)
                addr = data >> 76
                addr &= 0b1111111111
            
            addrHex = "{0:x}".format(addr)
            dataHex = "{0:x}".format(datablock)
            output.write("%s,%s,%s\n"%(current_time, addrHex, dataHex))
            print("%s-%s" % (addrHex, dataHex))

            # Check if the target address has been reached 
            if addrHex == self.target_addrHex:
                print("Target address reached, raising flag")
                if flag:
                    flag.send(1)
                
        elif type == self.SR_TAG:
            idx = data >> 12
            idx &= 127
            count = data & 0b111111111111
            output.write("%s,%s,%s\n"%(current_time, str(idx), str(count)))
            print(str(idx) + "-" + str(count))

        elif type == self.I2C1:
            print("I2C_1 Data Stream = ", data)
            output.write("%s,%s,%s\n"%(current_time, "I2C_1", data))

        elif type == self.I2C2: 
            print("I2C_2 Data Stream = ", data)
            output.write("%s,%s,%s\n"%(current_time, "I2C_2", data))

        elif type == self.FFMCU_TAG:
            ### when using MCU codes
            idx = data >> 64
            idx &= 0b1111111111111111111111111
            count = data & 0b111111111111111111111111111111111111111111111111111111111111111
            value = bin(count)[2:].zfill(60) #strip off the leading "0b" and pad with leading 0's
            output.write("%s,%s,%s\n"%(current_time,str(idx),str(value)))
            print(str(idx) + "\t" + str(value))

            # if die:
            #     datablock = data & (0xFFFFFFFF)
            #     addr = data >> 32
            #     addr &= 0b1111111111111
            # else:
            #     datablock = data & (0xFFFFFFFFFFFFFFFFFFF)
            #     addr = data >> 76
            #     addr &= 0b1111111111
            # addrHex = "{0:x}".format(addr)
            # dataHex = "{0:x}".format(datablock)
            # output.write("%s,%s,%s\n"%(current_time, addrHex, dataHex))
            # print("%s-%s" % (addrHex, dataHex))

        else:
            print("Error: Unexpected data type")

    def get_user_input(self, mode, die):
        vdd = input("Enter vdd (ex. 750): ").strip()
        particle = input("Enter particle (ex. alpha): ").strip().upper()
        freq = input("Enter freq (ex. 2.5): ").strip()
        degrees = input("Enter temp (ex. RT or 80C): ").strip().upper()
        board_num = input("Enter board number (ex. 31): ").strip().upper()
        board_num = die + "-" + board_num
        t_die = die == 'C20'
        
        if mode == "FTDI":
            t_ffmcu = input("FFMCU? (y/n): ").strip().lower() == "y"
        else:
            t_ffmcu = False
            
        t_seu = input("SEU? (y/n): ").strip().lower() == "y"
        t_sram = input("SRAM? (y/n): ").strip().lower() == "y"
        t_sense = input("Sensors? (y/n): ").strip().lower() == "y"
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

    def setup_serial_port(self, ports):
        # This method displays available serial ports and prompts the user to select one
        for i, port in enumerate(sorted(ports), start=1):
            print(f"{i}. {port}")
        port_num = int(input("Enter the number of the port you want to use: "))
        return str(ports[port_num - 1].device)
    
    def handle_data_stream(self, flag):
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
                if (dataTag == self.SRAM_TAG) and self.user_inputs['t_sram']:
                    self.processData(dataTogether, self.SRAM_TAG, self.files['SRAM'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.SR_TAG) and self.user_inputs['t_seu']:
                    self.processData(dataTogether, self.SR_TAG, self.files['SEU'], self.user_inputs['t_die'], flag)
                    loopCounter += 1
                    if loopCounter > self.LOOPLIMIT:
                        fileNum += 1
                        loopCounter = 0
                        self.files = self.create_new_files(fileNum)
                elif (dataTag == self.I2C1) and self.user_inputs['t_sense']:
                    self.processData(dataTogether, self.I2C1, self.files['SENSE'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.I2C2) and self.user_inputs['t_sense']:
                    self.processData(dataTogether, self.I2C2, self.files['SENSE'], self.user_inputs['t_die'], flag)
                elif (dataTag == self.FFMCU_TAG) and self.user_inputs['t_ffmcu']:
                    self.processData(dataTogether, self.FFMCU_TAG, self.files['FFMCU'], self.user_inputs['t_die'], flag)
                else:
                    print("Invalid input... Unexpected tag: ", dataTag)
        except KeyboardInterrupt:
            pass

    def create_folders(self):
        folder_name = []
        if self.user_inputs['t_seu']:
            folder_name.append(self.user_inputs['file_name'] + '_SEU')
        if self.user_inputs['t_sram']:
            folder_name.append(self.user_inputs['file_name'] + '_SRAM')
        if self.user_inputs['t_sense']:
            folder_name.append(self.user_inputs['file_name'] + '_SENSE')
        if self.user_inputs['t_ffmcu']:
            folder_name.append(self.user_inputs['file_name'] + '_FFMCU')
        for name in folder_name:
            if not os.path.exists(self.PATH + name):
                os.makedirs(self.PATH + name)
        return folder_name

    def create_new_files(self, file_num):
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

    def initialize(self, mode, die):
        print("\nWELCOME TO THE FPGA SCRIPT!\n")
        self.user_inputs = self.get_user_input(mode, die)
        ports = serial.tools.list_ports.comports()
        port = self.setup_serial_port(ports)
        self.user_inputs['folder_name'] = self.create_folders()
        file_num = 1
        start_time = time.asctime(time.localtime(time.time()))
        print("Start Time:", start_time)
        self.files = self.create_new_files(file_num)
        # self.controller = serial.Serial(port, 115200)
        if mode == "FTDI":
            self.controller = serial.Serial(port, 434000,8,"N",1) #about 15% slower than FPGA)
        else:
            self.controller = serial.Serial(port, 115200)
        self.controller.reset_input_buffer()
    
    def run(self, flag=None):
        self.handle_data_stream(flag)
        for f in self.files.values():
            f.close()
        sys.exit()

if __name__ == "__main__":
    script = FPGAScript()
    script.set_target_addrHex("1FFF")  # Set the target addrHex value
    script.initialize(mode="USB", die="C20")
    script.run()
    
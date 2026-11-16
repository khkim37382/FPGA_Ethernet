# Author: Yoni Xiong 
# Last Changed: 7-7-20
# Purpose: This file parses the serial data from the FPGA and organizes them in three files. 

#SRs    -> 001 + '0'*76 + 7 bits SR num + 12 bits err count
#I2C1   -> 100 + '0'*61 + 16 bits data + 16 bits data
#I2C2   -> 010 + '0'*61 + 16 bits data + 16 bits data
#SRAM1  -> 111 + '0'*48 + 13 bits addr + 32 bits data
#SRAM2  -> 111 + '0'*7  + 10 bits addr + 76 bits data

import time
import serial 
from datetime import datetime
import sys
import os

###############################################################

# user specified path for folder
PATH = "C:/Users/rer.user/Desktop/PUF/tests"

LOOPLIMIT = 64800 # number of cycles until make new file (64800 = 6 hours)

SR_NUM = 29 # Number of shift registers
SR_VALID_NUM = 29 # Number of valid registers
THRESHOLD = 4 # Number of SRs that can have errors at same cycle without being suspicious 

SRAM_TAG = int('111', 2) # SRAM Tag
SR_TAG = int('001', 2) # SR Tag 
I2C1 = int('100', 2) # I2C data stream 1
I2C2 = int('010', 2) # I2C data stream 2

#  the value of the 'other' resistor
SERIESRESISTOR = 150000
# resistance at 25 degrees C
THERMISTORNOMINAL = 1000
# temp. for nominal resistance (almost always 25 C)
TEMPERATURENOMINAL = 25
# The beta coefficient of the thermistor (usually 3000-4000)
BCOEFFICIENT = 3950
# current constant
CURRCONSTANT = 0.0015

###############################################################
def createNewFiles(type, file, fileNum):
    if type == "SEU":
        return file + "_SEU_" + str(fileNum)+ ".csv"

    if type == "SRAM":
        return file + "_SRAM_"+ str(fileNum)+ ".csv"

    if type == "SENSE":
        return file + "_Sense_" + str(fileNum)+ ".csv"

def processData(data, type, output, die): 
    now = datetime.now()
    current_time = now.strftime("%m/%d/%Y %H:%M:%S")
    # remove newline and carriage 
    data = int.from_bytes(data[-11:],'big') # >> 16 # removes tag and \n\r
    dataBytes = data.to_bytes(11, 'big')    # to bytes
    data = int.from_bytes(dataBytes, 'big') # back to int
    if (type == SRAM_TAG): 
        #C20: 13 bits addr, 32 bits data
        if(die):    
            # remove tag and align to right 
            datablock = data
            datablock &= (0xFFFFFFFF)
            # isolate addr 
            addr = data >> 32
            addr &= 0b1111111111111
            # isolate 32 bit data  
            addrHex = "{0:x}".format(addr)
            dataHex = "{0:x}".format(datablock)
            output.write("%s,%s,%s\n"%(current_time,addrHex, dataHex))
            print("%s-%s" % (addrHex, dataHex))
        #C21: 10 bits addr, 76 bits data
        else: 
            # remove tag and align to right 
            datablock = data
            datablock &= (0xFFFFFFFFFFFFFFFFFFF)
            # isolate addr 
            addr = data >> 76
            addr &= (0b1111111111)
            # isolate 72 bit data  
            addrHex = "{0:x}".format(addr)
            dataHex = "{0:x}".format(datablock)
            output.write("%s,%s,%s\n"%(current_time,addrHex, dataHex))
            print("%s-%s" % (addrHex, dataHex))
    elif (type == SR_TAG):
        idx = data
        idx = idx >> 12
        idx &= 127
        count = data
        count = data & 0b111111111111
        output.write("%s,%s,%s\n"%(current_time,str(idx),str(count)))
        print(str(idx) + "-" + str(count))
    elif (type == I2C1):
        # I2C1 data stream 1
        print ("I2C_1 Data Stream = ", data)
        output.write("%s,%s,%s\n"%(current_time, "I2C_1", data))

    elif (type == I2C2): 
        # I2C1 data stream 2
        print ("I2C_2 Data Stream = ", data)
        output.write("%s,%s,%s\n"%(current_time, "I2C_2", data))

    else:
        pass # Print error message in main loop

###############################################################

print("\nWELCOME TO THE FPGA SCRIPT!\n")

# obtain file names for everything that that directory
names = os.listdir(PATH)

N5 = "N5"
vdd = str(input("Enter vdd (ex. 750): ")).strip()
particle = str(input("Enter particle (ex. alpha): ")).strip().upper()
freq = str(input("Enter freq (ex. 2.5): ")).strip()
degrees = str(input("Enter temp (ex. RT or 80C): ")).strip().upper()
boardNum = str(input("Enter board nume (die - num) (ex. C20-31): ")).strip().upper()
print()
dienum = str(input("C20 or C21? (ex. 20 or 21): ")).strip()

# Get name of testing file
fileName = "%s_%s_%s_%s_%s_%s" % (N5, vdd, particle, freq, degrees, boardNum)

# questions for user
print()
tDie = dienum =='20'
tSEU = str(input("SEU? (y/n): ")).strip() == "y"
tSRAM = str(input("SRAM? (y/n): ")).strip() == "y"
tSense = str(input("Sensors? (y/n): ")).strip() == "y"

# create necessary folders if they do not exist yet
if tSEU and tSRAM and not tSense: 
    folder_name = [fileName + '_SEU', fileName + '_SRAM']
else: 
    folder_name = [fileName + '_SEU', fileName + '_SRAM', fileName + '_SENSE']
for name in folder_name:
    if not os.path.exists(PATH+name):
        os.makedirs(PATH+name)

# Get com port 
port = str(input("Enter COM Port (ex. COM3): ")).strip().upper()

fileNum = 1
localtime = time.asctime(time.localtime(time.time()))
print ("Start Time:", localtime)
if tSEU:
    fSEU = createNewFiles("SEU", PATH + folder_name[0] +"/"+ fileName, fileNum)
    oSEU = open(fSEU, "w+")
    oSEU.write("Time (Day/Month/Year Hour:Minute:Second),SR,Error Count\n")
if tSRAM:
    fSRAM = createNewFiles("SRAM", PATH + folder_name[1] +"/"+ fileName, fileNum)
    oSRAM = open(fSRAM, "w+")
    oSRAM.write("Time (Day/Month/Year Hour:Minute:Second),Address,Error Pattern\n")
if tSense:
    fSense = createNewFiles("SENSE", PATH + folder_name[2] +"/"+ fileName, fileNum)
    oSense = open(fSense, "w+")
    oSense.write("Time (Day/Month/Year Hour:Minute:Second),Data Stream ID,Data\n")

###############################################################
controller = serial.Serial(port, 115200)
controller.reset_input_buffer()
loopCounter = 0
try: 
    while True: 
        while controller.in_waiting < 14 : 
            pass
        data = controller.read(14)
        data = data[:12]
        dataTogether = data
        data = int.from_bytes(data, 'big')
        dataTag = data >> 93
        if (dataTag == SRAM_TAG) and tSRAM: 
            processData(dataTogether, SRAM_TAG, oSRAM, tDie)
        elif (dataTag == SR_TAG) and tSEU: 
            processData(dataTogether, SR_TAG, oSEU, tDie)
            loopCounter += 1 # increment
            if loopCounter > LOOPLIMIT:
                fileNum += 1 # increment
                loopCounter = 0 # reset
                if tSEU:         
                    newFile = createNewFiles("SEU", PATH + folder_name[0] + "/" + fileName, fileNum)
                    oSEU = open(newFile, "w+")
                if tSRAM: 
                    newFile = createNewFiles("SRAM", PATH + folder_name[1] + "/" + fileName, fileNum)
                    oSRAM = open(newFile, "w+")
                if tSense: 
                    newFile = createNewFiles("SENSE", PATH + folder_name[2] + "/" + fileName, fileNum)
                    oSense = open(newFile, "w+")
        elif (dataTag == I2C1) and tSense: 
            processData(dataTogether, I2C1, oSense, tDie)
        elif (dataTag == I2C2) and tSense:
            processData(dataTogether, I2C2, oSense, tDie)
        else:
            # TODO: Need to add log file to show when "Invalid Input" occurs with error in data tag
            print("Invalid input... Unexpected tag: ", dataTag)
except KeyboardInterrupt: 
    pass
if tSEU:         
    oSEU.close()
if tSRAM: 
    oSRAM.close()
if tSense: 
    oSense.close()

# consolodate files in each folder
sys.exit()
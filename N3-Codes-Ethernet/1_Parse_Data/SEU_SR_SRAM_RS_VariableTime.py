# Author: Yoni Xiong
# Last Changed: 9-22-23
# Purpose: This file parses the serial data from the FPGA and organizes them in three files.

# 160 bits total
#SRs    -> "00100000"(32) + 133 ZEROS+ 7 bit index+12 bit count 
#SRAM0  -> "11100000"(224) as 8 bit tag + 13 bit addr + 64 bit word
#SRAM1  -> "11100001"(225) as 8 bit tag + 11 bit addr + 128 bit word

import time
import serial
from datetime import datetime
import os
import math

LAPTOP = True

# resistance at 25 degrees
THERMISTORNOMINAL = 10000
# tune this value!!
THERMISTORBASELINE =  850
# temp. for nominal resistance (almost always 25 C)
TEMPERATURENOMINAL = 25
# The beta coefficient of the thermistor (usually 3000-4000)
BCOEFFICIENT = 3950
# internal voltage reference of ADC
INTERNAL_VOLT_REF = 2.048

###############################################################

# user specified path for folder
PATH = "Q4_Jumper_Alpha/"
DATA = PATH + "data/"

# Check whether the specified path exists or not
if not os.path.exists(PATH):
  # Create a new directory because it does not exist
  os.makedirs(PATH)

# Check whether the specified path exists or not
if not os.path.exists(DATA):
  # Create a new directory because it does not exist
  os.makedirs(DATA)
SR_TAG = int('00100000', 2) # SR Tag
SRAM_TAG_0 = int('11100000', 2) # SRAM Tag
SRAM_TAG_1 = int('11100001', 2) # SRAM Tag
FFMCU_TAG = int('01100000',2) # FFMCU Tag
I2C1 = int('10000000', 2) # I2C data stream 1
I2C2 = int('01000000', 2) # I2C data stream 2

##############################################################
def useData(data):
    dataTag = data[0]
    dataOnly = data[1:20]
    if (dataTag == SR_TAG) and tSEU:
        processData(dataOnly, SR_TAG, oSEU, tDie,runningSum)
    elif (dataTag == SRAM_TAG_0) and tSRAM:
        processData(dataOnly, SRAM_TAG_0, oSRAM_0, tDie,runningSum)
    elif (dataTag == SRAM_TAG_1) and tSRAM:
        processData(dataOnly, SRAM_TAG_1, oSRAM_1, tDie,runningSum)
    elif (dataTag == FFMCU_TAG) and tFFMCU:
        processData(dataOnly, FFMCU_TAG, oFFMCU, tDie,runningSum)
    elif (dataTag == I2C1) and tSense:
        processData(dataOnly, I2C1, oSense, tDie,runningSum)
    elif (dataTag == I2C2) and tSense:
        processData(dataOnly, I2C2, oSense, tDie,runningSum)
    else:
        pass
        #print("Invalid input... Unexpected tag: ", dataTag)
        #print(dataOnly)

##############################################################

def processData(data, dtype, output, die, runningSum):
    now = datetime.now()
    current_time = now.strftime("%m/%d/%Y %H:%M:%S")
    if (dtype == SRAM_TAG_0):
        #Athena 13 bit addr + 64 bit word 
        if(die):
            # isolate 13 bit addr
            addr = data[8:11]
            # isolate 64 bit data
            datablock = data[11:20]
            output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
            print("%s-%s" % (addr.hex(), datablock.hex()))
        #Zeus
        else:
            # isolate 9 bit addr
            addr = data[13:14]
            # isolate 40 bit data
            datablock = data[14:20]
            output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
            print("%s-%s" % (addr.hex(), datablock.hex()))
    elif (dtype == SRAM_TAG_1):
        #Athena 11 bit addr + 128 bit word
        if(die):
            # isolate 11 bit addr
            addr = data[0:3]
            # isolate 128 bit data
            datablock = data[3:20]
            output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
            print("%s-%s" % (addr.hex(), datablock.hex()))
        #Zeus
        else:
            # isolate 10 bit addr
            addr = data[0:3]
            # isolate 128 bit data
            datablock = data[3:20]
            output.write("%s,%s,%s\n"%(current_time,addr.hex(), datablock.hex()))
            print("%s-%s" % (addr.hex(), datablock.hex()))
    elif (dtype == SR_TAG):
        data = int.from_bytes(data, "big")
        dataPacket = (data << 133) >> 133
        idx = dataPacket >> 12
        count = dataPacket & 0b111111111111
        if idx in runningSum:
            runningSum[idx] += count
        else:
            runningSum[idx] = count
        output.write("%s,%s,%s\n"%(current_time,str(idx),str(count)))
        print(str(idx) + "-" + str(count) + " (" + str(runningSum[idx]) + ") ")
    elif (dtype == FFMCU_TAG):
        ### when using MCU codes
        data = int.from_bytes(data,"big")
        idx = data >> 64
        idx &= 0b1111111111111111111111111
        count = data & 0b111111111111111111111111111111111111111111111111111111111111111
        value = bin(count)[2:].zfill(60) #strip off the leading "0b" and pad with leading 0's
        output.write("%s,%s,%s\n"%(current_time,str(idx),str(value)))
        print(str(idx) + "\t" + str(value))
    elif (dtype == I2C1):
        # Obtain 16 bit reading from ADC.
        data = int.from_bytes(data,"big")
        code = data & 0x0000FFFF
        voltage = INTERNAL_VOLT_REF * (code / 2**(15))

        # Equation is according to Texas Instruments' ADS1119 Datasheet thermistor resistance measurement.
        # Is described on page 35. Calculate resistance according to ADC code using nominal resistance of 1250 ohms.
        # Multiply by 2 to account for voltage dividers.
        R = 2 * THERMISTORBASELINE * (code / 2**15) / (1 - (code / 2**15))

        # For testing purposes. Used to observe variable resistance at temperature.
        # print("Resistor Value: ", R)
        # print("Code: ", voltage)

        # Use Steinhart-Hart's Beta parameter equation to compute the reciprocal of temperature in Kelvin.
        # Equation is described at the following: https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation
        temp_nominal_kelvin = TEMPERATURENOMINAL + 273.15
        reciprocal_temp_nominal = 1.0/temp_nominal_kelvin
        reciprocal_beta = 1.0/BCOEFFICIENT
        log_difference_R = math.log(R/THERMISTORNOMINAL)
        reciprocal_temperature = (reciprocal_beta * log_difference_R + reciprocal_temp_nominal)
        degrees_C = (1.0/reciprocal_temperature) - 273.15

        # I2C1 data stream 1
        print ("I2C_1 Data Temperature 1 = ", degrees_C)
        output.write("%s,%s,%s\n"%(current_time, "I2C_1", degrees_C))

        # Capture upper half and shift right by 16 to obtain reading from ADC.
        code = data & 0xFFFF0000
        code = code >> 16

        # For testing purposes. Used to observe voltage.
        voltage = INTERNAL_VOLT_REF * (code / 2**(15))

        # Equation is according to Texas Instruments' ADS1119 Datasheet thermistor resistance measurement.
        # Is described on page 35. Calculate resistance according to ADC code using nominal resistance of 1250 ohms.
        # Multiply by 2 to account for voltage dividers.
        R = 2 * THERMISTORBASELINE * (code / 2**15) / (1 - (code / 2**15))

        # For testing purposes. Used to observe variable resistance at temperature.
        # print("Resistor Value: ", R)
        # print("Code: ", voltage)

        # Use Steinhart-Hart's Beta parameter equation to compute the reciprocal of temperature in Kelvin.
        # Equation is described at the following: https://en.wikipedia.org/wiki/Steinhart%E2%80%93Hart_equation
        temp_nominal_kelvin = TEMPERATURENOMINAL + 273.15
        reciprocal_temp_nominal = 1.0/temp_nominal_kelvin
        reciprocal_beta = 1.0/BCOEFFICIENT
        log_difference_R = math.log(R/THERMISTORNOMINAL)
        reciprocal_temperature = (reciprocal_beta * log_difference_R + reciprocal_temp_nominal)
        degrees_C = (1.0/reciprocal_temperature) - 273.15

        print ("I2C_1 Data Temperature 2 = ", degrees_C)
        output.write("%s,%s,%s\n"%(current_time, "I2C_1", degrees_C))

    elif (dtype == I2C2):
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
        io_voltage = INTERNAL_VOLT_REF * (data / 2**(15)) * 2

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
        core_voltage = INTERNAL_VOLT_REF * (data / 2**(15)) * 2

        # Print Core Voltage to display. Record.
        print ("I2C_2 Data Stream Voltage_Core = ", core_voltage)
        output.write("%s,%s,%s\n"%(current_time, "I2C_2", core_voltage))
    else:
        pass # Print error message in main loop

###############################################################

print("\nWELCOME TO THE FPGA SCRIPT!\n")

run = str(input("Enter run number: ")).strip()
N5 = "N3" #str(input("Enter node (ex. N5): ")).strip().upper()
vdd =  str(input("Enter vdd (ex. 750): ")).strip()
cond = str(input("Enter input condition (ex. 111): ")).strip()
particle = "alpha-100u" #str(input("Enter particle (ex. alpha): ")).strip().upper()
freq = str(input("Enter freq (ex. 2.5): ")).strip()
degrees = str(input("Enter temp (ex. RT or 80C): ")).strip()
boardNum = str(input("Enter board nume (ex. ATHENA-Waf.Loc): ")).strip()

print()
dienum = str(input("A or Z?: ")).strip()

print()
tSEU = True#str(input("SEU? (y/n): ")).strip() == "y"
tSRAM = True#str(input("SRAM? (y/n): ")).strip() == "y"
tSense = False#str(input("Sensors? (y/n): ")).strip() == "y"
tFFMCU = False #str(input("Sensors? (y/n): ")).strip() == "y"
tDie = dienum.upper() == "A"

# Get com port
port = "com11"#str(input("Enter COM Port (ex. COM3): ")).strip().upper()

# Get name of testing file, and open output file for writing
file = DATA + "%s_%s_%s_%s_%s_%s_%s_%s" % (run, N5, vdd, cond, particle, freq, degrees, boardNum)

localtime = time.asctime(time.localtime(time.time()))

def create_file(file_name, header):
    file_path = file_name + ".csv"
    overwrite = False
    if os.path.isfile(file_path):
        name = file_name.split("_")[-1]
        overwrite = str(input(f"{name} already exists, want to overwrite? (y/n): ")).strip() == "y"
    # Update file_path
    if not overwrite:
        counter = 1
        while os.path.exists(file_path):
            file_path = file_name + " (" + str(counter) + ").csv"
            counter += 1
    oFile = open(file_path, "w+")
    oFile.write(header)  
    return oFile

print ("Start Time:", localtime)
if tSEU:
    fSEU = file + "_SEU"
    oSEU = create_file(fSEU, "Time,SR,Error Count\n")    
if tSRAM:
    fSRAM = file + "_SRAM0"
    oSRAM_0 = create_file(fSRAM, "Time,Address,Error Pattern\n")
    fSRAM = file + "_SRAM1"
    oSRAM_1 = create_file(fSRAM, "Time,Address,Error Pattern\n")
if tSense:
    fSense = file + "_Sense"
    oSense = create_file(fSense, "Time,Voltage,Current,Temperature\n")
if tFFMCU:
    fFFMCU = file + "_FFMCU"
    oFFMCU = create_file(fFFMCU, "Time,SR,Error Count\n")   

###############################################################
if LAPTOP: 
    controller = serial.Serial(port, 115200,8,"N",1) #about 15% slower than FPGA)
else: 
    port = "/dev/ttyS0"
    controller = serial.Serial(port, 450000,8,"N",1) #about 15% slower than FPGA)
controller.reset_input_buffer()
runningSum = {}

# Align packets read off serial bus 
#   read more than of expected packet size (22*2 + 4)
#   find location of /n/r in packet (always ends in this)
#   complete the next packet by reading partial packet off buffer
#   process both packets
#   all subsequent reads are done with expected packet size (22)
while controller.in_waiting < 48:
    pass
data = controller.read(48)
start = data.find(b'\r')
stop = data.find(b'\r',start+1,len(data))
complete = data[start+1:stop+1]
partial = data[stop+1:len(data)]
need = 22 -(len(data)-stop-1)
moredata = controller.read(need)
nextData = partial + moredata
useData(complete)
useData(nextData)
print(complete)
print(nextData)
counter = 0
max = int(60*60) # 30 minutes
starttime = time.time() # time in seconds
try:
    while (time.time() - starttime) < max: # 1 hour x 3600 seconds/hour x 60 packets/ 10 seconds
        while controller.in_waiting < 22 :
            pass
        data = controller.read(22)
        useData(data)
        counter +=1
        if (counter % 57) == 0: 
            print(str("{:.2f}".format(((time.time() - starttime)/max)*100)) + "% complete")

except KeyboardInterrupt:
    pass

if tSEU:
    oSEU.close()
if tSRAM:
    oSRAM_0.close()
    oSRAM_1.close()
if tSense:
    oSense.close()
if tFFMCU:
    oFFMCU.close()

fluenceFiles = PATH + 'RUN_LOG.csv'
oFluence = open(fluenceFiles, "a+")
oFluence.write("%s,%s,%s,%s,%s,%s,%s,%s\n"%(run, N5, vdd, cond, particle, freq, degrees, boardNum))
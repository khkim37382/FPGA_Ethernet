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
# import numpy as np
from datetime import datetime
import sys
import os

###############################################################

# user specified path for folder
PATH = "C:/Users/rerus/Desktop/7nm_Data/12_06_22/"


SR_NUM = 29 # Number of shift registers
SR_VALID_NUM = 26 # Number of valid registers
BYTES_TO_READ = 8
THRESHOLD = 4 # Number of SRs that can have errors at same cycle without being suspicious

##############################################################

def processData(data, output, runningSum):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    data = data.strip().decode('utf-8').split("-")
    output.write("%s,%s,%s\n"%(current_time,data[0],data[1]))
    if int(data[0]) in runningSum:
        runningSum[int(data[0])] += int(data[1],16)
    else:
        runningSum[int(data[0])] = int(data[1],16)
    print(data[0] + "-" + data[1] + " (" + str(runningSum[int(data[0])]) + ") ")

###############################################################

print("\nWELCOME TO THE FPGA SCRIPT!\n")

N5 = "N7"
vdd = str(input("Enter vdd (ex. 750): ")).strip()
particle = str(input("Enter particle (ex. alpha): ")).strip().upper()
freq = str(input("Enter freq (ex. 2.5): ")).strip()
degrees = str(input("Enter temp (ex. RT or 80C): ")).strip()
fluence = str(input("Fluence: ")).strip()
boardNum = str(input("Enter board nume (die - num) (ex. 3-14): ")).strip()

# Get com port
port = str(input("Enter COM Port (ex. COM3): ")).strip().upper()

# Get name of testing file, and open output file for writing
file = PATH + "%s_%s_%s_%s_%s_%s_%s" % (N5, vdd, particle, freq, degrees, fluence, boardNum)

localtime = time.asctime(time.localtime(time.time()))
print ("Start Time:", localtime)
fSEU = file + "_SEU.csv"
oSEU = open(fSEU, "w+")
oSEU.write("Time,SR,Error Count\n")

###############################################################
controller = serial.Serial(port, 115200)
controller.reset_input_buffer()
runningSum = {}
try:
    while True:
        while controller.in_waiting < BYTES_TO_READ : #change
            pass
        data = controller.read(BYTES_TO_READ)
        processData(data, oSEU, runningSum)
except KeyboardInterrupt:
    pass

oSEU.close()

# Create output file with same name as input file, adding _parsed.txt to the end
f = open(fSEU, "rt")
filename = fSEU + "_parsed.txt"
output = open(filename, "w+")

# Create an empty dictionary to keep data
data = {}
tempData = {}

# Init error line, counter, and errorSR values
errorLine = 1
counter = 0
errorSR = 0

# Skip first line
header = f.readline()

# Parse through all data in file
for line in f:

    # Skipping lines that are just the new line character
    if line != "\n":

        # Split line at -
        temp = line.split(",")

        # Fill temp dictionary wtih SR0 to SR_NUM - 1 error counts
        if counter < SR_NUM:
            # Get number of shift register, and number of errors that occurred (converted hex to decimal)
            x = int(temp[1])
            y = int(temp[2], 16)

            # Add to temp dictionary
            tempData[x] = y
            counter += 1

            # Update running counts in data dictionary (may be inaccurate since may account for suspicous errors)
            if x in data:
                data[x] += y
            else:
                data[x] = y
        # Once temp dictionary has been filled, check if multiple SRs experianced errors
        if counter == SR_NUM:
            for i in range(SR_VALID_NUM):
                try:
                    if tempData[i] > 0:
                        errorSR += 1
                except:
                    pass
            if errorSR > THRESHOLD:
                print("Verify cycle starting at ln." + str(errorLine) + " : " + str(errorSR) + " SRs had errors in one cycle.")
                errorSR = 0
            errorLine += SR_NUM
            # Print dictionary contents to output file
            for item in tempData:
                # Write items to output file
                output.write("%2d - %d" % ( item, tempData[item]))
                output.write("\n")
            counter = 0

# Print final sum to terminal
print ("\nNote - please verify any aforementioned cycles before trusting the following total error counts")
print("The following total errors occured for each SR: ")
for item in data:
    # Write items to terminal
    if item < SR_VALID_NUM:
        print("%2d : %d" % ( item, data[item]))

f.close()
output.close()

from datetime import datetime
import time
import visa
import csv
import os

PATH = "14-MeV-Neutrons/"
POWER_DATA = PATH + "power/"
# Check whether the specified path exists or not
if not os.path.exists(POWER_DATA):
  # Create a new directory because it does not exist 
  os.makedirs(POWER_DATA)

rm = visa.ResourceManager()

power_supply = 'USB::0x0957::0x0F07::SG53000125::INSTR'

my_inst = rm.get_instrument(power_supply)
print(my_inst.query('*IDN?'))

runnumber = str(input("Enter run number: ")).strip()
NODE = "N3"
vdd = str(input("Enter vdd (ex. 750): ")).strip()
cond = str(input("Enter input conditions (ex. 111): ")).strip()
particle = "14-MEV-Neutrons" #str(input("Enter particle (ex. alpha): ")).strip().upper()
freq = "2.5" #str(input("Enter freq (ex. 2.5): ")).strip()
degrees = "RT" #str(input("Enter temp (ex. RT or 80C): ")).strip()
boardNum = "AThENA-ZEUS-W8-W7"#str(input("Enter board nume (ex. ATHENA-Waf.Loc): ")).strip()
print()
filename = POWER_DATA + "%s_%s_%s_%s_%s_%s_%s_%s" % (runnumber,NODE, vdd, cond, particle, freq, degrees, boardNum)

VDD_Athena = input("Athena VDD: ")
VDDIO_Athena = input("Athena VDDIO: ")
VDD_Zeus = input("Zeus VDD: ")
VDDIO_Zeus = input("Zeus VDDIO: ")

my_inst.write("VOLT "+str(VDD_Athena)+",(@1)")
my_inst.write("VOLT "+str(VDDIO_Athena)+",(@2)")
my_inst.write("VOLT "+str(VDD_Zeus)+",(@3)")
my_inst.write("VOLT "+str(VDDIO_Zeus)+",(@4)")

my_inst.write("OUTP ON,(@1,2,3,4)")

name = filename + '_power.csv'
file = open(name, 'w', newline='')
writer = csv.writer(file)

try:
    while True:
        v = my_inst.query_ascii_values("MEAS:VOLT? (@1,2,3,4)")
        c = my_inst.query_ascii_values("MEAS:CURR? (@1,2,3,4)")
        time.sleep(1)
        assemble = v+c
        now = datetime.now()
        current_time = now.strftime("%m/%d/%Y %H:%M:%S")
        writer.writerow([current_time]+assemble)
        print([current_time]+assemble)
except KeyboardInterrupt:
    my_inst.write("OUTP OFF,(@1,2,3,4)")
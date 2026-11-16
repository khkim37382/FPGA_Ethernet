from koradserial import KoradSerial
import csv
import time
import os

PATH = "MURR/"
POWER_DATA = PATH + "power/"

# Check whether the specified path exists or not
if not os.path.exists(POWER_DATA):
  # Create a new directory because it does not exist 
  os.makedirs(POWER_DATA)

try:
    runnumber = str(input("Enter run number: ")).strip()
    N5 = "N3" #str(input("N7 or N5: ")).strip()
    vdd = str(input("Enter vdd (ex. 750): ")).strip()
    cond = str(input("Enter input conditions (ex. 111): ")).strip()
    particle = str(input("Enter particle (ex. alpha): ")).strip().upper()
    freq = str(input("Enter freq (ex. 2.5): ")).strip()
    degrees = str(input("Enter temp (ex. RT or 80C): ")).strip()
    boardNum = str(input("Enter board nume (ex. ATHENA-Waf.Loc): ")).strip()
    print()
    port = input("What port is the PSU on?: ")

    power_supply = KoradSerial(port)
    power_supply.close()
    start_time = time.time()
    chan = power_supply.channels[0]
    print()
    outvoltage = input("OUTPUT VOLTAGE (V): ")
    while float(outvoltage) > 1.2:
        print("Output voltage too high, please input a value less than 1 V")
        outvoltage = input("OUTPUT VOLTAGE(V): ")
    current_lim = input("CURRENT LIMIT (A): ")
    while float(current_lim) > 4:
        print("Current limit too high, please input a value less than 4 A")
        outvoltage = input("CURRENT LIMIT (A): ")
    print()
    filename = POWER_DATA + "%s_%s_%s_%s_%s_%s_%s_%s" % (runnumber,N5, vdd, cond, particle, freq, degrees, boardNum)

    power_supply.open()
    if(power_supply.is_open != True):
        print("failure")
        quit()
    chan.current = float(current_lim)
    chan.voltage = float(outvoltage)

    name = filename + '_power.csv'
    file = open(name, 'w', newline='')
    writer = csv.writer(file)
    power_supply.output.on()
    writer.writerow([(time.time()), "Voltage (V)", "Current (A)"])
    print("T = 0 (s)   \tVoltage (V)\tCurrent (A)")
    while True:
        voltage = chan.output_voltage
        current = chan.output_current
        time.sleep(3)
        runTime = int(time.time()-start_time)
        print("T = " + str(runTime) + " (s)   \t" + str(voltage) + " (V)\t\t" + str(current) + " (A)")
        writer.writerow([(runTime),(voltage),(current)])

except KeyboardInterrupt:
    print()
    file.close()
    turn_off = str("turn off power supply? (y/n)").strip().upper() == "Y"
    if turn_off:
        power_supply.output.off()
    power_supply.close()
    fluenceFIles = PATH + 'RUN_LOG.csv'
fluence = str(input("Enter final fluence: ")).strip()
oFluence = open(fluenceFIles, "a+")
oFluence.write("%s,%s,%s\n"%(runnumber,name,fluence))

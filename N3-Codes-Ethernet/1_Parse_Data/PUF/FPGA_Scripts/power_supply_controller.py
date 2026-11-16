#import koradctl
from .koradserial import KoradSerial
import time
import serial.tools.list_ports

VOLTAGE_RAMP_DURATION = 1  # seconds
VOLTAGE_TARGET = 0.75  # volts
VOLTAGE_STEP_SIZE = 0.03  # volts
WAIT_TIME = 1  # seconds
HIGH_TIME = 1  # seconds
LOW_TIME = 2 # seconds

def increase_voltage(psu, duration):

    # Turn on the output and set initial voltage
    channel = psu.channels[0]
    channel.voltage = 0

    # Show status
    print("Output: {}".format(psu.status.output))

    time.sleep(LOW_TIME)

    # Calculate the sleep time for each increment
    total_steps = (VOLTAGE_TARGET - 0)/VOLTAGE_STEP_SIZE  # (0.75V - 0V) / 0.01V
    sleep_time = duration / total_steps
    # Incrementally increase the voltage
    for step in range(int(total_steps + 1)):
        new_voltage = step * VOLTAGE_STEP_SIZE
        channel.voltage = new_voltage
        time.sleep(sleep_time)

    # Set final voltage
    channel.voltage = 0.75

    print("End of cycle")
    # Wait for the voltage to settle for 1 second
    time.sleep(HIGH_TIME)

    # Turn off the output (optional)
    # psu.output.off()
    # channel.voltage = 0

def initialize_power_supply(port):
    # Initialize the power supply
    psu = KoradSerial(port)

    # Check if the serial port is open
    if not psu.is_open:
        raise Exception("Power supply is not connected")
    else:
        print("Power supply connected")

    # Print the model and status
    print("Model: {}".format(psu.model))
    print("Status: {}".format(psu.status))

    # Return the power supply object
    return psu

def run_power_supply_controller(psu):
    psu.output.on()
    # In a loop increase the voltage by 0.01V every 0.5 seconds until 0.75V is reached
    while True:
        increase_voltage(psu, VOLTAGE_RAMP_DURATION)
    
    psu.output.off()

def initialize_power_supply_process(port, flag):

    # Initialize the power supply
    psu = KoradSerial(port)

    # Check if the serial port is open
    if not psu.is_open:
        raise Exception("Power supply is not connected")
    else:
        print("Power supply connected")

    # Print the model and status
    print("Model: {}".format(psu.model))
    print("Status: {}".format(psu.status))

    while True:
        if flag.recv():
            print("PSU triggered by end of cycle\n")
            time.sleep(WAIT_TIME)
            # Turn on the output and set initial voltage
            channel = psu.channels[0]
            channel.voltage = 0

            # Show status
            # print("Output: {}".format(psu.status.output))

            time.sleep(LOW_TIME)

        #       DISABLED RAMPUP FOR EXPERIMENTATION
        #
        #    # Calculate the sleep time for each increment
        #    total_steps = (VOLTAGE_TARGET - 0)/VOLTAGE_STEP_SIZE  # (0.75V - 0V) / 0.01V
        #    sleep_time = duration / total_steps
        #    # Incrementally increase the voltage
        #    for step in range(int(total_steps + 1)):
        #        new_voltage = step * VOLTAGE_STEP_SIZE
        #        channel.voltage = new_voltage
        #        time.sleep(sleep_time)

            # Set final voltage
            channel.voltage = 0.75

            print("End of cycle")

        else:
            pass

def main():
    # Find serial port (macOS)
    # Present a list of serial ports
    # Show a number to the left and prompt the user to input the number of the port they want to use
    ports = serial.tools.list_ports.comports()
    port_num = 1
    for port, desc, hwid in sorted(ports):
        # Print a nubmer to the left of the port
        print("{}.\t{}: {} [{}]".format(port_num, port, desc, hwid))
        port_num += 1
    
    # Prompt the user to input the number of the port they want to use
    port_num = int(input("Enter the number of the port you want to use: "))

    # Select the port, accounting for the format of the list
    port = str(ports[port_num - 1][0])

    # Initialize the power supply
    psu = initialize_power_supply(port)

    # Run the power supply controller
    run_power_supply_controller(psu)

    # Exit
    exit()


if __name__ == "__main__":
    main()
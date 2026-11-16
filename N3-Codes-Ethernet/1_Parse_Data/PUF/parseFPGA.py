import serial.tools.list_ports
import multiprocessing
import serial

from FPGA_Scripts.FPGA_Parser_N3 import N3FPGA
from FPGA_Scripts.FPGA_Parser_N5 import N5FPGA

import FPGA_Scripts.power_supply_controller as psu

####################################################################################################
# Helper functions
####################################################################################################

def get_FPGA_communication_mode():
    # Get the FPGA communication mode
    if input("Enter \"y\" if you are using an external FTDI chip to communicate with the FPGA: ") == "y":
        mode = "FTDI"
    else:
        mode = "USB"
    
    return mode

def find_device_port():
    # Find serial port (macOS)
    # Present a list of serial ports
    # Show a number to the left and prompt the user to input the number of the port they want to use
    ports = serial.tools.list_ports.comports()
    port_num = 1
    for port, desc, hwid in sorted(ports):
        # Print a nubmer to the left of the port
        print("{}.\t{}: {} [{}]".format(port_num, port, desc, hwid))
        port_num += 1
    
    try:
        # Prompt the user to input the number of the port they want to use
        port_num = int(input("Enter the number of the port you want to use: "))
    except ValueError:
        print("Invalid input")
        exit()
    except KeyboardInterrupt:
        print("\nUser requested program termination. Exiting...")
        exit()

    # Select the port, accounting for the format of the list
    # check if the port number is valid
    if port_num < 1 or port_num > len(ports):
        print("Invalid port number")
        exit()
    else:
        port = str(ports[port_num - 1][0])

    return port

def get_IC_description():

    ic_node = input("Enter IC Node (N3 or N5): ").upper()

    if ic_node in ['N5', '5']:
        ic_node = 'N5'
        ic_design = input("Enter die config (C20 or C21): ").upper()
        if ic_design == 'C20' or ic_design == '20':
            ic_design = 'C20'
        elif ic_design == 'C21' or ic_design == '21':
            ic_design = 'C21'
        else:
            raise Exception("Invalid die specified") 
    elif ic_node in ['N3', '3']:    
        
        ic_node = 'N3'
        # Ask user if they are running FFMCU code, if they are, prompt them to set SW12 high on the FPGA
        print("If you are running FFMCU code, please set SW12 high on the FPGA.")
        
        ic_design = input("Enter die config (A or Z): ").upper()

        if not(ic_design in ['A', 'Z']):
            raise Exception("Invalid die specified")
        
    else:
        raise Exception("Invalid IC Node")

    return ic_node, ic_design

def calculate_stop_address(node, die):

    if node == 'N5':
        if die == 'C20' or die == '20':
            stop_address = '1FFF'
        elif die == 'C21' or die == '21':
            stop_address = '3FF'
        else:
            raise Exception("Invalid die specified")    
    elif node == 'N3':

        if die == 'A':
            # Prompt the user for the stop address based on the SRAM they're using
            response = input("Enter SRAM Stop Address:\n\t1. 1FFF\n\t2. 7FF\n")
            if response == '1':
                stop_address = '001FFF'
            elif response == '2':
                stop_address = '0007FF'
            else:
                raise Exception("Invalid SRAM Stop Address")
            
        elif die == 'Z':
            raise Exception("N3 Zeus is not supported yet")
        else:
            raise Exception("Invalid die specified")
    else:
        raise Exception("Invalid IC Node")
    
    return stop_address

####################################################################################################
# Main functions
####################################################################################################

def run_FPGA_script():
    print("\nWELCOME TO THE FPGA SCRIPT!\n")
    
    try:
        node, die = get_IC_description()
    except Exception as e:
        print(e)
        exit()
    
    try:
        if node == 'N3':
             # Initialize FPGAScript
            fpga_script = N3FPGA(get_FPGA_communication_mode(), die)
            fpga_script.handle_data_stream_N3(flag=None)
    
        elif node == 'N5':
            fpga_script = N5FPGA(get_FPGA_communication_mode(), die)
            fpga_script.handle_data_stream_N5(flag=None)
        else:
            raise Exception("Invalid IC Node, cannot run FPGA parsing script")
        
    except KeyboardInterrupt:
        pass

def power_supply_controller():
    # Code to run power supply controller
    print("\nWELCOME TO THE POWER SUPPLY CONTROLLER!\n")

    # Find serial port (macOS)
    port = find_device_port()

    # Initialize the power supply
    psu_obj = psu.initialize_power_supply(port)

    # Run the power supply controller
    psu.run_power_supply_controller(psu_obj)

    # Exit
    exit()

def run_combined_FPGA_and_PSU():
    # Not setup yet. Just pass for now
    print("WELCOME TO THE FPGA AND POWER SUPPLY CONTROL SCRIPT!\n")

    print("\nSelect the port for the power supply:")
    port = find_device_port()

    try:
        node, die = get_IC_description()
    except Exception as e:
        print(e)
        exit()

    # Initialize FPGAScript
    try:
        if node == 'N3':
            fpga_script = N3FPGA(get_FPGA_communication_mode(), die)
        elif node == 'N5':
            fpga_script = N5FPGA(get_FPGA_communication_mode(), die)
        else:
            raise Exception("Invalid IC Node, cannot run FPGA parsing script")
        
    except KeyboardInterrupt:
        pass


    tx_flag, rx_flag = multiprocessing.Pipe()

    try:
        psu_process = multiprocessing.Process(target=psu.initialize_power_supply_process, args=(port, rx_flag))
    except Exception as e:
        print(e)
        exit()

    psu_process.start()

    try:
        # Ask user if they are running FFMCU code, if they are, prompt them to set SW12 high on the FPGA
        # input("If you are running FFMCU code, please set SW12 high on the FPGA. Press enter to continue.")
        fpga_script.handle_data_stream(tx_flag)
        
    except KeyboardInterrupt:
        pass

    psu_process.join()
    exit()

####################################################################################################
# Main
####################################################################################################

def main():
    
    print("What do you want to do?")
    print("1. Run FPGA script")
    print("2. Run power supply controller")
    print("3. Run combined FPGA and power supply controller")

    try:
        choice = input("Enter the number corresponding to your choice: ")
    except KeyboardInterrupt:
        print("\nExiting...")
        exit()

    if choice == "1":
        run_FPGA_script()
    elif choice == "2":
        power_supply_controller()
    elif choice == "3":
        run_combined_FPGA_and_PSU()
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

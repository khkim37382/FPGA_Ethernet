import serial.tools.list_ports

# Get a list of available USB ports
ports = list(serial.tools.list_ports.comports())

# Prompt the user to select a port from the list
print("Available USB ports:")
for i, port in enumerate(ports):
    print(f"{i+1}. {port.device}")
selected_port_index = int(input("Select a port (enter the corresponding number): ")) - 1
selected_port = ports[selected_port_index].device

# Open the selected port at a baud rate of 434000
ser = serial.Serial(selected_port, baudrate=115200)

# Example Data: b'\x00\x00\x00\x00\x00\x00\x00\x0206\x85\x0f\xf7\xcf\xff\xff\xff\xfc\xff\n\r`\x00'
def format_data(data):

    # Split it into a tag and data portion then return a string "Tag: []\tData: []"
    # tag is 8 bits
    
    dataTag = data[0]
    dataOnly = data[1:20]

    # Convert the data to a string of hex values
    dataString = ' '.join([f"{byte:02x}" for byte in dataOnly])
    return f"Tag: {dataTag}\tData: {dataString}"
    

# Continuously read from the port and print the data to the console
while True:
    while ser.in_waiting < 48:
        pass
    
    # Align packets read off serial bus 
    # Read more than of expected packet size (22*2 + 4)
    data = ser.read(48)
        
    # Find location of /n/r in packet (always ends in this)
    start = data.find(b'\r')
    stop = data.find(b'\r',start+1,len(data))
        
    # Complete the next packet by reading partial packet off buffer
    complete = data[start+1:stop+1]
    partial = data[stop+1:len(data)]
    need = 22 -(len(data)-stop-1)
    moredata = ser.read(need)
    nextData = partial + moredata

    # Print the data to the console
    print(format_data(complete))
    print(format_data(nextData))

    while True:
        while ser.in_waiting < 22 :
                pass
        print(format_data(ser.read(22)))

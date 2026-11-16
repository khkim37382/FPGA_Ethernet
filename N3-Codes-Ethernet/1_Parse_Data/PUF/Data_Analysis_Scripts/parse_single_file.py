import pandas as pd

# Set the default width of the error pattern
ERROR_PATTERN_WIDTH = 76

# Set the address length
ADDRESS_LENGTH = 4

# This is a TERRIBLE way to do this, but it works for now
def set_global_variables(node, die, stop_address):

    global ADDRESS_LENGTH
    ADDRESS_LENGTH = len(stop_address)
    print(f"Using ADDRESS_LENGTH = {ADDRESS_LENGTH}")

    # Error pattern width: C20 = 32, C21 = 76, A = XX, Z = XX
    global ERROR_PATTERN_WIDTH
    if node == 'N5' and die == 'C20':
            ERROR_PATTERN_WIDTH = 32
    elif node == 'N5' and die == 'C21':
            ERROR_PATTERN_WIDTH = 76
    elif node == 'N3' and die == 'A':
        if stop_address == "001FFF":
            ERROR_PATTERN_WIDTH = 64
        elif stop_address == "0007FF":
            ERROR_PATTERN_WIDTH = 128
        else:
            raise Exception("Unexpected Error Occurred")
    elif node == 'N3' and die == 'Z':
        #if stop_address == "001FFF":
        #    ERROR_PATTERN_WIDTH = 64
        #elif stop_address == "0007FF":
        #    ERROR_PATTERN_WIDTH = 128
        #else:
        #    raise Exception("Unexpected Error Occurred")
        
        raise Exception("N3 Zeus is not supported yet")    
        
    else:
        raise Exception("Invalid IC Configuration")
    
    print(f"Using ERROR_PATTERN_WIDTH = {ERROR_PATTERN_WIDTH}")


def read_file(filename):
    full_df = pd.read_csv(filename, usecols=["Address", "Error Pattern"])

    # Assuming 'Address' is already a string; ensure it's padded correctly
    full_df['Address'] = full_df['Address'].apply(lambda x: x.zfill(ADDRESS_LENGTH).upper())

    # Split the dataframe at each occurrence of address '0' (zero padded to the address length)
    datasets = []
    last_index = 0
    for index, row in full_df.iterrows():
        if row['Address'] == '0' * ADDRESS_LENGTH:
            # Include the row with '0' in the previous dataset
            if index != last_index:
                datasets.append(full_df.iloc[last_index:index])
            last_index = index # Start the next dataset after the '000' address row

    # Append the last segment if not empty
    if last_index != len(full_df):
        datasets.append(full_df.iloc[last_index:])

    return datasets

def convert_to_binary(hex_string):
    return bin(int(hex_string, 16))[2:].zfill(ERROR_PATTERN_WIDTH)

def filter_datasets(datasets, stop_address):
    filtered_datasets = []
    remove_dataset = False

    for df in datasets:
        #print(df.head())

        # Check if the df starts at 0 (convert df value to hex)
        if int(df.iloc[0]['Address'], 16) != 0:
            print("Dataset does not start at 0")
            remove_dataset = True
            
        # Check if the df ends at the stop address
        elif int(df.iloc[-1]['Address'], 16) != int(stop_address, 16):
            print("Dataset does not end at the stop address")
            remove_dataset = True

        if not remove_dataset:
            filtered_datasets.append(df)
        
        remove_dataset = False


    print(f"Found {len(filtered_datasets)} datasets after filtering")

    return filtered_datasets

def process_files(dfs, stop_address):
    stop_address_int = int(stop_address, 16)
    
    address_counter = {(hex(i)[2:].zfill(ADDRESS_LENGTH).upper(), bit): [0, 0] for i in range(stop_address_int + 1) for bit in range(ERROR_PATTERN_WIDTH)}

    for df in dfs:
        df['Binary Pattern'] = df['Error Pattern'].apply(convert_to_binary)

        for index, row in df.iterrows():
            address = str(row['Address']).zfill(3).upper()
            bit_pos = 0
            if int(address, 16) > stop_address_int:
                continue
            for bit in row['Binary Pattern']:
                if bit == '0':
                    address_counter[(address, bit_pos)][0] += 1
                elif bit == '1':
                    address_counter[(address, bit_pos)][1] += 1
                bit_pos += 1

    return address_counter

def main():

    print("Welcome to the Data Analysis Script")
    print("This script will parse a single file and output a CSV file with the results")
    print("\n\nCurrently configured for: N5 die C21")
    stop_address = "3FF"    
    set_global_variables('N5', 'C21', stop_address)

    datasets = read_file()
    print(f"Found {len(datasets)} datasets")

    # Filter datasets
    datasets = filter_datasets(datasets)

    match_counter = process_files(datasets, stop_address)

    # Output to a file
    output_filename = f'output_dataset.csv'
    with open(output_filename, 'w') as f:
        f.write("Address,Bit Position,Zeros Match,Ones Match\n")
        for (address, bit_pos), counts in match_counter.items():
            f.write(f"{address},{bit_pos},{counts[0]},{counts[1]}\n")

    print(f"Output saved to {output_filename}")

if __name__ == "__main__":
    main()

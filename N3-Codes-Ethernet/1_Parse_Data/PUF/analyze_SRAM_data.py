import os
import csv
import pandas as pd

import Data_Analysis_Scripts.parse_single_file as parse
import Data_Analysis_Scripts.visualization as vis
import Data_Analysis_Scripts.signature_comparison as sig_comp
import Data_Analysis_Scripts.signature_identifier as sig_id
import Data_Analysis_Scripts.bulk_compare_sram_signatures as bulk_compare

####################################################################################################
# Helper functions
####################################################################################################

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
        
        ic_design = input("Enter die config (A or Z): ").upper()

        if not(ic_design in ['A', 'Z']):
            raise Exception("Invalid die specified")
        
    else:
        raise Exception("Invalid IC Node")

    return ic_node, ic_design

def calculate_stop_address(node, die, sram_num=None):
    """
        @brief This function will calculate the SRAM end address based on the IC node and die type
        @param node The IC node
        @param die The die type
        @param sram_num The SRAM number (0 or 1 -- for N3 only)
        @return The SRAM end address
    """

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
            if sram_num == '0':
                stop_address = '001FFF'
            elif sram_num == '1':
                stop_address = '0007FF'
            else:
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

def aggregate_sram_data():
    try:
        node, die = get_IC_description()

        # Get the stop address, ask the user which SRAM they're using
        stop_address = calculate_stop_address(node, die)
    except Exception as e:
        print(e)
        exit()

    parse.set_global_variables(node, die, stop_address)

    # Read the file
    filepath = input("Enter the file path to the CSV file: ")
    datasets = parse.read_file(filepath)

    print(f"Found {len(datasets)} datasets")

    # Filter datasets
    datasets = parse.filter_datasets(datasets)

    match_counter = parse.process_files(datasets, stop_address)

    # Prompt the user for a file identifier
    identifier = input("Please enter an identifier for the output file: ")
    # Synthesize the file name as analyzed_sram_[identifier]_[len(datasets)]_datasets.csv
    output_filename = f'analyzed_sram_{identifier}_length-{len(datasets)}.csv'
    with open(output_filename, 'w') as f:
        f.write("Address,Bit Position,Zeros Match,Ones Match\n")
        for (address, bit_pos), counts in match_counter.items():
            f.write(f"{address},{bit_pos},{counts[0]},{counts[1]}\n")

    print(f"Output saved to {output_filename}")
    
def run_sram_aggregate_visualization():
    # Code to run visualization
    file_path = input("Please enter the file path to your CSV: ")
    
    df = vis.load_and_process_data(file_path)

    # Create and display the aggregated heatmap
    vis.create_aggregated_heatmap(df)

def run_signature_identifier():
    file_path = input("Please enter the file path to your CSV: ")
    identifier = input("Please enter an identifier for the output file: ")
    data, max_value = sig_id.read_csv(file_path)
    sig_id.process_data_for_csv(data, max_value, identifier)

def run_signature_visualization():
    signature_file_path = input("Please enter the file path to your Signature CSV: ")
    sig_id.create_visualization_from_signature(signature_file_path)

def run_signature_comparison():
    # Get the paths to the signature files
    file_path1 = input("Enter the path to the first signature file: ")
    file_path2 = input("Enter the path to the second signature file: ")

    # Compare the signatures
    uniqueness = sig_comp.compare_signatures(file_path1, file_path2)

    # Print the result
    print(f"Signature uniqueness: {uniqueness:.2f}%")

def run_full_sram_analysis():

    # Path to the folder containing RAW sram data
    folder_name = input("Enter the name of the folder containing the raw SRAM data: ")
    usr_identifier = input("Enter an identifier for the output files: ")
    
    # Check the folder exists
    if not os.path.exists(folder_name):
        raise Exception("Folder not found")

    try:
        node, die = get_IC_description()

    except Exception as e:
        print(e)
        exit()

    # Identify the file to analyze (look for all .csv files with the word "SRAM" in them)
    # If there the node is N3, then we will need to look for two files SRAM0 and SRAM1
    files = []
    for file in os.listdir(folder_name):
        if file.endswith(".csv") and "SRAM" in file:
            files.append(file)

    if len(files) == 0:
        raise Exception("No files found")
    elif len(files) == 1 and node == 'N5':
        print(f"Found 1 file: {files[0]}")
    elif len(files) == 2 and node == 'N3':
        print(f"Found {len(files)} files: {files}")
    else:
        raise Exception("Unexpected number of files found")

    analyzed_sram_files = []
    identifiers = []

    for file in files:

        file_path = os.path.join(folder_name, file)

        # Get the stop address based on the IC node and die
        # N5 C20 = 1FFF, C21 = 3FF, 
        # N3 is more complicated: 
        #   if SRAM0 then: A = 1FFF, Z = 3FF
        #   if SRAM1 then: A = 7FF, Z = 7FF
    
        if node == 'N3':
            if 'SRAM0' in file:
                stop_address = calculate_stop_address(node, die, '0')
            elif 'SRAM1' in file:
                stop_address = calculate_stop_address(node, die, '1')
            else:
                raise Exception("The N3 SRAM file name that was found is not valid")
        else:
            stop_address = calculate_stop_address(node, die)

        # Set the variables for the address length and error pattern width
        parse.set_global_variables(node, die, stop_address)

        # Extract SRAM data into a dataframe
        datasets = parse.read_file(file_path)
        print(f"Found {len(datasets)} datasets")

        # Filter datasets by removing incomplete chunks of SRAM data
        datasets = parse.filter_datasets(datasets, stop_address)

        # Process the data into 1 and 0 counts for each address and bit position
        match_counter = parse.process_files(datasets, stop_address)

        # The output file will be in the user provided folder
        # Synthesize the file name as analyzed_sram_[identifier]_[len(datasets)]_datasets.csv
        identifier = f"{node}_{die}_{usr_identifier}_SRAM{files.index(file)}"
        identifiers.append(identifier)
        output_filename = f'analyzed_sram_{identifier}_length-{len(datasets)}.csv'
        output_filename = os.path.join(folder_name, output_filename)
        
        with open(output_filename, 'w') as f:
            f.write("Address,Bit Position,Zeros Match,Ones Match\n")
            for (address, bit_pos), counts in match_counter.items():
                f.write(f"{address},{bit_pos},{counts[0]},{counts[1]}\n")

        print(f"Saved analyzed SRAM file to {output_filename}")
        analyzed_sram_files.append(output_filename)

    
    # Create visualizations from the analyzed SRAM data
    # Also determine the PUF signature
    # Save these to the folder
    index_ct = 0
    for file in analyzed_sram_files:
        df = vis.load_and_process_data(file)

        # SRAM visualization
        save_file = os.path.join(folder_name, f'visualization_{identifiers[index_ct]}.png')
        vis.save_aggregated_heatmap(df, save_file)
    
        # Process the signature and save it
        data, max_value = sig_id.read_csv(file)
        sig_file = sig_id.process_data_for_csv(data, max_value, identifiers[index_ct], folder_name)
        
        # Signature visualization
        save_file = os.path.join(folder_name, f'signature_visualization_{identifiers[index_ct]}.png')
        sig_id.save_visualization_from_signature(sig_file, save_file)

        index_ct += 1

def bulk_compare_sram_signatures():

    print("This script takes an input folder containing signature files and outputs a CSV file of SRAM the uniquenesses in a 2D grid")
    print("Note that any file with the identifier \"signature\" in the title will be queued for comparison, \
          so remove any signature files that you do not with to compare, such as SRAM0 vs SRAM1 files or FF scan chain signature files ")
    input("\nPress any key to continue...")

    directory = input("Enter the directory path containing the signature files: ")
    identifier = input("Enter the output CSV file identifier: ")

    signature_files = bulk_compare.find_signature_files(directory)
    uniqueness_matrix = bulk_compare.compare_all_signatures(signature_files)

    output_file = f"SRAM_uniqueness_matrix_{identifier}.csv"
    bulk_compare.write_to_csv(uniqueness_matrix, output_file)

    print(f"Results have been written to {output_file}")

def compare_signature_with_raw_file():
    signature_file = input("Enter the path to the signature file: ")
    signature_df = pd.read_csv(signature_file)
    signature_df['Address'] = signature_df['Address'].apply(lambda x: f"{int(x, 16):03X}")
    signature_df['Bit Position'] = signature_df['Bit Position'].astype(int)
    signature_df['Value'] = signature_df['Value'].astype(str)
    sig_length = len(signature_df[signature_df['Value'] != 'X'])

    print(f"The signature length: {sig_length}\n")

    raw_sram_file = input("Enter the path to the raw SRAM data file: ")
    try:
        node, die = get_IC_description()
        stop_address = calculate_stop_address(node, die)
        stop_address_int = int(stop_address, 16)
    except Exception as e:
        print(e)
        return

    parse.set_global_variables(node, die, stop_address)
    datasets = parse.read_file(raw_sram_file)
    datasets = parse.filter_datasets(datasets, stop_address)

    print(f"Found {len(datasets)} datasets")

    # Create a dictionary for faster lookup
    signature_dict = {(row['Address'], row['Bit Position']): row['Value'] for _, row in signature_df.iterrows()}

    reliabilities = []

    dataset_count = 1

    for dataset in datasets:
        dataset['Binary Pattern'] = dataset['Error Pattern'].apply(parse.convert_to_binary)
        dataset['Address'] = dataset['Address'].apply(lambda x: int(x, 16))
        signature_does_not_match = 0
        signture_matches = 0

        for index, row in dataset.iterrows():
            address = row['Address']
            if address > stop_address_int:
                continue

            bit_pos = 0

            for bit in row['Binary Pattern']:
                signature_value = signature_dict.get((f"{address:03X}", bit_pos))
                if str(bit) != signature_value and signature_value != 'X':
                    signature_does_not_match += 1
                    print(f"Address {address:03X}, bit pos {bit_pos} mismatch: {bit} != signature value {signature_value}")
                elif signature_value != 'X':
                    signture_matches += 1
                    # Don't print anything if the signature value is X
                    # print(f"Signature value is X at address {address:03X} and bit position {bit_pos}", end='\r')
                #else:
                    # Print signature match but don't print to a new line
                    # print(f"Signature matches at address {address:03X} and bit position {bit_pos} with value {bit} and signature value {signature_value}", end='\r')
                
                
                bit_pos += 1

        print(f"Finished parsing dataset {dataset_count}. \nSignature matches: {signture_matches}, \nSignature mismatches: {signature_does_not_match}\nTotal signature length: {sig_length}\n")
        reliability = 1 - (signature_does_not_match / sig_length)
        reliabilities.append(reliability)
        print(f"Reliability was {reliability * 100:.2f}%")
        dataset_count += 1

    overall_reliability = sum(reliabilities) / len(reliabilities)
    print(f"Overall Reliability: {overall_reliability * 100:.2f}%")

####################################################################################################
# Main
####################################################################################################

def main():
    
    print("What do you want to do?")
    print("1. Run full SRAM analysis")
    print("---- Modes 2-5 simply decompose option 1 into steps ----")
    print("2. Aggregate SRAM data")
    print("3. Visualize aggregated SRAM data")
    print("4. Run signature identifier")
    print("5. Run signature visualization")
    print("--------------------------------------------------------")
    print("6. Compare two signatures")
    print("7. Bulk comparison of SRAM signatures")
    print("8. Compare signature with raw SRAM read data")

    try:
        choice = input("Enter the number corresponding to your choice: ")
    except KeyboardInterrupt:
        print("\nExiting...")
        exit()

    if choice == "1":
        run_full_sram_analysis()
    elif choice == "2":
        aggregate_sram_data()
    elif choice == "3":
        run_sram_aggregate_visualization()
    elif choice == "4":
        run_signature_identifier()
    elif choice == "5":
        run_signature_visualization()
    elif choice == "6":
        run_signature_comparison()
    elif choice == "7":
        bulk_compare_sram_signatures()
    elif choice == "8":
        compare_signature_with_raw_file()
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

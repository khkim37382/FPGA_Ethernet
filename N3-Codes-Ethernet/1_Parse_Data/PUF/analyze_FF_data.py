
# This program should perform comprehensive analysis of the PUF data for all scan chains
# Program flow is as follows:
#   - Request a folder path from the user where the data is stored
#   - Find the file that contains the data (file should contain the word "FFMCU" in the name)
#   - Parse the data and find the scan chains
#   - Analyze the scan chains in the folder "transposed_scan_chains" which exists in the folder provided to find the signatures
#   - Store the scan chains and signatures in a CSV file called "scan_chain_signatures_{id}_{threshold}%.csv"

import os
import pandas as pd
from Data_Analysis_Scripts.scan_chain_comparison import ScanChainComparison as compare
from Data_Analysis_Scripts.scan_chain_parse import ScanChainParser as parse
from Data_Analysis_Scripts.scan_chain_analysis import ScanChainAnalysis as analyze

def get_inputs():
    """
        @brief: Get the inputs from the user. Incl. folder path, threshold, identifier, and IC node
        @return: folder_path, file_path, threshold, identifier, ic_node, ic_design
    """

    folder_path = input("Enter the folder path: ")

    # Find the file that contains the data
    file_name = None
    for file in os.listdir(folder_path):
        if "FFMCU" in file:
            file_name = file
            break

    if file_name is None:
        raise Exception("No FFMCU file found in the folder")

    file_path = os.path.join(folder_path, file_name)

    identifier = input("Enter an identifier for the data: ")
    
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

        if not(ic_design in ['A', 'Z', 'ATHENA', 'ZEUS']):
            raise Exception("Invalid die specified")
        else:
            if ic_design == 'ATHENA':
                ic_design = 'A'
            elif ic_design == 'ZEUS':
                ic_design = 'Z'

    else:
        raise Exception("Invalid IC Node")
    
    return folder_path, file_path, identifier, ic_node, ic_design

def get_signature_with_threshold(analysis, identifier, threshold):
    """
        @brief: Get the signature with a specific threshold
        @param threshold: The threshold to use
        @return: The signature with the threshold
    """
    analysis.update_threshold(threshold)
    sig_id = f"{identifier}_threshold={int(threshold * 100)}%"
    analysis.export_all_signatures(sig_id)
    

def main():
    print("Welcome to the PUF Flip Flop Data Analysis Script")
    print("This script will parse the data from the FFMCU files and output the scan chain signatures")
    print("Please provide the path to the folder where the data is stored")

    folder_path, ffmcu_file, identifier, node, die = get_inputs()

    # Parse the data and find the scan chains, and export to a folder called "transposed_chain_data"
    print(f"Parsing the FFMCU file: {ffmcu_file}")
    parser = parse(ffmcu_file, folder_path, identifier)
    parser.parse_and_transpose()

    # Analyze the scan chains in the folder
    parsed_data_folder_path = os.path.join(folder_path, "transposed_chain_data")
    if not os.path.exists(parsed_data_folder_path):
        raise Exception("No transposed_chain_data folder found in the folder")
    else:
        print(f"Analyzing the scan chains in {parsed_data_folder_path}")

    threshold = 1
    analysis = analyze(parsed_data_folder_path, node, die, threshold)
    analysis.compare_scan_chains()
    analysis.calculate_chain_reliability()
    #analysis.visualize_scan_chain(11)

    # These methods will save data in one directory above the transposed_chain_data directory
    analysis.save_scan_chain_graphics(identifier)

    get_signature_with_threshold(analysis, identifier, threshold)
    get_signature_with_threshold(analysis, identifier, 0.99)
    get_signature_with_threshold(analysis, identifier, 0.95)
    get_signature_with_threshold(analysis, identifier, 0.9)
    get_signature_with_threshold(analysis, identifier, 0.8)

    # Compare the scan chains
    #comparison = compare("transposed_scan_chains", identifier)
    #comparison.compare(scan_chain_number=2)

    print("Scan program execution completed.")


if __name__ == "__main__":
    main()

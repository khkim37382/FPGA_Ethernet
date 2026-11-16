import csv
import os
import pandas as pd
import seaborn as sns
import math
import matplotlib.pyplot as plt
import numpy as np


def read_csv(file_path):
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        max_value = 0
        data = []

        # Find the maximum value in the "Zeros Match" and "Ones Match" columns
        for row in csv_reader:
            zeros_match = int(row['Zeros Match'])
            ones_match = int(row['Ones Match'])
            max_value = max(max_value, zeros_match, ones_match)
            data.append((int(row['Address'], 16), int(row['Bit Position']), zeros_match, ones_match))

        return data, max_value

def process_data_for_csv(data, max_value, identifier, folder_name='./'):
    signature_list = []

    reliability = 0

    # Define the threshold for which a value can be included in the signature
    threshold = max_value - 1

    number_of_bits_in_signature = len(data)
    stable_ones = 0
    stable_zeros = 0
    flip_bits = 0

    # Process each row to determine the value for each address and bit position
    for address, bit_position, zeros_match, ones_match in data:
        if zeros_match >= threshold and ones_match == 0:
            value = '0'  # Signature value is 0
            stable_zeros += 1
        elif ones_match >= threshold and zeros_match == 0:
            value = '1'  # Signature value is 1
            stable_ones += 1
        else:
            value = 'X'  # Not included in the signature
            number_of_bits_in_signature -= 1
            flip_bits += 1
    
        # We want to measure the reliability of the signature by the number of times a 1 or 0 
        # appears in the signature relative to the max

        reliability += max(zeros_match, ones_match) / max_value

        # Convert address to hexadecimal format
        hex_address = f"{address:03X}"

        signature_list.append((hex_address, bit_position, value))
    
    reliability = reliability / len(data)

    print(f"Signature derived from {max_value} measurements")
    print(f"Stable 0s: {stable_zeros}\nStable 1s: {stable_ones}\nFlip bits: {flip_bits}")
    print(f"Signature reliability: {reliability*100:.2f}%")
    print(f"Proportion of bits in final signature: {number_of_bits_in_signature/len(data)*100:.2f}%")

    # Write the signature list with values to a CSV file
    file_path = os.path.join(folder_name, f'signature_{identifier}.csv')
    with open(file_path, mode='w', newline='') as signature_file:
        writer = csv.writer(signature_file)
        writer.writerow(['Address', 'Bit Position', 'Value'])
        for item in signature_list:
            writer.writerow(item)

    print(f"Signature CSV file saved to {file_path}")

    return file_path

def create_visualization_from_signature(file_path):
     # Read the signature CSV file
    signature_df = pd.read_csv(file_path)

    color_scheme = input("Select the color scheme:\n1. Tricolor Signature\n2. Discrete Colored Signature\nEnter the number: ")
    while color_scheme not in ['1', '2']:
        color_scheme = input("Invalid selection. Please enter 1 or 2: ")

    # Aggregate data for visualization
    aggregated_data = []
    for _, row in signature_df.iterrows():
        address = f"{int(row['Address'], 16):03X}"  # Convert hex address to string
        bit_position = row['Bit Position']
        if color_scheme == '1':
            value = 0.8 if row['Value'] == '0' else 1 if row['Value'] == '1' else 0
        else:
            value = 1 if row['Value'] in ['0', '1'] else 0
        aggregated_data.append((f"{address},{bit_position}", value))

    # Calculate the size of the square grid
    num_addresses = len(aggregated_data)
    grid_size = int(math.ceil(math.sqrt(num_addresses)))  # Size of the grid

    # Create a square DataFrame for scores and another for addresses
    score_square_df = pd.DataFrame(np.nan, index=range(grid_size), columns=range(grid_size))
    address_square_df = pd.DataFrame("", index=range(grid_size), columns=range(grid_size))

    # Map each address and score to a position in the square grid
    for idx, (address, score) in enumerate(aggregated_data):
        row, col = divmod(idx, grid_size)
        score_square_df.iat[row, col] = score
        address_square_df.iat[row, col] = address

    # Create the heatmap with annotations
    plt.figure(figsize=(10, 10))
    sns.heatmap(score_square_df, cmap='viridis', linewidths=0)  # Adjust font size here    
    plt.title('Signature Visualization from Signature File')
    plt.xlabel('Grid Column')
    plt.ylabel('Grid Row')
    plt.show()

def save_visualization_from_signature(file_path, save_file):
    # Read the signature CSV file
    signature_df = pd.read_csv(file_path)

    # Aggregate data for visualization
    aggregated_data = []
    for _, row in signature_df.iterrows():
        address = f"{int(row['Address'], 16):03X}"  # Convert hex address to string
        bit_position = row['Bit Position']
        value = 0.8 if row['Value'] == '0' else 1 if row['Value'] == '1' else 0
        aggregated_data.append((f"{address},{bit_position}", value))

    # Calculate the size of the square grid
    num_addresses = len(aggregated_data)
    grid_size = int(math.ceil(math.sqrt(num_addresses)))  # Size of the grid

    # Create a square DataFrame for scores and another for addresses
    score_square_df = pd.DataFrame(np.nan, index=range(grid_size), columns=range(grid_size))
    address_square_df = pd.DataFrame("", index=range(grid_size), columns=range(grid_size))

    # Map each address and score to a position in the square grid
    for idx, (address, score) in enumerate(aggregated_data):
        row, col = divmod(idx, grid_size)
        score_square_df.iat[row, col] = score
        address_square_df.iat[row, col] = address

    # Create the heatmap with annotations
    plt.figure(figsize=(10, 10))
    sns.heatmap(score_square_df, cmap='viridis', linewidths=0, annot=False, cbar=False, xticklabels=False, yticklabels=False)
    plt.title('Signature Visualization from Signature File')
    plt.savefig(save_file)
    print(f"Saved signature visualization to {save_file}")

# Main program
if __name__ == "__main__":
    print("Select the mode:\n1. CSV output\n2. Visualize")
    mode_choice = input("Enter the number for the mode you want to use: ")

    if mode_choice == '1':
        file_path = input("Please enter the file path to your CSV: ")
        identifier = input("Please enter an identifier for the output file: ")
        data, max_value = read_csv(file_path)
        process_data_for_csv(data, max_value, identifier)
        print(f"Signature CSV file 'signature_{identifier}.csv' created.")
    elif mode_choice == '2':
        signature_file_path = input("Please enter the file path to your Signature CSV: ")
        create_visualization_from_signature(signature_file_path)
    else:
        print("Invalid mode selected.")
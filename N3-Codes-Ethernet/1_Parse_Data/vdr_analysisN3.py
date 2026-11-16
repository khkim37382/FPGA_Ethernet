import pandas as pd
import numpy as np
import glob
import matplotlib.pyplot as plt
import os
from openpyxl import Workbook
board="A-7.31"

# Define paths
raw_data_path = r"C:\Users\solom\OneDrive\Desktop\Vanderbilt\Graduate\1_Papers\NSREC 26 VDR vs SEU XS\Data\VDR\vdr repeat 3\Z-7.73\Set 3\\"  # Change this to the correct path
processed_data_path = r"C:\Users\solom\OneDrive\Desktop\Vanderbilt\Graduate\1_Papers\NSREC 26 VDR vs SEU XS\Data\VDR\vdr repeat 3\Z-7.73\Set 3\processed\\"

# Define constants

MIN_V = 0.0
MAX_V = 0.55
INC = 0.01
edges = np.arange(MIN_V-(INC/2),MAX_V+(INC/2),INC) #np.linspace(MIN_V, MAX_V, int((MAX_V - MIN_V) / INC) + 1)
line_colors = ["#ff00ff", 'r', "#00ff00", 'b']

# Get list of CSV files
raw_data_files = glob.glob(raw_data_path + '*750*SRAM*.csv')

# Initialize an empty VDR array

# Process each CSV file
for file in raw_data_files:
    file = file.replace("\\","/")
    # Read CSV into DataFrame
    print(file.upper())
    board_name = file.upper().split('RT_')[1].split('_SRAM')[0]
    if(board_name[0] == 'A'):
        if(file.split('SRAM')[-1][0] == '0'):
            NUM_ADDR = 2**13
            NUM_DATA = 64
        else:
            NUM_ADDR = 2**11
            NUM_DATA = 128
    elif(board_name[0] == 'Z'):
        if(file.split('SRAM')[-1][0] == '0'):
            NUM_ADDR = 2**9
            NUM_DATA = 40
        else:
            NUM_ADDR = 2**10
            NUM_DATA = 128
    elif(file.split("RT_")[1].split("-")[0] == 'C21'):
        NUM_ADDR = 1024
        NUM_DATA = 76
    elif(file.split("RT_")[1].split("-")[0] == 'C20'):
        NUM_ADDR = 8192
        NUM_DATA = 32

    input_pattern = file.split('750_')[1].split('_')[0]
    runinfo = file.split('_')
    dose = runinfo[5]
    sramnum = runinfo[-1].upper().replace('.CSV','')
    raw_data = pd.read_csv(file, dtype={'Address': str, 'Error Pattern': str, 'VDD':str})
    NUM_CELLS_TOTAL = NUM_ADDR * NUM_DATA
    vdr_array = np.zeros((NUM_ADDR, NUM_DATA))
    
    # Filter rows where Address and ErrorPattern are not both '0'
    raw_data = raw_data[~raw_data['Time'].str.contains("=")]
    raw_data_no_0_0 = raw_data[(raw_data['Address'].str.lstrip("0") != '') | (raw_data['Error Pattern'] != ("0"*(NUM_DATA//4)))]

    


    # idx2 = []
    # for idx in range(1,raw_data_no_0_0.size):  # Assuming idx2 is where the condition is met
    #    if (raw_data_no_0_0['Address'].values[idx] == '1') & (raw_data_no_0_0['Error Pattern'].values[idx] == '0'):
    #        idx2.append(idx)
    #     ##error_pattern_value = raw_data_no_0_0.at[idx, "ErrorPattern"]
    #    ## print(f"Index {idx} - Address: '{address_value}', ErrorPattern: '{error_pattern_value}'")
    
    # # Iterate through idx2 to adjust VDD between consecutive '1' entries
    # for j in range(1, len(idx2)):
    #     this_1_0 = idx2[j]
    #     last_1_0 = idx2[j - 1]
    #     if this_1_0 > last_1_0+1:
    #         x = raw_data_no_0_0_vdd.values[last_1_0]
    #         raw_data_no_0_0_vdd[last_1_0+1:this_1_0] = x

    # # Update the remaining VDD values after the last '1' entry
    # if idx2[-1] < len(raw_data_no_0_0_vdd) - 1:
    #     raw_data_no_0_0_vdd[idx2[-1] + 1:] = raw_data_no_0_0_vdd.values[idx2[-1]]

    # # Update the original DataFrame's VDD column
    # raw_data_no_0_0['VDD'] = raw_data_no_0_0_vdd

    # Filter the rows where Address is not '1' or ErrorPattern is not '0'
    processed_data = raw_data_no_0_0[(raw_data_no_0_0['Address'].str.lstrip("0") != '1') | (raw_data_no_0_0['Error Pattern'] != ("0"*(NUM_DATA//4)))]
    processed_data = processed_data[processed_data['Error Pattern'] != '0']
    # Remove first 8192 rows
    # processed_data = processed_data.iloc[8192:]

    # Pre-process data to group by address and convert error patterns
    grouped_data = processed_data.groupby('Address')
    address_error_map = {}
    
    for addr, group in grouped_data:
        error_pattern_hex = group['Error Pattern'].tolist()
        pattern_bin_32 = [f"{int(x,16):0{NUM_DATA}b}" for x in error_pattern_hex]
        address_error_map[addr[-4:]] = (group['VDD'].values, pattern_bin_32)

    # Iterate through the address space
    for i in range(NUM_ADDR):
        addr_hex = f'{i:04x}'
        if addr_hex not in address_error_map:
            continue
        
        vdd_values, pattern_bin_32 = address_error_map[addr_hex]
        
        for j in range(NUM_DATA):
            error_threshold = 1 << j
            cur_bit_indices = [idx for idx, val in enumerate(pattern_bin_32) if int(val, 2) & error_threshold > 0]
            
            if cur_bit_indices:
                cur_bit_vdr = np.max(vdd_values[cur_bit_indices])  # Using np.max instead of max to handle arrays
            else:
                cur_bit_vdr = np.nan
            
            vdr_array[i, j] = cur_bit_vdr

    # Create a DataFrame with the numerical index as the first column
    index_column = np.arange(NUM_ADDR)  # Numerical index from 0 to NUM_ADDR-1

    vdr_array_no_nan = np.nan_to_num(vdr_array, nan=0)

    vdr_df = pd.DataFrame(vdr_array_no_nan, columns=[f'Data_{j}' for j in range(NUM_DATA)])
    vdr_df.insert(0, 'Index', index_column)  # Insert the numerical index as the first column

    #---------------
    counts, bin_edges = np.histogram(vdr_array_no_nan.flatten(), bins=edges)

    # Compute bin centers
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Create Excel file
    wb = Workbook()
    ws = wb.active
    ws.title = "Histogram Data"

    # Write headers
    ws.append(["vdr value", "number of cells"])

    # Write each bin center + count
    for x, y in zip(bin_centers, counts):
        ws.append([float(x), int(y)])
    output_file_name = processed_data_path + 'histogram_' + (file.split('/')[-1]).split('.')[0] + (file.split('/')[-1]).split('.')[1] + '.xlsx'
    wb.save(output_file_name)

    #---------------------


    # Save the processed VDR data with the numerical index
    os.makedirs(os.path.dirname(processed_data_path), exist_ok=True)
    out_file_name = processed_data_path + file.split("/")[-1].replace("processed", "Vdr")
    vdr_df.to_csv(out_file_name, index=False)

    num_error_bits = int(np.sum(vdr_array > 0))
    percent_bit_err = num_error_bits / NUM_CELLS_TOTAL * 100
    
    # Create histogram
    # plt.figure(figsize=(3.5,5))
    plt.hist(vdr_array.flatten(), bins=edges, color=line_colors[0], edgecolor='white', linewidth=2)
    


    vdr_array = np.nan_to_num(vdr_array, nan=0)
    mean_vdr = float(np.sum(vdr_array)) / num_error_bits if num_error_bits > 0 else 0

    plt.ylim([0, NUM_CELLS_TOTAL/4])
    
    # Plot annotations
    title_text = f"{board_name}, Input {input_pattern}, Dose {dose}, {sramnum} VDR Dist"
    plt.title(title_text, fontsize=24)
    plt.xlabel("VDR (V)", fontsize=34, fontweight='bold')
    plt.ylabel("# of Cells", fontsize=34, fontweight='bold')
    
    # Add mean VDR text
    txt = f"mean VDR = {mean_vdr:.3f}"
    ax = plt.gca()
    ax.text(0.4, 0.8, txt, transform=ax.transAxes, fontsize=18)

    txt = f"Fail % =  {percent_bit_err:.1f}"
    ax = plt.gca()
    ax.text(0.4, 0.7, txt, transform=ax.transAxes, fontsize=18)
    
    # Customize axis
    ax.tick_params(axis='both', which='major', labelsize=22)
    plt.grid(True)
    
    # Save the figure
    out_file_name = processed_data_path + file.split('/')[-1].replace(".csv", "") + ".png"
    plt.savefig(out_file_name, bbox_inches='tight')
    plt.close()

    # Reset vdr_array for the next file
    vdr_array.fill(0)

    # Save processed data to a new CSV file
    output_file_name = processed_data_path + 'processed_' + file.split('/')[-1]
    processed_data.to_csv(output_file_name, index=False, quoting=1)  # quoting=1 ensures quotes around strings

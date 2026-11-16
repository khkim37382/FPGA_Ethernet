import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


class ScanChainAnalysis:
    def __init__(self, folder_path, node, die, threshold):
        """
            @description Initialize the TallyScanChains object
            @param folder_path - the path to the folder containing the parsed scan chain data
            @param node - the technology node (3nm, 5nm, 7nm etc.)
            @param die - the die configuration (specific to the technology node and the product)

            @return Initialized TallyScanChains object
        """
        self.folder_path = folder_path
        self.node = node
        self.die = die
        self.threshold = threshold
        self.chain_lengths = self.get_scan_chain_lengths(node, die)
        # Initialize the SR bit position counts dictionary
        self.sr_ones_count_at_bit_pos = {}

    def get_scan_chain_lengths(self, node, die):
        """
            @description Get the scan chain lengths for the given node and die configuration
            @param node - the technology node (3nm, 5nm, 7nm etc.)
            @param die - the die configuration (specific to the technology node and the product)

            @modifies self.chain_lengths : updates the scan chain lengths for the given node and die configuration

        """
        # Mapping of node and die configurations to constant arrays-- note that SR 0 is at the end of the array
        config_to_array = {
            ###          59,58,57,56,55,54,53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0
            ('N3', 'A'): [2, 1, 1, 1, 3, 3, 2, 1, 4, 4, 1, 4, 4, 2, 2, 3, 2, 1, 4, 4, 4, 4, 3, 5, 5, 1, 6, 6, 4, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 2, 6, 6, 6, 2, 1, 1, 2, 2, 2, 1, 2, 2, 2, 2, 1, 1, 4, 1, 4, 4],
            ('N3', 'Z'): [1, 4, 1, 4, 2, 6, 1, 1, 2, 1, 1, 2, 2, 2, 1, 1, 1, 2, 2, 1, 2, 1, 2, 2, 5, 4, 4, 4, 2, 2, 2, 2, 1, 2, 1, 1, 4, 4, 4, 2, 1, 1, 1, 2, 2, 4, 3, 3, 2, 2, 6, 2, 4, 2, 1, 0, 4, 4, 1, 4],
            ('N5', 'C20'): [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 4, 1, 1, 4, 2, 1, 2, 1, 2, 4, 2, 2, 2, 3, 1, 3, 1, 1, 2, 2, 4, 1, 1, 1, 1, 1, 4, 4],
            ('N5', 'C21'): [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 4, 4, 1, 4, 1, 1, 4, 2, 1, 2, 4, 1, 4, 2, 1, 4, 4, 1, 1, 1, 2, 2, 1, 1, 2, 4, 4, 4]
        }
        multipliers = config_to_array.get((node, die), None)
        if multipliers is None:
            return None

        chain_length_base_multiplier = 8192
        return [((chain_length_base_multiplier * multiplier)) for multiplier in multipliers]

    def compare_scan_chains(self):
        """
            @description Compare the scan chains in the given folder and tallies the count of 1's at each bit position for each SR number
            @modifies self.sr_ones_count_at_bit_pos - the count of 1's at each bit position for each SR number
            @modifies self.number_of_chains - the number of scan chains in the folder
            @return None
        """
        # Check to make sure our scan chain lengths are defined
        if self.chain_lengths is None:
            raise ValueError(f"No stop values defined for node {self.node} and die {self.die}")

        # Initialize SR bit counts and chain counts
        self.sr_ones_count_at_bit_pos = [[0] * stop_value for stop_value in self.chain_lengths]

        # Process each file in the folder
        self.number_of_chains = 0

        for file_name in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, file_name)
            if file_path.endswith('.csv'):
                self.number_of_chains += 1
                self.process_file(file_path)
            
    def process_file(self, file_path):
        """ 
            @description Process the given file and update the count of 1's at each bit position for each SR number
            @param file_path - the path to the file to process
            @modifies self.sr_ones_count_at_bit_pos - the count of 1's at each bit position for each SR number
            @return None
        """
        try:
            df = pd.read_csv(file_path)
            if not list(df.columns) == ['SR Number', 'Scan Chain Data']:
                raise ValueError(f"Incorrect file type in folder: {os.path.basename(file_path)}")

            # Process each SR number in the file
            for _, row in df.iterrows():
                sr_number = int(row['SR Number'])
                if sr_number < len(self.chain_lengths):
                    scan_chain_data = row['Scan Chain Data']
                    # Only up to the stop value for the given SR number
                    for bit_position, bit in enumerate(scan_chain_data):
                        if bit == '1' and bit_position < self.chain_lengths[sr_number]:
                            self.sr_ones_count_at_bit_pos[sr_number][bit_position] += 1
        except Exception as e:
            print(f"Error processing file {os.path.basename(file_path)}: {e}")

    def calculate_chain_reliability(self):
        """
            @description Calculate the reliability of each SR chain
            @modifies self.reliability_measure - the reliability of each SR chain
        """

        # Define an output structure that stores a reliability score for each SR and bit position combination
        self.reliability_measure = [[0] * stop_value for stop_value in self.chain_lengths]
        self.sr_prediction_values = [[0] * stop_value for stop_value in self.chain_lengths]

        for sr_number, counts in enumerate(self.sr_ones_count_at_bit_pos):
            for bit_position, count in enumerate(counts):
                if count < self.number_of_chains / 2:
                    self.sr_prediction_values[sr_number][bit_position] = 0
                    self.reliability_measure[sr_number][bit_position] = 1 - (count / self.number_of_chains)
                else:
                    self.sr_prediction_values[sr_number][bit_position] = 1
                    self.reliability_measure[sr_number][bit_position] = count / self.number_of_chains
    
    def print_chain_data(self):
        # For reach SR, print the length, then the number of chains we compared, then the
        # minimum, maximum, and average reliability

        output = ""

        #for sr_number, counts in self.sr_ones_count_at_bit_pos.items():
        for sr_number, counts in enumerate(self.sr_ones_count_at_bit_pos):
            temp_output = f"SR{sr_number} - Length: {self.chain_lengths[sr_number]}\n"
            if not(counts):
                temp_output += "\tEmpty chain\n"
            else:
                temp_output += f"\tNumber of chains: {self.number_of_chains}\n"
                temp_output += f"\tMin reliability: {min(self.reliability_measure[sr_number])}\n"
                temp_output += f"\tMax reliability: {max(self.reliability_measure[sr_number])}\n"
                temp_output += f"\tAverage reliability: {sum(self.reliability_measure[sr_number]) / len(self.reliability_measure[sr_number])}\n"
                temp_output += "\n"

            print(temp_output)
            output += temp_output

    def save_results(self, output_file):
        # Save the SR bit counts to a CSV file
        with open(output_file, 'w') as f:
            # The header should be the SR number and the bit positions up to maximum stop value
            f.write("SR Number, Bit: " + ", Bit: ".join(map(str, range(max(self.chain_lengths)))) + "\n")

            for sr_number, counts in self.sr_ones_count_at_bit_pos.items():
                f.write(f"SR{sr_number},{','.join(map(str, counts))}\n")

    def visualize_scan_chain(self, sr_num):
        """
        @description Visualize the scan chain data for the given SR number
        @param sr_num - the SR number to visualize
        @return None
        """

        # Create a heatmap with SR bit position vs reliability measure. Organize the heat map into rows of 256 bits
        heatmap_data = []
        yticklabels = []

        for i in range(0, self.chain_lengths[sr_num], 256):
            heatmap_data.append(self.reliability_measure[sr_num][i:i+256])

            # Skip every other label to make the plot more readable
            if i % 1024 == 0:
                yticklabels.append(str(i))
            else: 
                yticklabels.append('')

        # Create x tick labels and add a label every 64 bits, otherwise use ''
        xticklabels = [str(i) if i % 32 == 0 else '' for i in range(256)]
            
        # Convert heatmap_data to a NumPy array with a numeric type
        heatmap_data = np.array(heatmap_data, dtype=float)

        plt.figure(figsize=(10, 6))
        sns.heatmap(heatmap_data, cmap='viridis', linewidths=.5, annot=False, cbar=False, xticklabels=xticklabels, yticklabels=yticklabels)
        plt.title(f'Heat Map of Reliability Measure for SR{sr_num}')
        plt.show()

    def get_sr_scan_chain_results(self, sr_num):
        """
        @description Get the scan chain data for the given SR number
        @param sr_num - the SR number to get the scan chain data for
        @return The scan chain data for the given SR number
        """
        return self.sr_prediction_values[sr_num], self.reliability_measure[sr_num]  
    
    def update_threshold(self, threshold):
        """
        @description Update the threshold for valid signatures
        @param threshold - the threshold for valid signatures
        @return None
        """
        self.threshold = threshold

    def get_sr_signature(self, sr_num):
        """
        @description Get the SR signature for the given SR number
        @param sr_num - the SR number to get the SR signature for
        @return The SR signature for the given SR number
        """
        
        # Create an array of length equal to the stop value for the given SR number
        signature = [0] * self.chain_lengths[sr_num]
        
        for bitpos, bit in enumerate(self.sr_prediction_values[sr_num]):
            if self.reliability_measure[sr_num][bitpos] > self.threshold:
                signature[bitpos] = str(bit)
            else:
                signature[bitpos] = 'X'
        
        return signature
    
    def export_all_signatures(self, identifier):
        """
        @description Export the SR signatures to a CSV file called sr_signatures_{identifier}.csv
                     includes the SR number, average reliability per SR, and the SR signature
        @return None
        """
        # Create a dataframe with the SR signatures
        sr_signatures = []
        for sr_num in range(len(self.chain_lengths)):
            concat_sig = ''.join(self.get_sr_signature(sr_num))
            sr_signatures.append(concat_sig)

        # Create a dataframe with the SR signatures
        df = pd.DataFrame()
        df['SR Number'] = range(len(self.chain_lengths))
        if not self.reliability_measure:
            self.calculate_chain_reliability()
        
        # Check to see if the SR is valid (if the scan chain length is 0 we skip it)
        #df['Average Reliability'] = [sum(self.reliability_measure[sr_num]) / len(self.reliability_measure[sr_num]) for sr_num in range(len(self.chain_lengths))]
        for sr_num in range(len(self.chain_lengths)):
            if self.chain_lengths[sr_num] == 0:
                df.at[sr_num, 'Average Reliability'] = np.nan
            else:
                df.at[sr_num, 'Average Reliability'] = sum(self.reliability_measure[sr_num]) / len(self.reliability_measure[sr_num])

        df['SR Signature'] = sr_signatures

        # Save the dataframe to a CSV file
        file_path = f'sr_signatures_{identifier}.csv'

        file_path = os.path.join(self.folder_path, '../', file_path)
        df.to_csv(file_path, index=False)

    def save_scan_chain_graphics(self, identifier):
        # Save the scan chain graphics to a file
        # Same as visualize scan chain, but instead of showing the plot just save the image
        # Repeat for all of the scan chains in the folder

        # Set the path to save the graphics as ../scan_chain_graphics/[file]
        folder_path = os.path.join(self.folder_path, '../', 'scan_chain_graphics')
        try:
            os.mkdir(folder_path)
        except FileExistsError:
            # empty the existing folder if its already there
            for file in os.listdir(folder_path):
                os.remove(os.path.join(folder_path, file))
        
        for count in range(len(self.chain_lengths)):

            heatmap_data = []
            yticklabels = []

            sr = len(self.chain_lengths) - count - 1

            # Create file name and path
            file_name = f'scan_chain_graphics_SR{sr}_{identifier}.png'
            file_path = os.path.join(folder_path, file_name)

            for i in range(0, self.chain_lengths[sr], 256):
                heatmap_data.append(self.reliability_measure[sr][i:i+256])

                # Skip every other label to make the plot more readable
                if i % 2048 == 0:
                    yticklabels.append(str(i))
                else: 
                    yticklabels.append('')

            # Create x tick labels and add a label every 64 bits, otherwise use ''
            xticklabels = [str(i) if i % 32 == 0 else '' for i in range(256)]
                
            # Convert heatmap_data to a NumPy array with a numeric type
            heatmap_data = np.array(heatmap_data, dtype=float)

            # Adjust figure height based on the length of the scan chain
            # The scan chain is a multiple of 8192 bits, so we can use that to scale the figure height
            fig_width = 20
            fig_height = 5 + (self.chain_lengths[sr] // 8192)
            plt.figure(figsize=(fig_width, fig_height))
            sns.heatmap(heatmap_data, cmap='viridis', linewidths=.5, annot=False, cbar=True, xticklabels=xticklabels, yticklabels=yticklabels)
            plt.title(f'Heat Map of Reliability Measure for SR{sr}')
            plt.savefig(file_path)
            plt.close()


if __name__ == '__main__':

    folder_path = input("Enter the folder path: ")

    #identifier = input("Enter the identifier for this data: ")
    identifier = "no_id"

    node = 'N3'
    die = 'A'

    comparator = ScanChainAnalysis(folder_path, node, die, threshold=0.9)
    comparator.compare_scan_chains()
    comparator.calculate_chain_reliability()
    #comparator.visualize_scan_chain(11)
    #print(comparator.get_sr_signature(11))
    comparator.save_scan_chain_graphics(identifier)
    comparator.export_all_signatures(identifier)

    #Formulate the file name as per the given identifier: aggregated_scan_chain_<identifier>.csv
    #file_name = f'aggregated_scan_chain_{identifier}.csv'
    #comparator.save_results(file_name)

import pandas as pd
import os

class ScanChainParser:
    def __init__(self, file_path, folder, identifier):
        self.file_path = file_path
        self.folder = folder
        self.identifier = identifier

    def parse_and_transpose(self):
        # Read the CSV file
        df = pd.read_csv(self.file_path)

        # Find the maximum SR number across all chunks (should be around 49151 for a full N3 scan chain)
        # This is not the same as the physical SR number, but rather the length of the scan chain
        max_sr = df['SR'].max()

        # Split the dataset into chunks based on the SR column resetting to 0
        chunks = []
        start_index = 0
        for i in range(1, len(df)):
            if df.iloc[i]['SR'] < df.iloc[i - 1]['SR']:
                chunks.append(df.iloc[start_index:i])
                start_index = i
        chunks.append(df.iloc[start_index:])  # Add the last chunk

        # Print the number of found chunks
        print(f'Found {len(chunks)} chunks of data')

        # Create a folder called "transposed_chain_data" to store the transposed data
        new_folder_path = os.path.join(self.folder, 'transposed_chain_data')

        try:
            # Make the directory within ght folder
            os.mkdir(new_folder_path)
        except FileExistsError:
            # empty the existing folder if its already there
            for file in os.listdir(new_folder_path):
                os.remove(os.path.join(new_folder_path, file))

        # Process each chunk and save to a separate CSV file
        num_srs = len(chunks[0].iloc[0]['Error Count']) - 1

        print(f'Found {num_srs} SRs in the scan chain')

        chunk_counter = 0
        for chunk in chunks:
            # Check if the chunk contains all SR numbers from 0 to the absolute max SR
            if set(chunk['SR']) == set(range(max_sr + 1)):
                transposed_chunk = self.transpose_chunk(chunk, num_srs)
                file_name = f'scan_chain_{self.identifier}_{chunk_counter}.csv'
                file_name = os.path.join(new_folder_path, file_name)

                transposed_chunk.to_csv(file_name, index=False)
                print(f'Saved: {file_name}')
            else:
                print(f'Discarded incomplete chunk {chunk_counter}')
            
            chunk_counter += 1

    def transpose_chunk(self, chunk, num_srs):
        # Initialize the dataframe with SR Number and Scan Chain Data columns
        transposed_df = pd.DataFrame(columns=['SR Number', 'Scan Chain Data'])
        transposed_df['SR Number'] = range(len(chunk.iloc[0]['Error Count']))

        # Get the number of SRs as the length of the error count

        # Transpose the Error Count column into the Scan Chain Data column
        row_counter = 0

        for _, row in chunk.iterrows():
            for i, bit in enumerate(row['Error Count']):
                if pd.isna(transposed_df.at[num_srs - i, 'Scan Chain Data']):
                    transposed_df.at[num_srs - i, 'Scan Chain Data'] = bit
                else:
                    transposed_df.at[num_srs - i, 'Scan Chain Data'] += bit
            row_counter += 1
            print(f'Processed row {row_counter}', end='\r')

        return transposed_df

if __name__ == '__main__':
    file_path = input("Enter the name of the file: ")
    folder = input("Enter the folder path: ")
    identifier = input("Enter the identifier for this data: ")

    parser = ScanChainParser(file_path, folder, identifier)
    parser.parse_and_transpose()

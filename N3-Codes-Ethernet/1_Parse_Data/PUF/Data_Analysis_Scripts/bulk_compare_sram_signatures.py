import Data_Analysis_Scripts.signature_comparison as sig_comp
import itertools
import os
import csv

def find_signature_files(directory):
    signature_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv") and "signature" in file:
                signature_files.append(os.path.join(root, file))
    return signature_files

def compare_all_signatures(signature_files):
    uniqueness_matrix = {}
    for file1, file2 in itertools.combinations(signature_files, 2):
        uniqueness = sig_comp.compare_signatures(file1, file2)
        basename1, basename2 = os.path.basename(file1), os.path.basename(file2)
        if basename1 not in uniqueness_matrix:
            uniqueness_matrix[basename1] = {}
        if basename2 not in uniqueness_matrix:
            uniqueness_matrix[basename2] = {}
        uniqueness_matrix[basename1][basename2] = uniqueness
        uniqueness_matrix[basename2][basename1] = uniqueness
    return uniqueness_matrix

def write_to_csv(uniqueness_matrix, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        header = [''] + list(uniqueness_matrix.keys())
        writer.writerow(header)
        # Write rows
        for file1 in uniqueness_matrix:
            row = [file1]
            for file2 in header[1:]:
                if file1 == file2:
                    row.append('')  # Leave diagonal cells empty
                else:
                    row.append(uniqueness_matrix[file1].get(file2, ''))
            writer.writerow(row)

def main():
    directory = input("Enter the directory path containing the signature files: ")
    identifier = input("Enter the output CSV file identifier: ")

    signature_files = find_signature_files(directory)
    uniqueness_matrix = compare_all_signatures(signature_files)

    output_file = f"SRAM_uniqueness_matrix_{identifier}.csv"
    write_to_csv(uniqueness_matrix, output_file)

    print(f"Results have been written to {output_file}")

if __name__ == "__main__":
    main()
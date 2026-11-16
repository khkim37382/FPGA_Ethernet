import pandas as pd

class ScanChainComparison:
    def __init__(self, scan_chain_sig_1, scan_chain_sig_2):
        self.scan_chain_1 = scan_chain_sig_1
        self.scan_chain_2 = scan_chain_sig_2

    def compare(self, scan_chain_number):

        first_compare_chain = self.scan_chain_1[scan_chain_number]
        second_compare_chain = self.scan_chain_2[scan_chain_number]

        # Check the sig lengths are the same
        if len(first_compare_chain) != len(second_compare_chain):
            raise Exception("Scan chain lengths are not the same")

        # Compare the scan chains
        match_counter = 0
        valid_sig_bits = 0

        for i in range(len(first_compare_chain)):
            match_counter += 1 if first_compare_chain[i] == second_compare_chain[i] else 0
            if first_compare_chain[i] != 'X' and second_compare_chain[i] != 'X' and first_compare_chain[i] != second_compare_chain[i]:
                print(f"Error at bit {i}: {first_compare_chain[i]} != {second_compare_chain[i]}")

            if first_compare_chain[i] == 'X' or second_compare_chain[i] != 'X':
                valid_sig_bits += 1

        print(f"Matched {match_counter} bits out of {valid_sig_bits} valid bits")
        print(f"Matched {match_counter / valid_sig_bits * 100}% of signature bits")

        print(f"Matched {match_counter} bits out of {len(first_compare_chain)} total scan chain bits")
        print(f"Matched {match_counter / len(first_compare_chain) * 100}% of scan chain bits")


if __name__ == "__main__":

    file_one = input("Enter the first scan chain signature file path: ")
    file_two = input("Enter the second scan chain signature file path: ")

    # Read CSVs, the first column is SR Number, the second is Average Reliability, the third is the SR Signature
    # Compare the signatures across the two files for each SR Number

    df1 = pd.read_csv(file_one)
    df2 = pd.read_csv(file_two)

    scan_chain_sig1 = df1['SR Signature']
    scan_chain_sig2 = df2['SR Signature']

    comparison = ScanChainComparison(scan_chain_sig1, scan_chain_sig2)
    comparison.compare(scan_chain_number=2)


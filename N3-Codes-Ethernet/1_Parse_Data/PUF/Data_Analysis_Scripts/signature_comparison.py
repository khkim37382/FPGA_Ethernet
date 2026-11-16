import csv

def compare_signatures(file_path1, file_path2):
    # Initialize variables
    signature_one_depth = 0
    signature_two_depth = 0

    same_signature_addresses = 0
    signature_matches = 0

    # Open the first file and read its contents
    with open(file_path1, 'r') as file1:
        reader1 = csv.reader(file1)
        next(reader1)  # Skip the header

        # Open the second file and read its contents
        with open(file_path2, 'r') as file2:
            reader2 = csv.reader(file2)
            next(reader2)  # Skip the header

            # Iterate through both files simultaneously
            for row1, row2 in zip(reader1, reader2):
                # Check if the values in both rows are not 'X'
                if row1[2] != 'X':
                    signature_one_depth += 1
                if row2[2] != 'X':
                    signature_two_depth += 1

                # Compare values if none of them is 'X'
                if row1[2] != 'X' and row2[2] != 'X':
                    same_signature_addresses += 1

                    if row1[2] == row2[2]:
                        signature_matches += 1
                    

    # Calculate % uniqueness
    if signature_one_depth > 0 and signature_two_depth > 0:
        # Number of matches divided by the number of the bits in the signature
        uniqueness = (1-(signature_matches / min(signature_one_depth, signature_two_depth))) * 100
        print(f"There was {((1-(signature_matches/same_signature_addresses)) * 100):.2f}% uniqueness between addresses present in both signatures")
        #print(f"There were {signature_matches} bits which matched between the signatures, and {min(signature_one_depth, signature_two_depth)} bits in the smallest signature.")
    else:
        uniqueness = 0

    return uniqueness

if __name__ == '__main__':
    # Get the paths to the signature files
    file_path1 = input("Enter the path to the first signature file: ")
    file_path2 = input("Enter the path to the second signature file: ")

    # Compare the signatures
    uniqueness = compare_signatures(file_path1, file_path2)

    # Print the result
    print(f"Signature uniqueness: {uniqueness:.2f}%")
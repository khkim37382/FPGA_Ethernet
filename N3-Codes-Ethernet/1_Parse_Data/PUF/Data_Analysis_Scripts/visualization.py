import pandas as pd
import math
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_and_process_data(file_path):
    df = pd.read_csv(file_path)

    # This is how we assign a score to a given address
    df['Score'] = df[['Zeros Match', 'Ones Match']].max(axis=1)

    df['Address Int'] = df['Address'].apply(lambda x: int(x, 16))
    return df

def create_scatterplot(df):
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='Address Int', y='Bit Position', size='Score', hue='Score', palette='viridis', legend=False)
    plt.title('Scatterplot of Scores by Address and Bit Position')
    plt.xlabel('Address (as integer)')
    plt.ylabel('Bit Position')
    plt.grid(True)
    plt.show()

def create_heatmap(df):
    # Preparing data for heatmap
    heatmap_data = df.pivot(index="Address", columns="Bit Position", values="Score")
    heatmap_data = heatmap_data.fillna(0)

    # Creating the heatmap without annotations
    plt.figure(figsize=(10, 6))  # Adjust the figure size as needed
    sns.heatmap(heatmap_data, cmap='viridis', linewidths=.5, annot=False)
    plt.title('Heat Map of Scores by Address and Bit Position')
    plt.xlabel('Bit Position')
    plt.ylabel('Address')
    plt.show()

def create_aggregated_heatmap(df):
    # Aggregate scores by address
    aggregated_data = df.groupby('Address')['Score'].sum().reset_index()

    # Calculate the size of the square grid
    num_addresses = len(aggregated_data)
    grid_size = int(math.ceil(math.sqrt(num_addresses)))  # Size of the grid

    # Create a square DataFrame for scores and another for addresses
    score_square_df = pd.DataFrame(np.nan, index=range(grid_size), columns=range(grid_size))
    address_square_df = pd.DataFrame("", index=range(grid_size), columns=range(grid_size))

    # Map each address and score to a position in the square grid
    for idx, (address, score) in enumerate(aggregated_data.itertuples(index=False)):
        row, col = divmod(idx, grid_size)
        score_square_df.iat[row, col] = score
        address_square_df.iat[row, col] = address

    # Create the heatmap with annotations
    plt.figure(figsize=(10, 10))
    sns.heatmap(score_square_df, cmap='viridis', linewidths=.5, 
                annot=False)  # Adjust font size here    
    plt.title('Aggregated Heat Map of Scores by Address')
    plt.xlabel('Grid Column')
    plt.ylabel('Grid Row')
    plt.show()

def save_aggregated_heatmap(df, file_path):
    # Aggregate scores by address
    aggregated_data = df.groupby('Address')['Score'].sum().reset_index()

    # Calculate the size of the square grid
    num_addresses = len(aggregated_data)
    grid_size = int(math.ceil(math.sqrt(num_addresses)))  # Size of the grid

    # Create a square DataFrame for scores and another for addresses
    score_square_df = pd.DataFrame(np.nan, index=range(grid_size), columns=range(grid_size))
    address_square_df = pd.DataFrame("", index=range(grid_size), columns=range(grid_size))

    # Map each address and score to a position in the square grid
    for idx, (address, score) in enumerate(aggregated_data.itertuples(index=False)):
        row, col = divmod(idx, grid_size)
        score_square_df.iat[row, col] = score
        address_square_df.iat[row, col] = address

    # Create the heatmap with annotations
    # Remove ticks and labels
    plt.figure(figsize=(10, 10))
    sns.heatmap(score_square_df, cmap='viridis', linewidths=.5, annot=False, cbar=False, xticklabels=False, yticklabels=False)
    plt.title('Aggregated Heat Map of Scores by Address')
    plt.savefig(file_path)

def main():
    # Replace 'your_data.csv' with the path to your dataset file
    file_path = 'output_dataset.csv'
    df = load_and_process_data(file_path)

    # Create and display the scatterplot
    #create_scatterplot(df)

    # Create and display the heatmap with or without smoothing
    #create_heatmap(df)

    # Create and display the aggregated heatmap
    create_aggregated_heatmap(df)

if __name__ == "__main__":
    main()


from pyparsing.util import line
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

def main():
    # Load the CSV file
    csv_path = Path(__file__).parent / "output" / "live_cell_count_2_3_0_5.csv"
    data = pd.read_csv(csv_path)

    # Plot the data
    plt.figure(figsize=(10, 6))
    plt.plot(data['Iteration'], data['Live Cell Count'], marker='.', linestyle=' ')
    plt.title('Número de células vivas por iteración')
    plt.xlabel('Iteración')
    plt.ylabel('Número de células vivas')
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
from pathlib import Path

import matplotlib.pyplot as plt

import pickle as p

from trainer import get_logger_name

import pandas as pd

if __name__ == "__main__":
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]

    for name_dataset in names:
        plt.figure(figsize=(10,10))
        learning_rates = [0.1, 0.01, 0.001, 0.0001, 0.00001]

        files = ([get_logger_name(name_dataset, use_cocob=True)]
                 + [get_logger_name(name_dataset, use_cocob=False, learning_rate=l) for l in learning_rates])

        for file in files:
            try:
                with open(f"results/{file}", 'rb') as handle:
                    acc = p.load(handle)

                plt.plot(acc, label=file)
            except Exception as e:
                print(f"File {file} not found {e}")

        plt.title(name_dataset)
        plt.legend()
        plt.show()

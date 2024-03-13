from pathlib import Path

import matplotlib.pyplot as plt

import pickle as p

from trainer import get_logger_name

import pandas as pd


def plot_data(file, color, label):
    try:
        with open(f"results/{file}", 'rb') as handle:
            acc = p.load(handle)

        if label:
            plt.plot(acc, label=file, color=color)
        else:
            plt.plot(acc, color=color)
    except Exception as e:
        print(f"File {file} not found {e}")


if __name__ == "__main__":
    print(get_logger_name("a", use_cocob=True))

    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]

    max_num_seeds = 100
    colors=['b', 'r', 'g', 'm', 'y', 'k']

    for name_dataset in names:
        plt.figure(figsize=(10,10))
        learning_rates = [0.1, 0.01, 0.001, 0.0001, 0.00001]

        files = ([get_logger_name(name_dataset, use_cocob=True)]
                 + [get_logger_name(name_dataset, use_cocob=False, learning_rate=l) for l in learning_rates])

        color_idx = 0
        for seed in range(max_num_seeds):
            name_dataset_seed = f"{name_dataset}_{seed}"
            plot_data(get_logger_name(name_dataset, use_cocob=True), colors[color_idx])

        for l in learning_rates:
            for seed in range(max_num_seeds):
                name_dataset_seed = f"{name_dataset}_{seed}"
                plot_data(get_logger_name(name_dataset, use_cocob=False, learning_rate=l), colors[color_idx])
            color_idx+=1

        plt.title(name_dataset)
        plt.legend()
        plt.show()

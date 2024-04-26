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
    names = ["ElectricDevices", "ECG5000", "ChlorineConcentration", "Crop", "ECGFiveDays"]

    max_num_seeds = 100
    seed_offset = 0
    colors=['b', 'r', 'g', 'm', 'y', 'k']

    for name_dataset in names:
        plt.figure(figsize=(10,10))
        learning_rates = [0.001]  #[0.1, 0.01, 0.001, 0.0001, 0.00001]

        color_idx = 0
        for l in learning_rates:
            for seed in range(max_num_seeds):
                name_dataset_seed = f"{name_dataset}_{seed}"
                label = get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=l)
                plot_data(get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=l), colors[color_idx], label=seed==0)
            color_idx += 1

        """for seed in range(seed_offset, seed_offset + max_num_seeds):
            name_dataset_seed = f"{name_dataset}_{seed}"
            label = get_logger_name(name_dataset_seed, use_cocob=True)
            plot_data(get_logger_name(name_dataset_seed, use_cocob=True), colors[color_idx], label=seed==0)"""

        plt.title(name_dataset)
        plt.legend()
        plt.show()

from pathlib import Path

import matplotlib.pyplot as plt

import pickle as p

import numpy as np

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


def load_data(name_dataset, use_rocket, lr):
    file = get_logger_name(name_dataset, use_cocob=False, learning_rate=lr, use_rocket=use_rocket)
    try:
        with open(f"results/{file}", 'rb') as handle:
            acc = p.load(handle)
        return acc
    except:
        return None


def get_final_accuracy(name_dataset, use_rocket, lr):

    acc_evaluation = load_data(name_dataset + "_eval", use_rocket, lr)
    acc_test = load_data(name_dataset + "_test", use_rocket, lr)

    if acc_evaluation is None:
        return False, None

    return True, acc_test[np.argmax(acc_evaluation)]


def plot_comparison_entire_dataset():
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]
    results = []
    distance_to_boundary = []
    boundary = np.array([1.0, 1.0])
    boundary /= np.linalg.norm(boundary)
    boundary_ort = np.array([-1.0, 1.0])
    boundary_ort /= np.linalg.norm(boundary_ort)

    for n in names:
        for i in range(10):
            name_dataset_seed = f"{n}_{i}"
            succ_rocket, acc_rocket = get_final_accuracy(name_dataset_seed, True, 0.001)
            succ_nn, acc_nn = get_final_accuracy(name_dataset_seed, False, 0.001)
            if succ_nn and succ_rocket:
                results.append([acc_rocket, acc_nn])

                a = np.array([acc_rocket, acc_nn]) - boundary * np.dot(np.array([acc_rocket, acc_nn]), boundary)
                #distance_to_boundary.append(np.dot(boundary_ort, a.flatten()))
                distance_to_boundary.append(acc_nn/acc_rocket)

    results = np.array(results)
    plt.scatter(results[:, 0], results[:, 1])
    plt.plot([0, 1], [0, 1], 'k')

    print(np.sum(results[:, 0] > results[:, 1]) / len(results[:, 1]))

    data = {"accRocket": results[:, 0]*100, "accNN": results[:, 1]*100, "distanceBoundary": distance_to_boundary}
    df = pd.DataFrame(data)
    df.to_csv("results/plots/ComparisonNNROCKET.csv")

    plt.show()

if __name__ == "__main__":
    #plot_comparison_entire_dataset()
    #exit(0)

    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")

    names = data["Name"]
    #names = ["ElectricDevices", "NonInvasiveFetalECGThorax2", "Crop", "ChlorineConcentration"]
    names = ["FaceAll"]

    lr = 0.001

    max_num_seeds = 100
    seed_offset = 0
    colors=['b', 'r', 'g', 'm', 'y', 'k']
    seed = 0
    for name_dataset in names:
        plt.figure(figsize=(4,4))
        learning_rates = [0.001]
        color_idx = 0
        for i in range(0,10):
            name_dataset_seed = f"{name_dataset}_{i}_test"
            label = get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=lr, use_rocket=True)
            plot_data(label, colors[color_idx], label=label)
        color_idx += 1
        for i in range(0,10):
            name_dataset_seed = f"{name_dataset}_{i}_test"
            label = get_logger_name(name_dataset_seed, use_cocob=False, learning_rate=lr, use_rocket=False)
            plot_data(label, colors[color_idx], label=label)
        color_idx += 1

        plt.title(name_dataset)
        # plt.legend()
        plt.show()

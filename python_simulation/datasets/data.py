import pandas as pd
import torch
from torch.utils.data import Dataset
import numpy as np

from pathlib import Path

import copy

from rocket.minirocket import fit, transform


def class_string_to_int(values, class_values_dict):
    y = []
    for v in values:
        y.append(class_values_dict[v])
    return y


def normalize(x, std, mean):
    return (x - mean) / std


def load_ucr_dataset(name, test=False):
    data = copy.deepcopy(
        pd.read_csv(f"{Path.home()}/datasets/{name}/{name}_{'TRAIN' if not test else 'TEST'}.tsv", sep="\t",
                    header=None))

    # remove NANs by interpolation
    data = data.interpolate(axis=1)

    X = np.array(data[data.columns[1:]])
    y = np.array(data[data.columns[0]])

    # shuffle data
    shuffle_vec = np.array([i for i in range(len(y))])
    np.random.shuffle(shuffle_vec)

    X = X[shuffle_vec, :]
    y = y[shuffle_vec]

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


class ClassificationDataset:
    def __init__(self, params, seed):
        np.random.seed(seed)
        torch.random.manual_seed(seed)
        print(f"Starting to load dataset {params['dataset_name']}...")
        self.params = params

        X_train, y_train = load_ucr_dataset(name=params["dataset_name"], test=False)
        X_test, y_test = load_ucr_dataset(name=params["dataset_name"], test=True)

        self.data_mean = np.mean(X_train)
        self.data_std = np.std(y_train)

        X_train = normalize(X_train, self.data_std, self.data_mean)
        X_test = normalize(X_test, self.data_std, self.data_mean)

        size_training = int(round(len(X_train) * params["train_size"]))

        self.num_classes = int(round(max(y_test))) + 1
        self.length_timeseries = len(X_train[0])

        rocket_parameters = fit(X_train, 10_000)
        X_train = transform(X_train, rocket_parameters)
        X_test = transform(X_test, rocket_parameters)

        # X_train = torch.tensor(X_train, device="cuda:0")
        # X_test = torch.tensor(X_test, device="cuda:0")
        # y_train = torch.tensor(y_train, device="cuda:0")
        # y_test = torch.tensor(y_test, device="cuda:0")

        self.train_ds = PartDataset(X_train[0:size_training, :], y_train[0:size_training])
        self.eval_ds = PartDataset(X_train[size_training:, :], y_train[size_training:])
        self.test_ds = PartDataset(X_test, y_test)

        self.X_train = X_train
        self.y_train = y_train

        self.X_test = X_test
        self.y_test = y_test

        print(f"Loaded dataset {params['dataset_name']} with {self.num_classes} classes, "
              f"length of {self.length_timeseries} "
              f"with {len(X_train)} training entrances and {len(X_test)} test entrances")



class PartDataset(Dataset):
    """MLP Dataset class."""
    def __init__(self, input, output):
        self.input = input
        self.output = output

    def __len__(self):
        return len(self.input)

    def __getitem__(self, idx):
        return {'input': self.input[idx], 'target': self.output[idx]}


if __name__ == "__main__":
    params = {}
    params["dataset_name"] = "AllGestureWiimoteX"
    params["train_size"] = 0.8

    cd = ClassificationDataset(params)
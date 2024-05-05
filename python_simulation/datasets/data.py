import random

import pandas as pd
import torch
from torch.utils.data import Dataset
import numpy as np

from pathlib import Path

import copy

from rocket.minirocket import fit, transform

import struct
from array import array
from os.path  import join

import matplotlib.pyplot as plt

import torchvision

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
    print(y.dtype)
    assert False

    # shuffle data
    shuffle_vec = np.array([i for i in range(len(y))])
    np.random.shuffle(shuffle_vec)

    X = X[shuffle_vec, :]
    y = y[shuffle_vec]

    y_unique = np.unique(y)
    if len(y_unique) == 2:
        if np.all(np.unique(y) == [-1, 1]):
            y[y == 1] = 2
            y[y==-1] = 1

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


class MnistDataloader(object):
    def __init__(self, training_images_filepath, training_labels_filepath,
                 test_images_filepath, test_labels_filepath):
        self.training_images_filepath = training_images_filepath
        self.training_labels_filepath = training_labels_filepath
        self.test_images_filepath = test_images_filepath
        self.test_labels_filepath = test_labels_filepath

    def read_images_labels(self, images_filepath, labels_filepath):
        labels = []
        with open(labels_filepath, 'rb') as file:
            magic, size = struct.unpack(">II", file.read(8))
            if magic != 2049:
                raise ValueError('Magic number mismatch, expected 2049, got {}'.format(magic))
            labels = array("B", file.read())

        with open(images_filepath, 'rb') as file:
            magic, size, rows, cols = struct.unpack(">IIII", file.read(16))
            if magic != 2051:
                raise ValueError('Magic number mismatch, expected 2051, got {}'.format(magic))
            image_data = array("B", file.read())
        images = []
        for i in range(size):
            images.append([0] * rows * cols)
        for i in range(size):
            img = np.array(image_data[i * rows * cols:(i + 1) * rows * cols])
            img = img.reshape(28, 28)
            images[i][:] = img

        return images, labels

    def load_data(self):
        x_train, y_train = self.read_images_labels(self.training_images_filepath, self.training_labels_filepath)
        x_test, y_test = self.read_images_labels(self.test_images_filepath, self.test_labels_filepath)
        return (np.array(x_train, dtype=np.float32)[0:1000], np.array(y_train)[0:1000]), (np.array(x_test[0:1000], dtype=np.float32), np.array(y_test)[0:1000])


def quantize_8_bit(data, offset, scaling):
    return np.clip((data - offset) / scaling * 127, a_min=-127, a_max=127)


class ClassificationDataset:
    def __init__(self, params, seed):
        np.random.seed(seed)
        torch.random.manual_seed(seed)
        print(f"Starting to load dataset {params['dataset_name']}...")
        self.params = params

        if self.params["dataset_name"] == "Mnist":
            input_path = f"{Path.home()}/torch_datasets/Mnist"
            training_images_filepath = join(input_path, 'train-images-idx3-ubyte/train-images-idx3-ubyte')
            training_labels_filepath = join(input_path, 'train-labels-idx1-ubyte/train-labels-idx1-ubyte')
            test_images_filepath = join(input_path, 't10k-images-idx3-ubyte/t10k-images-idx3-ubyte')
            test_labels_filepath = join(input_path, 't10k-labels-idx1-ubyte/t10k-labels-idx1-ubyte')

            #
            # Load MINST dataset
            #
            mnist_dataloader = MnistDataloader(training_images_filepath, training_labels_filepath, test_images_filepath,
                                               test_labels_filepath)
            (X_train, y_train), (X_test, y_test) = mnist_dataloader.load_data()

            X_train = np.reshape(X_train, (len(X_train), X_train.shape[1] * X_train.shape[2]))
            X_test = np.reshape(X_test, (len(X_test), X_test.shape[1] * X_test.shape[2]))

        elif self.params["dataset_name"] == "cifar":
            train_data = torchvision.datasets.CIFAR10(root=f"{Path.home()}/torch_datasets/Cifar",
                                                            train=True, download=True)

            test_data = torchvision.datasets.CIFAR10(root=f"{Path.home()}/torch_datasets/Cifar",
                                                      train=False, download=True)

            def reformat_cifar(data, num_samples):
                X = np.zeros((num_samples, 32, 32, 3), dtype=np.float32)
                y = np.zeros((num_samples,), dtype=np.int64)
                for i in range(num_samples):
                    im, cl = data[i]
                    X[i] = np.array(im, dtype=np.float32)
                    y[i] = cl

                X_ = np.zeros((num_samples, 32*32*3), dtype=np.float32)
                for i in range(32):
                    X_[:, i * (32*3):(i+1)*(32*3)] = np.reshape(X[:, i, :, :], (len(X), 32*3))
                    if i%2 == 1:
                        X_[:, i * (32*3):(i+1)*(32*3)] = np.flip(X_[:, i * (32*3):(i+1)*(32*3)], axis=1)

                return X_, y

            X_train, y_train = reformat_cifar(train_data, 600)
            X_test, y_test = reformat_cifar(test_data, 600)


        else:
            X_train, y_train = load_ucr_dataset(name=params["dataset_name"], test=False)
            X_test, y_test = load_ucr_dataset(name=params["dataset_name"], test=True)

            if params["use_rocket"]:
                quantization_offset = np.mean(X_train)
                quantization_scaling = np.percentile(np.abs(X_train - quantization_offset), q=99.9)

                X_train = quantize_8_bit(X_train, quantization_offset, quantization_scaling)
                X_test = quantize_8_bit(X_test, quantization_offset, quantization_scaling)

            self.data_mean = np.mean(X_train)
            self.data_std = np.std(X_train)

            X_train = normalize(X_train, self.data_std, self.data_mean)
            X_test = normalize(X_test, self.data_std, self.data_mean)


        size_training = int(round(len(X_train) * params["train_size"]))

        self.num_classes = int(round(max(y_train)))
        y_test -= 1
        y_train -= 1
        self.length_timeseries = len(X_train[0])

        if params["use_rocket"]:
            rocket_parameters = fit(X_train, 10_000)
            X_train = transform(X_train, rocket_parameters)
            X_test = transform(X_test, rocket_parameters)

        # X_train = torch.tensor(X_train, device="cuda:0")
        # X_test = torch.tensor(X_test, device="cuda:0")
        # y_train = torch.tensor(y_train, device="cuda:0")
        # y_test = torch.tensor(y_test, device="cuda:0")

        self.num_features = len(X_train[0])

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
    params["dataset_name"] = "cifar"
    params["train_size"] = 0.8

    cd = ClassificationDataset(params, 0)
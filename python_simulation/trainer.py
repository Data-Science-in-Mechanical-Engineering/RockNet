import copy
import time

import yaml

from datasets.data import ClassificationDataset
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils import data

from tqdm import tqdm

from rocket.minirocket import fit, transform

from optimizer.cocob import COCOB_Backprop

def init(layer):
    if isinstance(layer, nn.Linear):
        nn.init.constant_(layer.weight.data, 0)
        nn.init.constant_(layer.bias.data, 0)


def get_dataloader(
        ds,
        batch_size: int,
        num_workers: int,
        pin_memory: bool = True,  # accelerates copy operation to GPU
        **kwargs):
    """Shortcut to get the DataLoader of 'ds' with default settings from config."""
    return data.DataLoader(
        ds,
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        **kwargs)

def get_accuracy(y_pred, labels):
    _, predicted = torch.max(y_pred, dim=1)
    return (predicted == labels).sum() / len(labels)


class Trainer:
    def __init__(self, params):
        self.__params = params
        self.__classification_dataset = ClassificationDataset(self.__params)

        self.__train_dl = get_dataloader(self.__classification_dataset.train_ds, batch_size=self.__params["batch_size"],
                                         num_workers=self.__params["dataloader_num_workers"])
        self.__eval_dl = get_dataloader(self.__classification_dataset.eval_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])
        self.__test_dl = get_dataloader(self.__classification_dataset.test_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])

        self.__num_features = 84 * (10_000 // 84)

        self.__model = nn.Sequential(nn.Linear(self.__num_features, self.__classification_dataset.num_classes))
        self.__loss_function = nn.CrossEntropyLoss()

        if not self.__params["use_cocob"]:
            self.__optimizer = optim.Adam(self.__model.parameters(), lr=params["learning_rate"])
            self.__scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.__optimizer, factor=0.5, min_lr=1e-8,
                                                                    patience=params["patience_lr"])
        else:
            self.__optimizer = COCOB_Backprop(self.__model.parameters())
            self.print("Using COCOB")
        self.__model.apply(init)

        self.__best_model = None

    def run(self):
        rocket_parameters = fit(self.__classification_dataset.X_train, 10_000)

        best_validation_loss = 1000000000000000
        stall_count = 0
        for epoch in range(self.__params["max_epochs"]):
            start = time.time()
            # train
            for batch_nr, batch in enumerate(self.__train_dl):
                #X_transform = transform(batch["input"].numpy(), rocket_parameters)
                X_transform = batch["input"]

                self.__optimizer.zero_grad()
                _Y_training = self.__model(torch.tensor(X_transform))
                training_loss = self.__loss_function(_Y_training, batch["target"])
                training_loss.backward()
                self.__optimizer.step()

            #validate
            validation_loss = 0
            num_datapoints = 0
            accuracy = 0
            for batch_nr, batch in enumerate(self.__eval_dl):
                #X_transform = transform(batch["input"].numpy(), rocket_parameters)
                X_transform = batch["input"]

                _Y_validation = self.__model(torch.tensor(X_transform))
                validation_loss += self.__loss_function(_Y_validation, batch["target"]) * len(batch)

                accuracy += get_accuracy(_Y_validation, batch["target"]) * len(batch)

                num_datapoints += len(batch)
            validation_loss /= num_datapoints
            accuracy /= num_datapoints

            if not self.__params["use_cocob"]:
                self.__scheduler.step(validation_loss)

            if validation_loss.item() >= best_validation_loss:
                stall_count += 1
                if stall_count >= self.__params["patience"]:
                    print(f"\n<Stopped at Epoch {epoch + 1}>")
                    break
            else:
                best_validation_loss = validation_loss.item()
                self.__best_model = copy.deepcopy(self.__model)
                stall_count = 0

            self.print(f"Epoch {epoch+1} took {time.time()-start}, accuracy={accuracy*100}%, loss={validation_loss}")

    def print(self, text):
        if self.__params["show_print"]:
            print(text)


if __name__ == "__main__":
    np.random.seed(1)
    parameter_path = "parameters/test.yaml"
    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)

    Trainer(params).run()


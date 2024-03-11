import copy
import multiprocessing
import time
from pathlib import Path

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

import pickle as p

device = "cuda" if torch.cuda.is_available() else "cpu"


def get_logger_name(dataset_name, use_cocob, learning_rate=None):
    app = f"lr_{learning_rate}".replace(".", "_") if not use_cocob else "cocob"
    return f"{dataset_name}_{app}.p"

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
        shuffle=True,
        **kwargs)

def get_accuracy(y_pred, labels):
    _, predicted = torch.max(y_pred, dim=1)
    return (predicted == labels).sum() / len(labels)


class Trainer:
    def __init__(self, params, seed):
        self.__params = params
        self.__seed = seed
        self.__classification_dataset = ClassificationDataset(self.__params, seed)

        self.__train_dl = get_dataloader(self.__classification_dataset.train_ds,
                                         batch_size=self.__params["batch_size"],
                                         num_workers=self.__params["dataloader_num_workers"])
        self.__eval_dl = get_dataloader(self.__classification_dataset.eval_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])
        self.__test_dl = get_dataloader(self.__classification_dataset.test_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])

        self.__num_features = 84 * (10_000 // 84)

        self.__model = nn.Sequential(nn.Linear(self.__num_features, self.__classification_dataset.num_classes,
                                               device=device))
        self.__loss_function = nn.CrossEntropyLoss()

        if not self.__params["use_cocob"]:
            self.__optimizer = optim.Adam(self.__model.parameters(), lr=params["learning_rate"])
            self.__scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.__optimizer, factor=0.5, min_lr=1e-8,
                                                                    patience=params["patience_lr"])
        else:
            self.__optimizer = COCOB_Backprop(self.__model.parameters(), weight_decay=1e-6)
            self.print("Using COCOB")
        self.__model.apply(init)

        self.__best_model = None

        self.__accuracies = []

    def run(self):
        # rocket_parameters = fit(self.__classification_dataset.X_train, 10_000)

        best_validation_loss = 1000000000000000
        stall_count = 0

        for epoch in range(self.__params["max_epochs"]):
            start = time.time()
            # train
            loss = 0
            num_datapoints = 0
            for batch_nr, batch in enumerate(self.__train_dl):
                #X_transform = transform(batch["input"].numpy(), rocket_parameters)
                X_transform = batch["input"].to(device)
                labels = batch["target"].to(device)

                self.__optimizer.zero_grad()
                _Y_training = self.__model(X_transform)
                training_loss = self.__loss_function(_Y_training, labels)
                training_loss.backward()
                self.__optimizer.step()
                loss += training_loss * len(batch["input"])
                print(training_loss)
                num_datapoints += len(batch["input"])
                # print(len(batch["input"]))

            print(loss.detach().item() / num_datapoints)

            #validate
            self.__model.eval()
            validation_loss, validation_accuracy = self.eval(self.__eval_dl)

            _, test_accuracy = self.eval(self.__test_dl)

            self.__accuracies.append(test_accuracy.detach().cpu().numpy())

            if epoch % 10 == 0:
                file_name = get_logger_name(f"{self.__params['dataset_name']}_{self.__seed}",
                                            use_cocob=self.__params['use_cocob'],
                                            learning_rate=self.__params['learning_rate'])
                with open(f"results/{file_name}", 'wb') as handle:
                    p.dump(self.__accuracies, handle, protocol=p.HIGHEST_PROTOCOL)

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

            self.print(f"Epoch {epoch+1} took {time.time()-start},\n"
                       f"validation_accuracy={validation_accuracy*100},\n"
                       f"test_accuracy={test_accuracy*100}%,\n"
                       f"loss={validation_loss}")

    def print(self, text):
        if self.__params["show_print"]:
            print(text)

    def eval(self, dl):
        validation_loss = 0
        num_datapoints = 0
        accuracy = 0
        for batch_nr, batch in enumerate(dl):
            # X_transform = transform(batch["input"].numpy(), rocket_parameters)
            X_transform = batch["input"].to(device)
            labels = batch["target"].to(device)

            _Y_validation = self.__model(X_transform)
            l = self.__loss_function(_Y_validation, labels)
            validation_loss += l * len(batch["input"])

            accuracy += get_accuracy(_Y_validation, labels) * len(batch["input"])

            num_datapoints += len(batch["input"])
        validation_loss /= num_datapoints
        accuracy /= num_datapoints
        return validation_loss, accuracy


def parallel_simulation_wrapper(params, seed):
    printout = f"Dataset: {params['dataset_name']}, cocob: {params['use_cocob']}, lr: {params['learning_rate']}"
    print(f"Starting {printout}")
    Trainer(params, seed).run()
    print(f"Finished {printout}")
    return 0


def run_batch(param_array):
    max_threads = multiprocessing.cpu_count() - 2
    p = multiprocessing.Pool(processes=np.min((max_threads, len(param_array))), maxtasksperchild=1)
    temp = [x for x in p.imap(parallel_simulation_wrapper, param_array)]
    p.close()
    p.terminate()
    p.join()


if __name__ == "__main__":
    """max_params = 768
    param_array = []
    for i in range(max_params):
        with open(f"{Path.home()}/hpc_parameters/ROCKET/params{i}.yaml", "r") as file:
            param_array.append(yaml.safe_load(file))
        parallel_simulation_wrapper(param_array[-1])
        print(f"Finished params {i}")
    exit()"""

    np.random.seed(1)
    parameter_path = "parameters/test.yaml"
    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)

    Trainer(params).run()


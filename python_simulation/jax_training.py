from functools import partial
import equinox as eqx
import optax
import jax
import jax.numpy as jnp
import math

import time
from pathlib import Path

import numpy as np

import pandas as pd
import yaml

from datasets.data import ClassificationDataset

import torch
from torch.utils import data

import pickle as p

import jax_training as jt

from training.quantized_adam import QuantizedAdam

from training.loss import cross_entropy, loss_acc_func, loss_acc_grad_func, loss_func

from datasets.data import ClassificationDataset


def init_weight(dim_in, dim_out, key):
    stdv = 1. / math.sqrt(dim_out)
    return jax.random.uniform(key, (dim_out, dim_in)) * 2 * stdv - stdv


def init_bias(dim_out, key):
    stdv = 1. / math.sqrt(dim_out)
    return jax.random.uniform(key, (dim_out,)) * 2 * stdv - stdv
    


@eqx.filter_jit
def optim_step(model, loss, x, y, opt_state, optim):
    loss_value, grads = eqx.filter_value_and_grad(loss_func)(model, loss, x, y)
    updates, opt_state = optim.update(grads, opt_state, model)
    model = eqx.apply_updates(model, updates)
    return model, opt_state, loss_value


class FCLayer(eqx.Module):
    weight: jax.Array
    bias: jax.Array
    activation: callable
    activation_function_name: str

    def __init__(self, input_dim, output_dim, rng_key, activation_function='linear'):
        super().__init__()
        key_weight, key_bias = jax.random.split(rng_key)
        self.weight = init_weight(input_dim, output_dim, key_weight)
        self.bias = init_bias(output_dim, key_bias)

        if activation_function == 'linear':
            self.activation = None
        elif activation_function == 'relu':
            self.activation = jax.nn.relu
        elif activation_function == 'tanh':
            self.activation = jax.nn.tanh
        else:
            raise ValueError(f'Activation function {activation_function} not implemented.')

        self.activation_function_name = activation_function


    def __call__(self, x):

        weight = self.weight
        bias = self.bias 
           
        y = weight @ x + bias
        if self.activation is None:
            return y
        return self.activation(y)

def get_logger_name(dataset_name, 
                    seed, 
                    use_rocket,
                    eval_dataset,
                    quantize_adam,
                    use_dynamic_tree_quantization,
                    learning_rate,
                    sample_dataset_iid=False):
    if use_rocket and quantize_adam:
        app = "eval" if eval_dataset else "test"
        app += f"{learning_rate}".replace(".", "_")
        app += "" if use_rocket else "nn"
        if quantize_adam:
            app += "_qadam"
            if use_dynamic_tree_quantization:
                app += "_dyntree"
        return f"{dataset_name}_{app}_{seed}.p"
    
    app = "eval" if eval_dataset else "test"
    app += f"_lr_{learning_rate}".replace(".", "_")
    app += f"_{sample_dataset_iid}"
    if not use_rocket:
        return f"{dataset_name}_{seed}_{app}nn.p"
    return f"{dataset_name}_{seed}_{app}.p"


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
        shuffle=False,
        **kwargs)


class Trainer:
    def __init__(self, params, seed):
        self.__params = params
        self.__seed = seed
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.__classification_dataset = ClassificationDataset(self.__params, seed, 
                                                                sample_dataset_iid=self.__params["sample_dataset_iid"])

        self.__train_dl = get_dataloader(self.__classification_dataset.train_ds,
                                         batch_size=self.__params["batch_size"],
                                         num_workers=self.__params["dataloader_num_workers"],)
        self.__eval_dl = get_dataloader(self.__classification_dataset.eval_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])
        self.__test_dl = get_dataloader(self.__classification_dataset.test_ds,
                                        batch_size=self.__params["batch_size_testing"],
                                        num_workers=self.__params["dataloader_num_workers"])

        self.__num_features = self.__classification_dataset.num_features

        self.__key = jax.random.PRNGKey(seed)

        if self.__params["use_rocket"]:
            self.__model = jt.FCLayer(self.__num_features, self.__classification_dataset.num_classes, self.next_key(),
                                      activation_function='linear')
        else:
            assert False
        self.__loss = cross_entropy

        if not self.__params["quantize_adam"]:
            self.__optim = optax.adamw(learning_rate=self.__params["learning_rate"]) 
        else:
            self.__optim = QuantizedAdam(learning_rate=self.__params["learning_rate"], 
                                         use_dynamic_tree_quantization=self.__params["use_dynamictree_quantization"])
        self.__opt_state = self.__optim.init(eqx.filter(self.__model, eqx.is_array))

        self.__test_accuracies = []
        self.__evaluation_accuracies = []

    
    def run(self):
        for epoch in range(self.__params["max_epochs"]):
            start = time.time()
            # train
            loss = 0
            num_datapoints = 0
            for batch_nr, batch in enumerate(self.__train_dl):
                #X_transform = transform(batch["input"].numpy(), rocket_parameters)
                X_transform = jnp.array(batch["input"])
                labels = jnp.array(batch["target"])

                self.__model, self.__opt_state, training_loss = optim_step(self.__model, self.__loss, X_transform, labels, self.__opt_state, self.__optim)
                
                loss += training_loss * len(batch["input"])
                num_datapoints += len(batch["input"])

            #validate
            validation_loss, validation_accuracy = self.eval(self.__eval_dl)
            self.__evaluation_accuracies.append(validation_accuracy)

            _, test_accuracy = self.eval(self.__test_dl)

            self.__test_accuracies.append(test_accuracy)

            # save results
            if epoch % 1 == 0:
                file_name = get_logger_name(self.__params['dataset_name'],
                                            seed=self.__seed,
                                            use_rocket=self.__params["use_rocket"],
                                            eval_dataset=False,
                                            quantize_adam=self.__params["quantize_adam"],
                                            use_dynamic_tree_quantization=self.__params["use_dynamictree_quantization"],
                                            learning_rate=self.__params['learning_rate'],
                                            sample_dataset_iid=self.__params["sample_dataset_iid"])
                
                with open(f"{self.__params['saving_path']}/{file_name}", 'wb') as handle:
                    p.dump(self.__test_accuracies, handle, protocol=p.HIGHEST_PROTOCOL)

                file_name = get_logger_name(self.__params['dataset_name'],
                                            seed=self.__seed,
                                            use_rocket=self.__params["use_rocket"],
                                            eval_dataset=True,
                                            quantize_adam=self.__params["quantize_adam"],
                                            use_dynamic_tree_quantization=self.__params["use_dynamictree_quantization"],
                                            learning_rate=self.__params['learning_rate'],
                                            sample_dataset_iid=self.__params["sample_dataset_iid"])
                with open(f"{self.__params['saving_path']}/{file_name}", 'wb') as handle:
                    p.dump(self.__evaluation_accuracies, handle, protocol=p.HIGHEST_PROTOCOL)

            self.print(f"Epoch {epoch+1} took {time.time()-start},\n"
                       f"validation_accuracy={validation_accuracy*100},\n"
                       f"test_accuracy={test_accuracy*100}%,\n"
                       f"loss={loss/num_datapoints}")

    def print(self, text):
        if self.__params["show_print"]:
            print(text)

    def eval(self, batches):
        evaluation_loss = 0
        evaluation_acc = 0
        num_eval_data = 0
        for batch in batches:
            X_transform = jnp.array(batch["input"])
            labels = jnp.array(batch["target"])

            loss, acc = loss_acc_func(self.__model, self.__loss, X_transform, labels)
            evaluation_loss += loss * len(batch["input"])
            evaluation_acc += acc * len(batch["input"]) / 100
            num_eval_data +=  len(batch["input"])

        evaluation_loss /= num_eval_data
        evaluation_acc /= num_eval_data

        return evaluation_loss, evaluation_acc
    

    def next_key(self):
        self.__key, subkey = jax.random.split(self.__key)
        return subkey
    

def parallel_simulation_wrapper(params, seed):
    printout = f"Dataset: {params['dataset_name']}, cocob: {params['use_cocob']}, lr: {params['learning_rate']}"
    print(f"Starting {printout}")
    Trainer(params, seed).run()
    print(f"Finished {printout}")
    return 0


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
    df = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = ["ElectricDevices"]
    for n in names:
        with open(parameter_path, "r") as file:
            params = yaml.safe_load(file)
        params["dataset_name"] = n
        for s in range(10):
            Trainer(params, seed=s).run()

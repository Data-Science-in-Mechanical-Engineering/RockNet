import copy

import pandas as pd
from pathlib import Path

import yaml

if __name__ == "__main__":
    parameter_path = "../parameters/test.yaml"
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]

    learning_rates = [0.001, 0.0001] #[0.1, 0.01, 0.001, 0.0001, 0.00001]

    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)

    i = 0
    for n in names:
        params_copy = copy.deepcopy(params)

        params_copy["dataset_name"] = n
        params_copy["show_print"] = False

        # cocob
        params_copy["use_cocob"] = True

        with open(f"{Path.home()}/hpc_parameters/ROCKET/params{i}.yaml", 'w') as file:
            yaml.dump(params_copy, file)
            i += 1

        # ADAM
        params_copy["use_cocob"] = False
        for lr in learning_rates:
            params_copy["learning_rate"] = lr
            with open(f"{Path.home()}/hpc_parameters/ROCKET/params{i}.yaml", 'w') as file:
                yaml.dump(params_copy, file)
                i += 1


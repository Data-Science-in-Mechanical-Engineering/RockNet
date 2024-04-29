import copy

import pandas as pd
from pathlib import Path

import yaml

if __name__ == "__main__":
    parameter_path = "../parameters/test.yaml"
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]

    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)

    i = 0
    for n in names:
        params_copy = copy.deepcopy(params)

        params_copy["dataset_name"] = n
        params_copy["show_print"] = False

        for use_rocket in [True, False]:
            params_copy["use_rocket"] = use_rocket
            with open(f"{Path.home()}/hpc_parameters/ROCKET/params{i}.yaml", 'w') as file:
                yaml.dump(params_copy, file)
                i += 1

        """# cocob
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
                i += 1"""


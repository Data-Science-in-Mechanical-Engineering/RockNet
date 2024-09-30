import copy

import pandas as pd
from pathlib import Path

import yaml

if __name__ == "__main__":
    parameter_path = "../parameters/test.yaml"
    data = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = data["Name"]
    print(data)

    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)

    params["saving_path"] = "/work/mf724021/rocknet"
    i = 0
    for data_index, n in enumerate(names):
        if data["Train "][data_index] < 100:
            pass
            # continue
        params_copy = copy.deepcopy(params)

        params_copy["dataset_name"] = n
        params_copy["show_print"] = False

        # for use_rocket in [True]:   #, False]:
        for quantize_adam in [False, True]:
            params_copy["use_rocket"] = True
            params_copy["quantize_adam"] = quantize_adam
            params_copy["use_dynamictree_quantization"] = True
            with open(f"/work/mf724021/hpc_parameters/ROCKET/params{i}.yaml", 'w') as file:
                yaml.dump(params_copy, file)
                i += 1
            
        params_copy["use_rocket"] = True
        params_copy["quantize_adam"] = True
        params_copy["use_dynamictree_quantization"] = False
        with open(f"/work/mf724021/hpc_parameters/ROCKET/params{i}.yaml", 'w') as file:
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
    print(f"Generated {i} combinations")


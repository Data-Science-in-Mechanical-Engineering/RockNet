import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import trainer

def parse_arguments():
    parser = argparse.ArgumentParser(description="Training NN on HPC cluster")
    parser.add_argument("-i", "--iter_id", help="ID of the current iteration", type=int)
    # parser.add_argument("-p", "--iteration", help="path to the .yaml file specifying the parameters", type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    np.random.seed(1)
    parameter_path = "parameters/test.yaml"
    df = pd.read_csv(f"{Path.home()}/datasets/DataSummary.csv")
    names = df["Name"]

    with open(parameter_path, "r") as file:
        params = yaml.safe_load(file)
    params["dataset_name"] = names[args.iter_id]
    trainer.Trainer(params, seed=0).run()

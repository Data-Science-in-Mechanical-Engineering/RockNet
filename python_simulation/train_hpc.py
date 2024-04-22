import argparse
import yaml
import trainer

def parse_arguments():
    parser = argparse.ArgumentParser(description="Training NN on HPC cluster")
    # comb_id = from sbatch --export=comb_id=X flag
    parser.add_argument("-c", "--comb_id", help="ID of the hyperparameter combination", type=int)
    # iter_id = SLURM_ARRAY_TASK_ID
    parser.add_argument("-i", "--iter_id", help="ID of the current iteration", type=int)

    parser.add_argument("-r", "--pruning_step", help="current pruning step", type=int)

    # slurm_job_id = SLURM_ARRAY_JOB_ID
    parser.add_argument("-s", "--slurm_job_id", help="ID of the SLURM job", type=int)

    parser.add_argument("-p", "--params", help="path to the .yaml file specifying the parameters", type=str)

    parser.add_argument("-n", "--name", help="name of parameter sweep", type=str)

    # parser.add_argument("-p", "--iteration", help="path to the .yaml file specifying the parameters", type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    print(f"Starting training of combination of {args.iter_id}")

    with open(f"/work/mf724021/hpc_parameters/ROCKET/params{args.iter_id}.yaml", "r") as file:
        params = yaml.safe_load(file)

    for i in range(100):
        trainer.parallel_simulation_wrapper(params, seed=i)

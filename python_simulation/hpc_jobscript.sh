#!/usr/local_rwth/bin/zsh
#
#SBATCH --job-name=ROCKET
#SBATCH --output=/home/mf724021/hpc_data/slurm_output/%A_%a.out
#SBATCH --nodes=1 # request one node
#SBATCH --account=rwth1476
#SBATCH --cpus-per-task=10
#SBATCH --partition=c23ms
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=alexander.graefe@dsme.rwth-aachen.de
#SBATCH --time=0-10:00:00
#SBATCH --array=0-255

module load Python/3.10.4

source venv/bin/activate
python train_hpc.py -i $SLURM_ARRAY_TASK_ID -j True
deactivate

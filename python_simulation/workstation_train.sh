#!/bin/bash

for ((SLURM_ARRAY_TASK_ID=20;SLURM_ARRAY_TASK_ID<=200;SLURM_ARRAY_TASK_ID++));
do
  python train_workstation.py -i $SLURM_ARRAY_TASK_ID
done
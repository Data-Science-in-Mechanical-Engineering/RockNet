#!/bin/bash

rsync -a -e ssh ~/hpc_parameters/ROCKET/ mf724021@copy18-1.hpc.itc.rwth-aachen.de:/work/mf724021/hpc_parameters/ROCKET/
#rsync -a -e ssh mf724021@copy18-1.hpc.itc.rwth-aachen.de:~/Dokumente/rocket_distributed_inference/python_simulation/results/ results/

# rsync -a -e ssh /home/alex/hpc_parameters/aeon_best/ mf724021@copy18-1.hpc.itc.rwth-aachen.de:/work/mf724021/hpc_parameters/aeon_best
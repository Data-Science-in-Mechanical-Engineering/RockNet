# RockNet: Distributed Learning on Ultra-Low-Power Devices

This is the accompanying repository for our paper: RockNet: Distributed Learning on Ultra-Low-Power Devices

# Installation
## Simulation

Download the UCR timeseries archive [https://www.cs.ucr.edu/~eamonn/time_series_data/](https://www.cs.ucr.edu/~eamonn/time_series_data/).

To start training run
```Console
cd python_simulation
pip install -r requirements.txt
python trainer.py
```

## Hardware Experiments
Install Segger Embedded Studio V5.44 for ARM: https://www.segger.com/downloads/embedded-studio/ .
You can open the firmware (e.g., to build and flash it) by opening c_src/cp_firmware/app/cp_firmware.emProject.

Run
```Console
python GenerateCodeDistributedRocket.py
```
to export the dataset and configure RockNet. This will automatically change the code inside c_src.

## Hardware Files
For gerber files regarding the communication PCBs, please contact: alexander.graefe@dsme.rwth-aachen.de

# Citation
```
@article{Graefe2025RockNet,
TODO
}
``` 


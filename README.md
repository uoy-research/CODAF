# CODAF
**The content of this repository has been developed as a component of a project conducted at the University of York. The authors wish to clarify that they do not plan to provide ongoing maintenance or support for the codebase. Therefore, users are advised to exercise caution and utilize the software at their own discretion and risk.**

This repository contains the following files:

1. **Battery Simulation**: This file provides details about battery modeling and simulation. It covers aspects such as state of charge, power draw during mission, physical parameters of battery and mission planner.

2. **Reconfiguration**: 

3. **Graphical User Interface (GUI)**: In this file, we describe the GUI component of our project. It demonstrates relevant mission parameters.

# 1-Battery Simulation
**Developed in simulink-Matlab in Windows 11.**

The content for this work is in the 'Battery Simulation' folder. The **Simulink-Battery.zip** folder containis the simulink files for the battery simulation. **Simscape** is required to run the simulation.

# 2-Reconfiguration

# 3-Graphical User Interface
**Developed and tested in Python 3.11.7, Windows 11.**
The content for this work is in the 'GUI' folder under the zip file: `CODAF-Final.zip`.
To run the GUI, extract all files from the provided zip archive and execute `CODAF-Final.exe`.

The Python code for the graphical user interface (GUI) is `CODAF-Final.py`. 

The following libraries are required to run the GUI:
- `sys`
- `os`
- `PyQt5`
- `pandas`
- `matplotlib`
- `schemdraw`
- `io`

To run the GUI, execute the following command in the Conda terminal in the files directory:

python CODAF-Final.py

A video demonstrating the GUI software running is available in the file `Demo.zip`.



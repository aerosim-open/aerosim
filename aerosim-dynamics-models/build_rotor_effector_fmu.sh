#!/bin/bash

pythonfmu3 build -f python/aerosim_dynamics_models/rotor_effector_fmu_model.py
mv rotor_effector_fmu_model.fmu ../examples/fmu
echo Built and moved rotor_effector_fmu_model.fmu to ../examples/fmu

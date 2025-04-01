#!/bin/bash

pythonfmu3 build -f python/aerosim_dynamics_models/jsbsim_standalone_fmu_model.py python/aerosim_dynamics_models/requirements_jsbsim_dynamics.txt
mv jsbsim_standalone_fmu_model.fmu ../examples/fmu
echo Built and moved jsbsim_standalone_fmu_model.fmu to ../examples/fmu

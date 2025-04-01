#!/bin/bash

pythonfmu3 build -f python/aerosim_dynamics_models/evtol_effectors_fmu_model.py
mv evtol_effectors_fmu_model.fmu ../examples/fmu
echo Built and moved evtol_effectors_fmu_model.fmu to ../examples/fmu

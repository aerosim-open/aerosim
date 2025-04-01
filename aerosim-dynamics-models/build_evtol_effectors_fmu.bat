@echo off

pythonfmu3 build -f python/aerosim_dynamics_models/evtol_effectors_fmu_model.py || exit /b
move /Y evtol_effectors_fmu_model.fmu ..\examples\fmu || exit /b
echo Built and moved evtol_effectors_fmu_model.fmu to ..\examples\fmu

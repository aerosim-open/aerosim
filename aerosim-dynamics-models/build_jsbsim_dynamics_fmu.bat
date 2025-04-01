@echo off

pythonfmu3 build -f python/aerosim_dynamics_models/jsbsim_dynamics_fmu_model.py python/aerosim_dynamics_models/requirements_jsbsim_dynamics.txt || exit /b
move /Y jsbsim_dynamics_fmu_model.fmu ..\examples\fmu || exit /b
echo Built and moved jsbsim_dynamics_fmu_model.fmu to ..\examples\fmu

@echo off

pythonfmu3 build -f python/aerosim_dynamics_models/rotor_effector_fmu_model.py || exit /b
move /Y rotor_effector_fmu_model.fmu ..\examples\fmu || exit /b
echo Built and moved rotor_effector_fmu_model.fmu to ..\examples\fmu

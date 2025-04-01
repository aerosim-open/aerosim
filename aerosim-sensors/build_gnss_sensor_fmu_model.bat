@echo off

pythonfmu3 build -f python/aerosim_sensors/gnss_sensor_fmu_model.py python/aerosim_sensors/sensor_requirements.txt || exit /b
move /Y gnss_sensor_fmu_model.fmu ..\examples\fmu || exit /b
echo Built and moved gnss_sensor_fmu_model.fmu to ..\examples\fmu

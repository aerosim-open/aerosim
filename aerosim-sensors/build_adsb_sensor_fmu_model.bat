@echo off

pythonfmu3 build -f python/aerosim_sensors/adsb_sensor_fmu_model.py python/aerosim_sensors/sensor_requirements.txt || exit /b
move /Y adsb_sensor_fmu_model.fmu ..\examples\fmu || exit /b
echo Built and moved adsb_sensor_fmu_model.fmu to ..\examples\fmu

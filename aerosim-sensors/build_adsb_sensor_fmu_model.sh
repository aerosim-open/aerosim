#!/bin/bash

pythonfmu3 build -f python/aerosim_sensors/adsb_sensor_fmu_model.py python/aerosim_sensors/sensor_requirements.txt
mv adsb_sensor_fmu_model.fmu ../examples/fmu
echo Built and moved adsb_sensor_fmu_model.fmu to ../examples/fmu

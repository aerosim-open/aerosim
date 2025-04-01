#!/bin/bash

SRC_FOLDER=python/aerosim_controllers
FMU_PYTHON_SCRIPT=jsbsim_flight_controller_fmu_model.py
FMU_REQUIREMENTS_TXT=requirements_jsbsim.txt
OUTPUT_FOLDER=../examples/fmu

if [ "$FMU_REQUIREMENTS_TXT" = "" ]; then
    REQUIREMENTS_TXT=
else
    REQUIREMENTS_TXT=$SRC_FOLDER/$FMU_REQUIREMENTS_TXT
fi

OUTPUT_FMU=${FMU_PYTHON_SCRIPT::-3}.fmu

BUILD_FMU_CMD="pythonfmu3 build -f $SRC_FOLDER/$FMU_PYTHON_SCRIPT $REQUIREMENTS_TXT"

echo "Running: $BUILD_FMU_CMD"
$BUILD_FMU_CMD
mv $OUTPUT_FMU $OUTPUT_FOLDER
echo "Built and moved $OUTPUT_FMU to $OUTPUT_FOLDER"

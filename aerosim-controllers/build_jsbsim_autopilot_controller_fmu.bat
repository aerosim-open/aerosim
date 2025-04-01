@echo off

set SRC_FOLDER=python\aerosim_controllers
set FMU_PYTHON_SCRIPT=jsbsim_autopilot_controller_fmu_model.py
set FMU_REQUIREMENTS_TXT=requirements_jsbsim.txt
set OUTPUT_FOLDER=..\examples\fmu

if %FMU_REQUIREMENTS_TXT% == "" (
    set REQUIREMENTS_TXT=
) else (
    set REQUIREMENTS_TXT=%SRC_FOLDER%\%FMU_REQUIREMENTS_TXT%
)

set OUTPUT_FMU=%FMU_PYTHON_SCRIPT:~0,-3%.fmu
set BUILD_FMU_CMD=pythonfmu3 build -f %SRC_FOLDER%\%FMU_PYTHON_SCRIPT% %REQUIREMENTS_TXT%

echo Running: %BUILD_FMU_CMD%
%BUILD_FMU_CMD% || exit /b
move /Y %OUTPUT_FMU% %OUTPUT_FOLDER% || exit /b
echo Built and moved %OUTPUT_FMU% to %OUTPUT_FOLDER%

@echo off

@REM Install/sync the Python virtual environment
rye sync || exit /b %ERRORLEVEL%

@REM Activate the Python virtual environment
call .venv\Scripts\activate

@REM Build AeroSim with force flag to ensure aerosim-world-link is always rebuilt
rye run build -f

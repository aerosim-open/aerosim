@echo off
setlocal enabledelayedexpansion

echo Reset aerosim and all related repositories by running 'git clean -fdx' and 'git reset --hard' in the following repositories:
echo.
echo   aerosim repo: %AEROSIM_ROOT%
echo   aerosim-app repo: %AEROSIM_APP_ROOT%
echo   aerosim-assets repo: %AEROSIM_ASSETS_ROOT%
echo   aerosim-omniverse-kit-app repo: %AEROSIM_OMNIVERSE_ROOT%
echo   aerosim-omniverse-extension repo: %AEROSIM_OMNIVERSE_ROOT%\source\extensions\aerosim.omniverse.extension
echo   aerosim-unreal-plugin repo: %AEROSIM_UNREAL_PLUGIN_ROOT%
echo   aerosim-unreal-project repo: %AEROSIM_UNREAL_PROJECT_ROOT%
echo   aerosim-assets-unreal repo: %AEROSIM_ASSETS_UNREAL_ROOT%
echo   aerosim-simulink repo: %AEROSIM_SIMULINK_ROOT%
echo.
echo WARNING: This will delete any uncommitted changes in all repositories
choice /C YN /M "Do you want to continue?"
if errorlevel 2 goto :eof

call :resetrepo "aerosim" %AEROSIM_ROOT%
call :resetrepo "aerosim-app" %AEROSIM_APP_ROOT%
call :resetrepo "aerosim-assets" %AEROSIM_ASSETS_ROOT%
call :resetrepo "aerosim-omniverse-kit-app" %AEROSIM_OMNIVERSE_ROOT%
call :resetrepo "aerosim-omniverse-extension" %AEROSIM_OMNIVERSE_ROOT%\source\extensions\aerosim.omniverse.extension
call :resetrepo "aerosim-unreal-plugin" %AEROSIM_UNREAL_PLUGIN_ROOT%
call :resetrepo "aerosim-unreal-project" %AEROSIM_UNREAL_PROJECT_ROOT%
call :resetrepo "aerosim-assets-unreal" %AEROSIM_ASSETS_UNREAL_ROOT%
call :resetrepo "aerosim-simulink" %AEROSIM_SIMULINK_ROOT%

@REM Exit the script
goto :eof

@REM Function to perform git clean/reset in a repo
:resetrepo
echo.
echo Resetting %~1 repo...
set DO_RESET=1
if %~2 == "" set DO_RESET=0
if not exist %~2 set DO_RESET=0
if !DO_RESET! == 0 (
    echo WARNING %~1 repo not found at: %~2
    echo Skipping %~1 repo.
) else (
    pushd %~2
    echo Running 'git clean -fdx' in !cd!
    git clean -fdx
    echo Running 'git reset --hard' in !cd!
    git reset --hard
    popd
)
goto :eof

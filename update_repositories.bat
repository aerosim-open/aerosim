@echo off
setlocal enabledelayedexpansion

echo Updating aerosim and related repositories

rem Function to perform git pull in a repo
call :pullrepo "aerosim" %AEROSIM_ROOT%
call :pullrepo "aerosim-app" %AEROSIM_APP_ROOT%
call :pullrepo "aerosim-assets" %AEROSIM_ASSETS_ROOT%
call :pullrepo "aerosim-omniverse-kit-app" %AEROSIM_OMNIVERSE_ROOT%
call :pullrepo "aerosim-unreal-project" %AEROSIM_UNREAL_PROJECT_ROOT%
call :pullrepo "aerosim-assets-unreal" %AEROSIM_ASSETS_UNREAL_ROOT%
call :pullrepo "aerosim-unreal-plugin" %AEROSIM_UNREAL_PLUGIN_ROOT%

rem Exit the script
goto :eof

:pullrepo
echo %~1
cd %~2
echo %cd%
git pull
git branch
goto :eof
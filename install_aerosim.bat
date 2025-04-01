@echo off
setlocal enabledelayedexpansion
title AeroSim Installation Script - Windows

:: -------------------------------------------------------------
:: Banner (ASCII art) and Intro text
:: -------------------------------------------------------------
for /f "delims=" %%i in ('echo prompt $E^| cmd') do set "ESC=%%i"
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "RED=%ESC%[31m"
set "CYAN=%ESC%[36m"
set "MAGENTA=%ESC%[35m"
set "RESET=%ESC%[0m"

:::          ___                  _____ _
:::         /   | ___  _________ / ___/(_)___ ___
:::        / /| |/ _ \/ ___/ __ \\__ \/ / __ `__ \
:::       / ___ /  __/ /  / /_/ /__/ / / / / / / /
:::      /_/  |_\___/_/   \____/____/_/_/ /_/ /_/
cls
echo %CYAN%======================================================%
for /f "delims=: tokens=*" %%A in ('findstr /b ::: "%~f0"') do @echo(%%A
echo.
echo             AeroSim Installation Script
echo ====================================================== %RESET%
echo.
echo This script installs the AeroSim simulator environment.
echo.
echo %YELLOW%IMPORTANT:%RESET%
echo - Ensure your GitHub, Epic Games, and Cesium accounts are set up.
echo - Link your GitHub and Epic Games accounts as described in the installation guide.
echo.
pause

:: -------------------------------------------------------------
:: Set Working Directory and Variables
:: -------------------------------------------------------------
cd /d "%~dp0"
set "INSTALL_SCRIPT=%~nx0"
set "INSTALL_SCRIPT_PATH=%~dp0"
if "!INSTALL_SCRIPT_PATH:~-1!"=="\" set "INSTALL_SCRIPT_PATH=!INSTALL_SCRIPT_PATH:~0,-1!"

:: Repository URLs and flags
set "GIT_CLONE_PREFIX=https://github.com/"
set "AEROSIM_REPO_URL=aerosim-open/aerosim.git"
set "AEROSIM_UNREAL_PROJECT_REPO_URL=aerosim-open/aerosim-unreal-project.git"
set "AEROSIM_UNREAL_PLUGIN_URL=aerosim-open/aerosim-unreal-plugin.git"
set "AEROSIM_OMNIVERSE_KIT_APP_URL=aerosim-open/aerosim-omniverse-kit-app.git"
set "AEROSIM_OMNIVERSE_EXTENSION_URL=aerosim-open/aerosim-omniverse-extension.git"
set "AEROSIM_ASSETS_REPO_URL=aerosim-open/aerosim-assets.git"
set "AEROSIM_ASSETS_UNREAL_REPO_URL=aerosim-open/aerosim-assets-unreal.git"
set "AEROSIM_SIMULINK_REPO_URL=aerosim-open/aerosim-simulink.git"
set "AEROSIM_APP_REPO_URL=aerosim-open/aerosim-app.git"

:: If running inside an existing AeroSim repo, adjust working directory.
if exist "!INSTALL_SCRIPT_PATH!\.git\config" (
    findstr /m /c:"%AEROSIM_REPO_URL%" "!INSTALL_SCRIPT_PATH!\.git\config" >NUL 2>&1
    if !ERRORLEVEL! equ 0 (
        for %%i in ("!INSTALL_SCRIPT_PATH!") do set "AEROSIM_REPO_FOLDER=%%~nxi"
        echo %YELLOW%[INFO] Existing AeroSim repo found: !AEROSIM_REPO_FOLDER!\%RESET%
        if /i "!CD!"=="!INSTALL_SCRIPT_PATH!" (
            cd ..
            echo %YELLOW%[INFO] Changing working directory to parent folder: !CD!%RESET%
        )
    )
) else (
    set "AEROSIM_REPO_FOLDER=aerosim"
)
set "WORKING_DIR=%CD%"

:: Initialize installation flags
set PREREQS_FLAG=0
set DEV_FLAG=0
set UNREAL_FLAG=0
set OMNIVERSE_FLAG=0
set ASSETS_FLAG=0
set SIMULINK_FLAG=0
set APP_FLAG=0
set PIXEL_STREAMING_FLAG=0
set "CREATED_ENV_VARS="

:: -------------------------------------------------------------
:: CLI Mode vs Interactive Mode
:: -------------------------------------------------------------
set "ARGS=%*"
if "%ARGS%"=="" (
    goto :MainMenu
) else (
    set "CLI_MODE=1"
    goto :ARGPARSE
)

:ARGPARSE
    if /i "%~1"=="-h" (
        goto :HELP
    ) else if /i "%~1"=="-prereqs" (
        set PREREQS_FLAG=1
    ) else if /i "%~1"=="-dev" (
        set DEV_FLAG=1
    ) else if /i "%~1"=="-unreal" (
        set UNREAL_FLAG=1
    ) else if /i "%~1"=="-omniverse" (
        set OMNIVERSE_FLAG=1
    ) else if /i "%~1"=="-assets" (
        set ASSETS_FLAG=1
    ) else if /i "%~1"=="-simulink" (
        set SIMULINK_FLAG=1
    ) else if /i "%~1"=="-app" (
        set APP_FLAG=1
    ) else if /i "%~1"=="-pixelstreaming" (
        set PIXEL_STREAMING_FLAG=1
    ) else if /i "%~1"=="-all" (
        set PREREQS_FLAG=1
        set DEV_FLAG=1
        set UNREAL_FLAG=1
        set OMNIVERSE_FLAG=1
        set ASSETS_FLAG=1
        set SIMULINK_FLAG=1
        set APP_FLAG=1
        set PIXEL_STREAMING_FLAG=1
    ) else (
        echo %RED%Unknown argument: %~1%RESET%
        goto :HELP
    )
    shift
    if not "%~1"=="" goto ARGPARSE
goto :INSTALL_CLI

:HELP
echo.
echo Usage: %INSTALL_SCRIPT% [-h] [-prereqs] [-dev] [-unreal] [-omniverse] [-assets] [-simulink] [-app] [-pixelstreaming] [-all]
echo.
echo Parameters:
echo    -h               Show this help and quit.
echo    -prereqs         Install prerequisites.
echo    -dev             Install development environment.
echo    -unreal          Install Unreal integration.
echo    -omniverse       Install Omniverse integration.
echo    -assets          Install asset library.
echo    -simulink        Install Simulink integration.
echo    -app             Install AeroSim application.
echo    -pixelstreaming  Install Pixel Streaming.
echo    -all             Install everything.
goto :EOF

:INSTALL_CLI
echo %CYAN%[INFO] Running in CLI mode with options:%RESET%
echo    Prereqs: %PREREQS_FLAG%
echo    Development Environment: %DEV_FLAG%
echo    Unreal Integration: %UNREAL_FLAG%
echo    Omniverse Integration: %OMNIVERSE_FLAG%
echo    Asset Library: %ASSETS_FLAG%
echo    Simulink Integration: %SIMULINK_FLAG%
echo    Application: %APP_FLAG%
echo    Pixel Streaming: %PIXEL_STREAMING_FLAG%
pause

if %PREREQS_FLAG%==1 (
    echo %YELLOW%[INFO] Installing prerequisites... (Not implemented; please run check_prerequisites.bat)%RESET%
)
if %DEV_FLAG%==1 call :InstallDev
if %UNREAL_FLAG%==1 call :InstallUnreal
if %OMNIVERSE_FLAG%==1 call :InstallOmniverse
if %ASSETS_FLAG%==1 call :InstallAssets
if %SIMULINK_FLAG%==1 call :InstallSimulink
if %APP_FLAG%==1 call :InstallApp
if %PIXEL_STREAMING_FLAG%==1 call :InstallPixelStreaming

goto :FinishInstall

:: -------------------------------------------------------------
:: Interactive Main Menu
:: -------------------------------------------------------------
:MainMenu
cls
echo %CYAN%======================================================%
for /f "delims=: tokens=*" %%A in ('findstr /b ::: "%~f0"') do @echo(%%A
echo.
echo           AeroSim Installation - Main Menu
echo ====================================================== %RESET%
echo.
echo 0. Install All Packages
echo 1. Install AeroSim Development Environment (Repo)
echo 2. Install Unreal Engine Integration
echo 3. Install Omniverse Integration
echo 4. Install Asset Library
echo 5. Install Simulink Integration
echo 6. Install AeroSim Application
echo 7. Install Pixel Streaming
echo 8. Exit Installation
echo.
set /p "userinput=Enter one or more numbers separated by space or comma: "
if "%userinput%"=="" goto :MainMenu

:: Replace commas with spaces for easier parsing
set "userinput=%userinput:,= %"

:: Initialize interactive flags
set "FLAG_DEV=0"
set "FLAG_UNREAL=0"
set "FLAG_OMNIVERSE=0"
set "FLAG_ASSETS=0"
set "FLAG_SIMULINK=0"
set "FLAG_APP=0"
set "FLAG_PIXELSTREAMING=0"

for %%a in (%userinput%) do (
    if "%%a"=="0" (
        set "ALL_MODE=1"
        set "FLAG_DEV=1"
        set "FLAG_UNREAL=1"
        set "FLAG_OMNIVERSE=1"
        set "FLAG_ASSETS=1"
        set "FLAG_SIMULINK=1"
        set "FLAG_APP=1"
        set "FLAG_PIXELSTREAMING=1"
    )
    if "%%a"=="1" set "FLAG_DEV=1"
    if "%%a"=="2" set "FLAG_UNREAL=1"
    if "%%a"=="3" set "FLAG_OMNIVERSE=1"
    if "%%a"=="4" set "FLAG_ASSETS=1"
    if "%%a"=="5" set "FLAG_SIMULINK=1"
    if "%%a"=="6" set "FLAG_APP=1"
    if "%%a"=="7" set "FLAG_PIXELSTREAMING=1"
    if "%%a"=="8" (
        call :FinishInstall
        exit /b 0
    )
)

if "%FLAG_DEV%"=="1" call :InstallDev
if "%FLAG_UNREAL%"=="1" call :InstallUnreal
if "%FLAG_OMNIVERSE%"=="1" call :InstallOmniverse
if "%FLAG_ASSETS%"=="1" call :InstallAssets
if "%FLAG_SIMULINK%"=="1" call :InstallSimulink
if "%FLAG_APP%"=="1" call :InstallApp
if "%FLAG_PIXELSTREAMING%"=="1" call :InstallPixelStreaming

:: If ALL_MODE is defined, exit without prompting to return to the main menu.
if defined ALL_MODE (
    goto :FinishInstall
) else (
    echo.
    echo %CYAN%Returning to Main Menu...%RESET%
    pause >nul
    goto :MainMenu
)

:: -------------------------------------------------------------
:: Installation Subroutines
:: -------------------------------------------------------------
:InstallDev
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing AeroSim Development Environment...%RESET%
echo.
if exist "!AEROSIM_REPO_FOLDER!" (
    echo %YELLOW%[INFO] AeroSim repo already exists at "!AEROSIM_REPO_FOLDER!". Skipping clone.
    echo Updating repository...
    pushd "!AEROSIM_REPO_FOLDER!"
    git pull
    popd
) else (
    echo %YELLOW%[INFO] Cloning AeroSim repository...%RESET%
    git clone %GIT_CLONE_PREFIX%%AEROSIM_REPO_URL% "!AEROSIM_REPO_FOLDER!"
)
set "AEROSIM_ROOT=%WORKING_DIR%\!AEROSIM_REPO_FOLDER!"
setx AEROSIM_ROOT "!AEROSIM_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_ROOT=!AEROSIM_ROOT!"
:: Set the AEROSIM_WORLD_LINK_LIB variable
set "AEROSIM_WORLD_LINK_LIB=!AEROSIM_ROOT!\aerosim-world-link\lib"
setx AEROSIM_WORLD_LINK_LIB "!AEROSIM_WORLD_LINK_LIB!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_WORLD_LINK_LIB=!AEROSIM_WORLD_LINK_LIB!"
exit /b

:InstallUnreal
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing Unreal Engine Integration...%RESET%
echo.
if not defined AEROSIM_UNREAL_ENGINE_ROOT (
    echo %RED%[ERROR] AEROSIM_UNREAL_ENGINE_ROOT is not set.%RESET%
    echo Please set it to your Unreal Engine installation path.
    echo Example: setx AEROSIM_UNREAL_ENGINE_ROOT "C:\Program Files\Epic Games\UE_5.3"
    exit /b
) else (
    echo %GREEN%[OK] AEROSIM_UNREAL_ENGINE_ROOT is set to: %AEROSIM_UNREAL_ENGINE_ROOT%%RESET%
)
if exist "aerosim-unreal-project\" (
    echo %YELLOW%[INFO] AeroSim Unreal project repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_UNREAL_PROJECT_REPO_URL% "aerosim-unreal-project"
)
if not exist "aerosim-unreal-project\Plugins" mkdir "aerosim-unreal-project\Plugins"
pushd "aerosim-unreal-project\Plugins"
if exist "aerosim-unreal-plugin\" (
    echo %YELLOW%[INFO] AeroSim Unreal plugin repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_UNREAL_PLUGIN_URL% "aerosim-unreal-plugin"
)
popd
set "AEROSIM_UNREAL_PROJECT_ROOT=%WORKING_DIR%\aerosim-unreal-project"
setx AEROSIM_UNREAL_PROJECT_ROOT "!AEROSIM_UNREAL_PROJECT_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_UNREAL_PROJECT_ROOT=!AEROSIM_UNREAL_PROJECT_ROOT!"
set "AEROSIM_UNREAL_PLUGIN_ROOT=!AEROSIM_UNREAL_PROJECT_ROOT!\Plugins\aerosim-unreal-plugin"
setx AEROSIM_UNREAL_PLUGIN_ROOT "!AEROSIM_UNREAL_PLUGIN_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_UNREAL_PLUGIN_ROOT=!AEROSIM_UNREAL_PLUGIN_ROOT!"
exit /b

:InstallOmniverse
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing Omniverse Integration...%RESET%
echo.
if exist "aerosim-omniverse-kit-app\" (
    echo %YELLOW%[INFO] AeroSim Omniverse Kit App repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_OMNIVERSE_KIT_APP_URL% "aerosim-omniverse-kit-app"
)
if not exist "aerosim-omniverse-kit-app\source\extensions" mkdir "aerosim-omniverse-kit-app\source\extensions"
pushd "aerosim-omniverse-kit-app\source\extensions"
if exist "aerosim.omniverse.extension\" (
    echo %YELLOW%[INFO] AeroSim Omniverse extension repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_OMNIVERSE_EXTENSION_URL% "aerosim.omniverse.extension"
)
popd
set "AEROSIM_OMNIVERSE_ROOT=%WORKING_DIR%\aerosim-omniverse-kit-app"
setx AEROSIM_OMNIVERSE_ROOT "!AEROSIM_OMNIVERSE_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_OMNIVERSE_ROOT=!AEROSIM_OMNIVERSE_ROOT!"
exit /b

:InstallAssets
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing Asset Library...%RESET%
echo.
if defined AEROSIM_UNREAL_PROJECT_ROOT (
    echo Installing Unreal-native assets to: !AEROSIM_UNREAL_PROJECT_ROOT!\Plugins
    pushd "!AEROSIM_UNREAL_PROJECT_ROOT!\Plugins"
    if exist "aerosim-assets-unreal\" (
        echo %YELLOW%[INFO] AeroSim asset library repo already exists in Unreal project plugins folder. Skipping clone.
    ) else (
        git clone %GIT_CLONE_PREFIX%%AEROSIM_ASSETS_UNREAL_REPO_URL% "aerosim-assets-unreal"
    )
    popd
    set "AEROSIM_ASSETS_UNREAL_ROOT=!AEROSIM_UNREAL_PROJECT_ROOT!\Plugins\aerosim-assets-unreal"
    setx AEROSIM_ASSETS_UNREAL_ROOT "!AEROSIM_ASSETS_UNREAL_ROOT!" >NUL 2>&1
    set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_ASSETS_UNREAL_ROOT=!AEROSIM_ASSETS_UNREAL_ROOT!"
)
echo.
echo Installing USD assets to: !WORKING_DIR!\aerosim-assets
if exist "aerosim-assets\" (
    echo %YELLOW%[INFO] AeroSim USD asset library repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_ASSETS_REPO_URL% "aerosim-assets"
)
set "AEROSIM_ASSETS_ROOT=!WORKING_DIR!\aerosim-assets"
setx AEROSIM_ASSETS_ROOT "!AEROSIM_ASSETS_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_ASSETS_ROOT=!AEROSIM_ASSETS_ROOT!"
exit /b

:InstallSimulink
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing Simulink Integration...%RESET%
echo.
if exist "aerosim-simulink\" (
    echo %YELLOW%[INFO] AeroSim Simulink repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_SIMULINK_REPO_URL% "aerosim-simulink"
)
set "AEROSIM_SIMULINK_ROOT=!WORKING_DIR!\aerosim-simulink"
setx AEROSIM_SIMULINK_ROOT "!AEROSIM_SIMULINK_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_SIMULINK_ROOT=!AEROSIM_SIMULINK_ROOT!"
exit /b

:InstallApp
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing AeroSim Application...%RESET%
echo.
if exist "aerosim-app\" (
    echo %YELLOW%[INFO] AeroSim app repo already exists. Skipping clone.
) else (
    git clone %GIT_CLONE_PREFIX%%AEROSIM_APP_REPO_URL% "aerosim-app"
)
pushd "aerosim-app"
echo Installing app dependencies...
bun install
popd
set "AEROSIM_APP_ROOT=!WORKING_DIR!\aerosim-app"
setx AEROSIM_APP_ROOT "!AEROSIM_APP_ROOT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_APP_ROOT=!AEROSIM_APP_ROOT!"
set "AEROSIM_APP_WS_PORT=5001"
setx AEROSIM_APP_WS_PORT "!AEROSIM_APP_WS_PORT!" >NUL 2>&1
set "CREATED_ENV_VARS=!CREATED_ENV_VARS! AEROSIM_APP_WS_PORT=!AEROSIM_APP_WS_PORT!"
exit /b

:InstallPixelStreaming
cls
echo %CYAN%------------------------------------------------------%RESET%
echo %CYAN%Installing Pixel Streaming...%RESET%
echo.
:: Determine the correct WEBSERVERS_PATH based on Unreal package flag
if !LAUNCH_UNREAL_PACKAGE! == true (
    :: Use the packaged project's Pixel Streaming WebServers (default config: Development)
    set "PACKAGE_CONFIG=Development"
    set "WEBSERVERS_PATH=%AEROSIM_UNREAL_PROJECT_ROOT%\package-%PACKAGE_CONFIG%\Windows\AerosimUE5\Samples\PixelStreaming\WebServers"
) else (
    :: Use the Unreal Engine's default Pixel Streaming WebServers location
    set "WEBSERVERS_PATH=%AEROSIM_UNREAL_ENGINE_ROOT%\Engine\Plugins\Media\PixelStreaming\Resources\WebServers"
)
echo %YELLOW%[INFO] Using WebServers path: !WEBSERVERS_PATH!%RESET%

pushd "!WEBSERVERS_PATH!"
:: Check if SignallingWebServer is installed; if not, install it
if exist "SignallingWebServer\" (
    echo %YELLOW%[INFO] SignallingWebServer already exists. Skipping download.%RESET%
) else (
    echo %YELLOW%[INFO] SignallingWebServer does not exist. Downloading SignallingWebServer...%RESET%
    if not exist "get_ps_servers.bat" (
        echo %RED%[ERROR] get_ps_servers.bat not found at "!WEBSERVERS_PATH!"%RESET%
        goto :FinishPixelStreaming
    )
    call "get_ps_servers.bat"
)
popd

echo.
echo Administrator elevation is required for the next step of running the SignallingWebServer setup script.
pause
powershell -Command "Start-Process powershell -ArgumentList \"Push-Location 'C:\Program Files\Epic Games\UE_5.3\Engine\Plugins\Media\PixelStreaming\Resources\WebServers\SignallingWebServer\platform_scripts\cmd';.\setup.bat\" -Verb RunAs"
echo.

echo Finished with Pixel Streaming installation. (Server not launched)
:FinishPixelStreaming
exit /b

:FinishInstall
cls
echo %GREEN%[OK] Installation complete.%RESET%
echo.
echo %YELLOW%[INFO] AeroSim environment variables are set as:%RESET%
echo   AEROSIM_ROOT=!AEROSIM_ROOT!
echo   AEROSIM_WORLD_LINK_LIB=!AEROSIM_WORLD_LINK_LIB!
echo   AEROSIM_UNREAL_PROJECT_ROOT=!AEROSIM_UNREAL_PROJECT_ROOT!
echo   AEROSIM_UNREAL_PLUGIN_ROOT=!AEROSIM_UNREAL_PLUGIN_ROOT!
echo   AEROSIM_OMNIVERSE_ROOT=!AEROSIM_OMNIVERSE_ROOT!
echo   AEROSIM_ASSETS_ROOT=!AEROSIM_ASSETS_ROOT!
echo   AEROSIM_ASSETS_UNREAL_ROOT=!AEROSIM_ASSETS_UNREAL_ROOT!
echo   AEROSIM_SIMULINK_ROOT=!AEROSIM_SIMULINK_ROOT!
echo   AEROSIM_APP_ROOT=!AEROSIM_APP_ROOT!
echo   AEROSIM_APP_WS_PORT=!AEROSIM_APP_WS_PORT!
echo.
echo %YELLOW%[INFO] IMPORTANT: Restart your terminal to refresh them.%RESET%
echo.
pause
exit /b

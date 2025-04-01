@echo off
setlocal enabledelayedexpansion

@REM This script is used to launch Aerosim and all the required services
echo AEROSIM_ROOT: %AEROSIM_ROOT%

set FILE_N=%~n0

@REM Print batch params (debug purpose)
@REM echo %FILE_N% params: %*

@REM ----------------------------------------------------------------------------
@REM Parse arguments

set DOC_STRING=Launch Aerosim.
set USAGE_STRING="Usage: %FILE_N% [--help] [--unreal] [--unreal-editor] [--unreal-editor-nogui] [--omniverse] [--pixel-streaming] [--pixel-streaming-ip={127.0.0.1}] [--pixel-streaming-port={8888}] [--config={Debug,Development,Shipping}] [--renderer-ids="0,1,2^"}] [--kafka-tmpfs] [--kafka-tmpfs-size={5G}]"

set REMOVE_INTERMEDIATE=false
set LAUNCH_UNREAL_PACKAGE=false
set LAUNCH_UNREAL_EDITOR_NOGUI=false
set LAUNCH_UNREAL_EDITOR=false
set LAUNCH_OMNIVERSE=false
set PACKAGE_CONFIG=Development
set PIXEL_STREAMING=false
set PIXEL_STREAMING_IP=127.0.0.1
set PIXEL_STREAMING_PORT=8888
@REM Default to a single renderer instance with ID="0"
set RENDERER_IDS="0"
@REM Create tmpfs in RAM for Kafka to allow faster I/O operations
set KAFKA_TMPFS=false
set KAFKA_TMPFS_SIZE=5G

:arg-parse
if not "%1"=="" (
    if "%1"=="--unreal" (
        set LAUNCH_UNREAL_PACKAGE=true
        set LAUNCH_UNREAL_EDITOR=false
        set LAUNCH_UNREAL_EDITOR_NOGUI=false
        set LAUNCH_OMNIVERSE=false
    )
    if "%1"=="--unreal-editor" (
        set LAUNCH_UNREAL=true
        set LAUNCH_UNREAL_EDITOR=true
        set LAUNCH_UNREAL_EDITOR_NOGUI=false
        set LAUNCH_OMNIVERSE=false
    )
    if "%1"=="--unreal-editor-nogui" (
        set LAUNCH_UNREAL=false
        set LAUNCH_UNREAL_EDITOR=false
        set LAUNCH_UNREAL_EDITOR_NOGUI=true
        set LAUNCH_OMNIVERSE=false
    )
    if "%1"=="--omniverse" (
        set LAUNCH_UNREAL=false
        set LAUNCH_UNREAL_EDITOR=false
        set LAUNCH_UNREAL_EDITOR_NOGUI=false
        set LAUNCH_OMNIVERSE=true
    )
    if "%1"=="--config" (
        set PACKAGE_CONFIG=%~2
        shift
    )
    if "%1"=="--pixel-streaming" (
        set PIXEL_STREAMING=true
    )
    if "%1"=="--pixel-streaming-ip" (
        set PIXEL_STREAMING_IP=%2
        shift
    )
    if "%1"=="--pixel-streaming-port" (
        set PIXEL_STREAMING_PORT=%2
        shift
    )
    if "%1"=="--renderer-ids" (
        set RENDERER_IDS=%2
        shift
    )
    if "%1"=="--kafka-tmpfs" (
        set KAFKA_TMPFS=true
    )
    if "%1"=="--kafka-tmpfs-size" (
        set KAFKA_TMPFS_SIZE=%2
        shift
    )
    if "%1"=="--help" (
        echo %DOC_STRING%
        echo %USAGE_STRING%
        goto :eof
    )
    shift
    goto :arg-parse
)

@REM ----------------------------------------------------------------------------
@REM Check if WSL networking mode is NAT
@REM (NAT with directly-set IP seems faster than mirrored 127.0.0.1)

wsl.exe -e wslinfo --networking-mode > networking_mode.txt
set /p NETWORKING_MODE=<networking_mode.txt
if not "!NETWORKING_MODE!" == "nat" (
    echo WSL networking mode is not set to NAT.
    echo To reduce latency, change WSL networking mode to NAT: https://learn.microsoft.com/en-us/windows/wsl/wsl-config#wslconfig
)

@REM ----------------------------------------------------------------------------
@REM Start a local Kafka server

pushd kafka
@REM Convert shell scripts from CRLF to LF
wsl.exe -e bash -c "sed -i 's/\r$//' get_kafka.sh run_kafka_local.sh"
wsl.exe -e sh get_kafka.sh %KAFKA_TMPFS% %KAFKA_TMPFS_SIZE%
for /f %%i in ('wsl.exe hostname -I') do set WSL_IP=%%i
start wsl.exe -e sh run_kafka_local.sh %WSL_IP% %KAFKA_TMPFS%
@REM Wait for the Kafka server to start
timeout /t 5 /nobreak
popd

@REM ----------------------------------------------------------------------------
@REM Handle packaging Unreal binary and launching Pixel Streaming webservers

set LAUNCH_UNREAL=false
if !LAUNCH_UNREAL_PACKAGE! == true set LAUNCH_UNREAL=true
if !LAUNCH_UNREAL_EDITOR! == true set LAUNCH_UNREAL=true
if !LAUNCH_UNREAL_EDITOR_NOGUI! == true set LAUNCH_UNREAL=true

if !LAUNCH_UNREAL! == true (
    @REM Package the Unreal binary if it does not already exist
    if !LAUNCH_UNREAL_PACKAGE! == true (
        if exist %AEROSIM_UNREAL_PROJECT_ROOT%\package-!PACKAGE_CONFIG!\Windows\AerosimUE5.exe (
            echo AerosimUE5 is already packaged.
        ) else (
            echo Starting AerosimUE5 packaging...
            pushd %AEROSIM_UNREAL_PROJECT_ROOT%
            call package.bat --config=!PACKAGE_CONFIG! || exit /b %ERRORLEVEL%
            popd
        )
    )

    @REM Launch the Pixel Streaming webservers
    if !PIXEL_STREAMING! == true (
        set SSSProcessName=Start_SignallingServer.exe
        tasklist | findstr /i !SSSProcessName! >nul
        if !errorlevel!==0 (
            echo SignallingWebServer is already running. Please next time close the process before running the script.
            taskkill /f /im !SSSProcessName!
            if !errorlevel!==0 (
                echo Killed the process !SSSProcessName!. Make sure next time to close the process before running the script.
            ) else (
                echo ERROR Could not kill the process !SSSProcessName!. Please make sure the process is not running.
                exit /b 2
            )
        )

        if !LAUNCH_UNREAL_PACKAGE! == true (
            @REM Launch Pixel Streaming webservers from an Unreal packaged binary
            set WEBSERVERS_PATH=%AEROSIM_UNREAL_PROJECT_ROOT%\package-!PACKAGE_CONFIG!\Windows\AerosimUE5\Samples\PixelStreaming\WebServers
        ) else (
            @REM Launch Pixel Streaming webservers from Unreal Editor
            set WEBSERVERS_PATH=%AEROSIM_UNREAL_ENGINE_ROOT%\Engine\Plugins\Media\PixelStreaming\Resources\WebServers
        )

        cd !WEBSERVERS_PATH!

        @REM Download the SignallingWebServer if it does not already exist
        if exist SignallingWebServer\ (
            echo SignallingWebServer already exists. Skipping download.
        ) else (
            echo SignallingWebServer does not exist. Downloading SignallingWebServer
            if not exist get_ps_servers.bat (
                echo Error: get_ps_servers.bat not found at '!WEBSERVERS_PATH!'
                exit /b 1
            )
            call get_ps_servers.bat || exit /b %ERRORLEVEL%
        )

        @REM Check if the port is already in use
        netstat -an | find ":!PIXEL_STREAMING_PORT!" > nul
        if not errorlevel 1 (
            echo Warning: Port !PIXEL_STREAMING_PORT! is already in use. Pixel streaming may fail to start.
        )

        @REM Launch the SignallingServer
        powershell -Command "Start-Process powershell -ArgumentList '-File \"!WEBSERVERS_PATH!\SignallingWebServer\platform_scripts\cmd\Start_SignallingServer.ps1\"'" || exit /b %ERRORLEVEL%
    )
)

cd %AEROSIM_ROOT%

@REM ----------------------------------------------------------------------------
@REM Handle launching Unreal renderer

if !LAUNCH_UNREAL! == true (
    @REM Set up Pixel Streaming argument flags
    set RENDERER="unreal"
    set APP_ARGS=--renderer=!RENDERER!

    set PIXEL_STREAMING_FLAGS=
    if !PIXEL_STREAMING! == true (
        echo Starting AerosimUE5 with Pixel Streaming enabled on !PIXEL_STREAMING_IP!:!PIXEL_STREAMING_PORT!
        set PIXEL_STREAMING_FLAGS="-PixelStreamingIP=!PIXEL_STREAMING_IP!" "-PixelStreamingPort=!PIXEL_STREAMING_PORT!"

        set RENDER_OFFSCREEN=false
        if !LAUNCH_UNREAL_PACKAGE! == true set RENDER_OFFSCREEN=true
        if !LAUNCH_UNREAL_EDITOR_NOGUI! == true set RENDER_OFFSCREEN=true

        if !RENDER_OFFSCREEN! == true (
            set PIXEL_STREAMING_FLAGS=!PIXEL_STREAMING_FLAGS! -RenderOffscreen -log
        )
    )

    if !LAUNCH_UNREAL_PACKAGE! == true (
        cd %AEROSIM_UNREAL_PROJECT_ROOT%\package-!PACKAGE_CONFIG!\Windows
        if not exist AerosimUE5.exe (
            echo Error: AerosimUE5.exe not found in %AEROSIM_UNREAL_PROJECT_ROOT%\package-!PACKAGE_CONFIG!\Windows
            echo Please ensure the Unreal project is properly packaged for !PACKAGE_CONFIG! configuration
            exit /b 1
        )
        echo start AerosimUE5.exe -game !PIXEL_STREAMING_FLAGS!
        start AerosimUE5.exe -game -ResX=1280 -ResY=720 !PIXEL_STREAMING_FLAGS!
        cd %AEROSIM_ROOT%
    )

    if !LAUNCH_UNREAL_EDITOR_NOGUI! == true (
        cd %AEROSIM_UNREAL_PROJECT_ROOT%
        @REM Build the project
        call build.bat || exit /b %ERRORLEVEL%
        @REM Launch in the editor's stand-alone game mode
        echo build.bat game IDS=!RENDERER_IDS! !PIXEL_STREAMING_FLAGS!
        call build.bat game IDS=!RENDERER_IDS! !PIXEL_STREAMING_FLAGS! || exit /b %ERRORLEVEL%
        cd %AEROSIM_ROOT%
    )

    if !LAUNCH_UNREAL_EDITOR! == true (
        cd %AEROSIM_UNREAL_PROJECT_ROOT%
        @REM Build the project
        call build.bat || exit /b %ERRORLEVEL%
        @REM Launch in editor mode
        echo build.bat launch IDS=!RENDERER_IDS! !PIXEL_STREAMING_FLAGS!
        call build.bat launch IDS=!RENDERER_IDS! !PIXEL_STREAMING_FLAGS! || exit /b %ERRORLEVEL%
        cd %AEROSIM_ROOT%
    )
)

@REM ----------------------------------------------------------------------------
@REM Handle launching Omniverse renderer

if !LAUNCH_OMNIVERSE! == true (
    cd %AEROSIM_OMNIVERSE_ROOT%
    set RENDERER="omniverse"
    set APP_ARGS=--renderer=!RENDERER!

    call build.bat || exit /b %ERRORLEVEL%
    if !PIXEL_STREAMING! == true (
        start launch_aerosim_dev_kit_app.bat --no-window || exit /b %ERRORLEVEL%
    ) else (
        start launch_aerosim_dev_kit_app.bat || exit /b %ERRORLEVEL%
    )
    cd %AEROSIM_ROOT%
)

@REM ----------------------------------------------------------------------------
@REM Handle no renderer selected

if !LAUNCH_UNREAL! == false (
    if !LAUNCH_OMNIVERSE! == false (
        echo No renderer was selected to be launched.
    )
)

@REM ----------------------------------------------------------------------------
@REM Handle launching the AeroSim App

cd %AEROSIM_APP_ROOT%
set CLEAN_RENDERER=!RENDERER:"=!
start "AeroSim App" bun run dev:!CLEAN_RENDERER!
cd %AEROSIM_ROOT%

@REM ----------------------------------------------------------------------------
@REM Wait for user to end the simulator

echo.
echo Launched Aerosim. Press 'Q' key to end the simulator...
call choice /c q >nul

@REM ----------------------------------------------------------------------------
@REM End the simulator

echo.
echo Ending simulator, stopping local kafka server...
wsl.exe -e bash ./kafka/bin/kafka-server-stop.sh
echo Done.

@echo on

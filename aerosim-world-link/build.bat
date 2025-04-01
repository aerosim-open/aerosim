@echo off
setlocal enabledelayedexpansion

echo Building aerosim-world-link library...

:: Check if header file exists, if not force a clean build
if not exist %~dp0\lib\aerosim_world_link.h (
    echo Header file aerosim_world_link.h is missing, performing clean build...
    cargo clean --manifest-path=%~dp0\Cargo.toml
)

cargo build --release --manifest-path=%~dp0\Cargo.toml || exit /b %ERRORLEVEL%

:: Create lib directory if it doesn't exist
if not exist %~dp0\lib mkdir %~dp0\lib

echo Copying library files to output lib folder...
if exist %~dp0\target\release\aerosim_world_link.dll (
    echo Found Windows DLL: aerosim_world_link.dll
    copy /Y %~dp0\target\release\aerosim_world_link.dll %~dp0\lib\aerosim_world_link.dll
    echo Copied as aerosim_world_link.dll
    
    :: Also copy any associated files if they exist
    if exist %~dp0\target\release\aerosim_world_link.dll.lib (
        copy /Y %~dp0\target\release\aerosim_world_link.dll.lib %~dp0\lib\aerosim_world_link.lib
        echo Copied dll.lib file as aerosim_world_link.lib
    )
    
    :: Copy the DLL lib file as a regular lib file for Unreal
    if exist %~dp0\target\release\aerosim_world_link.dll.lib (
        copy /Y %~dp0\target\release\aerosim_world_link.dll.lib %~dp0\lib\aerosim_world_link.dll.lib
        echo Copied dll.lib file as aerosim_world_link.dll.lib
    )
) else (
    echo Error: Could not find expected DLL in target\release directory
    echo Contents of target\release directory:
    dir %~dp0\target\release
    exit /b 1
)

echo Done building aerosim-world-link library.
exit /b 0

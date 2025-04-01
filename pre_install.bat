@echo off
setlocal enabledelayedexpansion
title AeroSim Pre-installation Script - Windows

:: Enable ANSI escape sequences (works in Windows 10/11)
for /f "delims=" %%i in ('echo prompt $E^| cmd') do set "ESC=%%i"

:: Define color variables
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "RED=%ESC%[31m"
set "CYAN=%ESC%[36m"
set "MAGENTA=%ESC%[35m"
set "RESET=%ESC%[0m"

:: -- Intro --
echo %CYAN%======================================================
echo         AeroSim Pre-installation Script
echo ====================================================== %RESET%
echo.
echo This script installs/upgrades prerequisites for AeroSim on Windows.
echo.
echo %YELLOW%IMPORTANT:%RESET%
echo   1. Ensure you have set up your GitHub, Epic Games, and Cesium accounts.
echo   2. Link your GitHub and Epic Games accounts as per the AeroSim installation guide.
echo   3. Please ensure that Visual Studio 2022 or the VS C++ Build Tools are installed correctly.
echo      (Ensure the C++ development on desktop module and .NET framework are selected as part of the MSVS install.)
echo   4. Install and Build Unreal Engine:
echo      - Download Unreal Engine using the Epic Games Launcher or by cloning the repository from Epic Games Git.
echo      - Follow the official build instructions to compile Unreal Engine.
echo      - Set the Unreal Engine directory path as AEROSIM_UNREAL_ENGINE_ROOT ("C:\Program Files\Epic Games\UE_5.3").
echo   5. Configure Cesium:
echo      - After creating your Cesium account, generate a Cesium token for your project.
echo      - Copy the token and assign it to the environment variable AEROSIM_CESIUM_TOKEN.
echo      - This token is required to load photorealistic tiles from the Cesium server.
echo.
pause

:: -- Check for winget --
echo %CYAN%------------------------------------------------------%RESET%
echo Checking for winget package manager...
winget --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR] winget is not installed. Please install winget from the Microsoft Store or the official website.%RESET%
    pause
    goto EndScript
) else (
    echo %GREEN%[OK] winget is installed.%RESET%
)
echo.

:Prerequisites
cls
echo %CYAN%======================================================%RESET%
echo           Prerequisites Check
echo %CYAN%======================================================%RESET%
echo.
echo This step will check for and, if necessary, install:
echo   - Rust    (%MAGENTA%https://www.rust-lang.org/tools/install%RESET%)
echo   - CMake   (%MAGENTA%https://cmake.org/download/%RESET%)
echo   - Git     (%MAGENTA%https://git-scm.com/downloads%RESET%)
echo   - Git LFS (%MAGENTA%https://git-lfs.github.com/%RESET%)
echo   - Bun     (%MAGENTA%https://bun.sh%RESET%)
echo   - NASM    (%MAGENTA%https://www.nasm.us/%RESET%)
echo   - Rye     (%MAGENTA%https://rye.astral.sh/guide/installation/%RESET%)
echo.
pause

call :CheckRust
call :CheckCMake
call :CheckGit
call :CheckGitLFS
call :CheckBun
call :CheckNASM
call :CheckRye

echo.
echo %GREEN%[INFO] Prerequisites check complete.%RESET%
echo.
pause

:EndScript
exit /b 0

:: --- Function definitions ---

:CheckRust
echo.
echo %CYAN%--- Checking for Rust --- %RESET%
where rustc >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] Rust is installed.%RESET%
    rem Attempt to get the Rust version
    rustc --version >nul 2>&1
    if errorlevel 1 (
         echo %YELLOW%[INFO] No default Rust toolchain configured. Setting default to stable...%RESET%
         rustup default stable
         if errorlevel 1 (
             echo %RED%[ERROR] Failed to set default Rust toolchain.%RESET%
         ) else (
             echo %GREEN%[OK] Default Rust toolchain set to stable.%RESET%
         )
         rustc --version
    ) else (
         rustc --version
    )
    goto :EOF
)
echo %YELLOW%[INFO] Rust is not installed.%RESET%
set /p ans="Install Rust automatically via rustup? (Y/N): "
if /i "%ans%"=="Y" (
    echo.
    echo %CYAN%[INFO] Downloading rustup installer...%RESET%
    curl -L -o rustup-init.exe https://win.rustup.rs
    if errorlevel 1 (
         echo %RED%[ERROR] Failed to download rustup installer via curl.%RESET%
         goto ManualInstall
    )
    echo %CYAN%[INFO] Running rustup installer with default settings...%RESET%
    rustup-init.exe -y
    if errorlevel 1 (
         echo %RED%[ERROR] rustup installer encountered an error.%RESET%
         goto ManualInstall
    )
    echo %GREEN%[OK] Rust installed successfully. Please restart your terminal if needed.%RESET%
    goto :EOF
) else (
    goto ManualInstall
)

:ManualInstall
echo.
echo %YELLOW%[INFO] Please manually download and run the rustup installer from:%RESET%
echo %MAGENTA%https://www.rust-lang.org/tools/install%RESET%
pause
goto :EOF

:CheckCMake
echo.
echo %CYAN%--- Checking for CMake --- %RESET%
where cmake >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] CMake is installed.%RESET%
    cmake --version
    goto :EOF
)
echo %YELLOW%[INFO] CMake is not installed.%RESET%
set /p ans="Install CMake now using winget? (Y/N): "
if /i "%ans%"=="Y" (
    winget install --id kitware.cmake --silent
    if errorlevel 1 (
        echo %RED%[ERROR] Failed to install CMake via winget.%RESET%
        pause
    ) else (
        echo %GREEN%[OK] CMake installed successfully.%RESET%
    )
) else (
    echo Skipping CMake installation.
)
goto :EOF

:CheckGit
echo.
echo %CYAN%--- Checking for Git --- %RESET%
where git >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] Git is installed.%RESET%
    git --version
    goto :EOF
)
echo %YELLOW%[INFO] Git is not installed.%RESET%
set /p ans="Install Git now using winget? (Y/N): "
if /i "%ans%"=="Y" (
    winget install --id Git.Git --silent
    if errorlevel 1 (
        echo %RED%[ERROR] Failed to install Git via winget.%RESET%
        pause
    ) else (
        echo %GREEN%[OK] Git installed successfully.%RESET%
    )
) else (
    echo Skipping Git installation.
)
goto :EOF

:CheckGitLFS
echo.
echo %CYAN%--- Checking for Git LFS --- %RESET%
git lfs version >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] Git LFS is installed.%RESET%
    git lfs version
    goto :EOF
)
echo %YELLOW%[INFO] Git LFS is not installed.%RESET%
set /p ans="Install Git LFS now using winget? (Y/N): "
if /i "%ans%"=="Y" (
    winget install --id Git.LFS --silent
    if errorlevel 1 (
        echo %RED%[ERROR] Failed to install Git LFS via winget.%RESET%
        pause
    ) else (
        echo %GREEN%[OK] Git LFS installed successfully.%RESET%
    )
) else (
    echo Skipping Git LFS installation.
)
goto :EOF

:CheckBun
echo.
echo %CYAN%--- Checking for Bun --- %RESET%
where bun >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] Bun is installed.%RESET%
    bun --version
    goto :EOF
)
echo %YELLOW%[INFO] Bun is not installed. Installing automatically...%RESET%
echo.
echo %CYAN%[INFO] Installing Bun using PowerShell...%RESET%
powershell -c "irm bun.sh/install.ps1|iex"
if errorlevel 1 (
    echo %RED%[ERROR] Failed to install Bun.%RESET%
    pause
) else (
    echo %GREEN%[OK] Bun installed successfully.%RESET%
)
goto :EOF

:CheckNASM
echo.
echo %CYAN%--- Checking for NASM --- %RESET%
where nasm >nul 2>&1
if defined ASM_NASM (
    echo %GREEN%[OK] NASM is already installed.%RESET%
    "%ASM_NASM:/=\%" -v
    goto :EOF
)
echo %YELLOW%[INFO] NASM is not installed.%RESET%
set /p nasm_ans="Install NASM now using winget? (Y/N): "
if /i "%nasm_ans%"=="Y" (
    echo %CYAN%[INFO] Installing NASM via winget...%RESET%
    winget install nasm --silent
    if errorlevel 1 (
         echo %RED%[ERROR] Failed to install NASM via winget.%RESET%
         pause
         goto :EOF
    ) else (
         echo %GREEN%[OK] NASM installed successfully.%RESET%
         goto :ConfigureNASM
    )
) else (
    echo %YELLOW%[INFO] Skipping NASM installation as per user choice.%RESET%
    goto :EOF
)

:ConfigureNASM
echo.
echo %CYAN%--- Configuring NASM Environment Variable --- %RESET%
echo.
echo %CYAN%[INFO] Setting ASM_NASM environment variable...%RESET%
setx ASM_NASM "C:/Program Files/NASM/nasm.exe" >nul 2>&1
if errorlevel 1 (
        echo %RED%[ERROR] Failed to set ASM_NASM environment variable. Please set it manually.%RESET%
) else (
        echo %GREEN%[OK] ASM_NASM environment variable set successfully.%RESET%
)

goto :EOF

:CheckRye
echo.
echo %CYAN%--- Checking for Rye --- %RESET%
rye --version >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK] Rye is installed.%RESET%
    rye --version
    goto :EOF
)
echo %YELLOW%[INFO] Rye is not installed.%RESET%
set /p ans="Install Rye automatically via Cargo? (Y/N): "
if /i "%ans%"=="Y" (
    cargo install --git https://github.com/astral-sh/rye rye
    if errorlevel 1 (
         echo %RED%[ERROR] Failed to install Rye via Cargo.%RESET%
         echo.
         echo %YELLOW%[INFO] To install Rye manually, please follow these steps:%RESET%
         echo   1. Download the Rye 64-bit installer from:
         echo      https://rye.astral.sh/guide/installation/
         echo   2. Run the installer and press Enter when prompted for each option to accept the default.
         pause
    ) else (
         echo %GREEN%[OK] Rye installed successfully.%RESET%
    )
) else (
    echo Skipping Rye installation.
)
goto :EOF

# AeroSim Windows installation

This guide demonstrates how to setup and build AeroSim in __Windows 11__.

* [__Setup accounts__](#set-up-your-accounts)
* [__Install prerequisites__](#install-build-tools-and-prerequisites)
    - [Install Rust](#install-rust)
    - [Install Make and CMake](#install-cmake)
    - [Install Rye](#install-rye)
    - [Install Git LFS](#install-git-large-file-system)
* [__Install Unreal Engine 5.3__](#install-unreal-engine-53)
* [__Build AeroSim__](#build-aerosim)
* [__Set up Cesium token__](#set-up-cesium-token)
* [__Verify installation__](#verify-installation)

## Set up your accounts

Before you start, you should set up the necessary accounts needed to gain access to the source code and assets needed by AeroSim:

* [__GitHub__](https://github.com/signup): AeroSim is hosted on GitHub and requires GitHub credentials
* [__Epic Games__](https://www.epicgames.com/id/register/date-of-birth): AeroSim requires the source code for the Unreal Engine 5.3
* [__Cesium__](https://ion.cesium.com/signup/): AeroSim sources 3D assets from Cesium

In order to authorise the download of the Unreal Engine 5.3 repository, you must link your GitHub account with Epic Games. Follow [this guide](https://www.unrealengine.com/en-US/ue-on-github) to link your accounts. You will need to provide your GitHub credentials (username and [token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)) to authorise the download. You may also wish to [connect to GitHub through SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

---

## Install build tools and prerequisites

### Install Rust

Download and run the installer for the 64-bit version from [here](https://www.rust-lang.org/tools/install). When prompted, select the option "Quick install via the Visual Studio Community installer".

### Install Make and CMake

Use WingGet to install Make:

```sh
winget install ezwinports.make
```

And Cmake:

```sh
winget install kitware.cmake
```

If you have Visual Studio installed or have the Visual Studio installer, you can install/use the `C++ CMake Tools` available as part of the `Desktop Development with C++` bundle.

### Install Rye

Download and use the Rye [64-bit installer](https://github.com/astral-sh/rye/releases/latest/download/rye-x86_64-windows.exe) following: [https://rye.astral.sh/guide/installation/](https://rye.astral.sh/guide/installation/).

Press enter when prompted for each installation option to choose the default option.

### Install Git Large File System

The Git Large File System is required to maintain source control over large files, such as those used for 3D environments and assets.

If you don't already have Git installed, you should first install Git. Download and run the installer found [here](https://gitforwindows.org).

With Git installed, download and install the 64-bit Git LFDS installer [here](https://git-lfs.com/). Verify the installation by running `git lfs version` in a terminal.

### Install Unreal Engine 5.3

To clone the Unreal Engine code, you need to connect your GitHub account to Epic Games to authorise the download.

```sh
git clone -b 5.3 --depth=1 https://github.com/EpicGames/UnrealEngine.git
```

You will be prompted to sign into your GitHub account to authorize the download of the repository.

Move into the root folder of the Unreal Engine repository and run the setup scripts:

```sh
Setup.bat
GenerateProjectFiles.bat
```

Inside this source folder open the UE5.sln file in Visual Studio (double click). In the build bar ensure that you have selected `Development Editor`, `Win64` and `UnrealBuildTool` option.

---

## Build AeroSim

After the prerequisites are installed and Unreal Engine 5.3 is successfully built, clone the AeroSim repository:

```sh
git clone https://github.com/aerosim-open/aerosim.git
```

After this is complete, enter the root directory of the repository and run the `install_aerosim.bat` script to install AeroSim.

```sh
cd aerosim
install_aerosim.bat
```

By default, this script will install the assets and the Unreal Engine and Omniverse plugins. If you are using a custom build, there are several options available:

* `-h`: Show help and quit
* `-prereqs`: Install prerequisites.
* `-dev`: Install development environment.
* `-unreal`: Install Unreal renderer integration.
* `-omniverse`: Install Omniverse integration.
* `-assets`: Install asset library.
* `-simulink`: Install Simulink integration.
* `-all`: Install everything.

---

## Set up Cesium token

To access Cesium assets, you will need to set up an access token. Log in to your Cesium account and go to the *Access Tokens* tab. If you don't already have a token, click on *Create Token* and create a new token with the default settings. Copy the token to the clipboard. Next locate the environment variables dialogue, click on the *Start* button and type *advanced system*, then open *View Advanced System Settings*. Add a new environment variable in either the *User* or *System* variables using the *New..* field. Name the environment variable `AEROSIM_CESIUM_TOKEN` and paste the token from Cesium into the *value* field.


---

## Verify installation

To verify the installation has completed successfully, execute the AeroSim launch script:

```sh
launch_aerosim.bat --unreal-editor
```

This script should launch the Unreal Engine editor interface. Next, in a new terminal activate the AeroSim virtual environment, which has all the Python dependencies installed:

```sh
.venv\Scripts\activate
```

Then run the `run_trajectories.py` Python script from within the examples folder:

```sh
python run_trajectories.py
```

In the Unreal Editor viewport, you should then see an aircraft model follow a set trajectory which is visialized in the interface. If this example runs successfully, your installation has been successful.

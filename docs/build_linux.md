# AeroSim Linux installation

This guide demonstrates how to setup and build AeroSim in __Ubuntu 22.04__.

* [__Set up accounts__](#set-up-your-accounts)
* [__Install prerequisites__](#install-build-tools-and-prerequisites)
    - [Install debian packages](#install-debian-packages)
    - [Install Rust](#install-rust)
    - [Install Rye](#install-rye)
    - [Install Git LFS](#install-git-large-file-system)
* [__Install Unreal Engine 5.3__](#clone-and-build-unreal-engine-53)
* [__Build AeroSim__](#build-aerosim)
* [__Set up Cesium token__](#set-up-cesium-token)
* [__Verify installation__](#verify-installation)

---

## Set up your accounts

Before you start, you should set up the necessary accounts needed to gain access to the source code and assets needed by AeroSim:

* [__GitHub__](https://github.com/signup): AeroSim is hosted on GitHub
* [__Epic Games__](https://www.epicgames.com/id/register/date-of-birth): AeroSim requires the source-code or installed-build for the Unreal Engine 5.3
* [__Cesium__](https://ion.cesium.com/signup/): AeroSim sources 3D assets from Cesium

In order to authorise the download of the Unreal Engine 5.3 repository, you must link your GitHub account with Epic Games. Follow [this guide](https://www.unrealengine.com/en-US/ue-on-github) to link your accounts. You will need to provide your GitHub credentials (username and [token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)) to authorise the download. You may also wish to [authorize to GitHub through SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

---

## Install prerequisites

### Install debian packages

Install the packages required for building AeroSim using apt:

```sh
sudo apt update
sudo apt install cmake build-essential libclang-dev openjdk-21-jdk
sudo apt install wget curl clang unzip
```

### Install Rust

AeroSim uses the Rust programming language to implement and build the simulation components, with bindings to wrap them in Python packages.

[Install Rust](https://doc.rust-lang.org/beta/book/ch01-01-installation.html#installing-rustup-on-linux-or-macos
) using `curl`:

```sh
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
```

Proceed with the standard installation (press Enter).

### Install Git Large File System:

AeroSim uses the Git Large File System to download large 3D asset files. Install and verify Git LFS with the following commands:


```sh
sudo apt install git-lfs
git lfs version
```

### Install Rye

AeroSim uses the Rye Python project and package management tool. Install Rye with the following commands:


```sh
curl -sSf https://rye.astral.sh/get | bash
```

Press enter when prompted with options to proceed with default options.

Add the Rye shims to the PATH:

`echo 'source "$HOME/.rye/env"' >> ~/.bashrc`

Reload the terminal to refresh paths

---

## Download Unreal Engine 5.3 or build from source

### Download Unreal Engine 5.3

Download Unreal Engine 5.3 for Linux from [this link](https://www.unrealengine.com/en-US/linux) and install it following the instructions.
Alternatively, you can follow the instructions in the next section to build from source.

### Clone and build Unreal Engine 5.3

To clone the Unreal Engine code, you need to connect your GitHub account to Epic Games to authorise the download.

```sh
git clone -b 5.3 --depth=1 git@github.com:EpicGames/UnrealEngine.git
```

Now build Unreal Engine 5.3, this process could take up to 3 hours.

```sh
./Setup.sh && ./GenerateProjectFiles.sh && make
```

Create an environment variable to locate the root folder of the Unreal Engine 5.3 repository, you may want to add this to your `.bashrc` profile.


```sh
export AEROSIM_UNREAL_ENGINE_ROOT=/path/to/UnrealEngine
```

---

## Build AeroSim

After the prerequisites are installed and Unreal Engine 5.3 is successfully built, clone the AeroSim repository:

```sh
git clone https://github.com/aerosim-open/aerosim.git
```

After this is complete, enter the root directory of the repository and run the `install_aerosim.sh` script to install AeroSim.

```sh
cd aerosim
source install_aerosim.sh
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

## Set up Cesium token

To access Cesium assets, you will need to set up an access token. Log in to your Cesium account and go to the *Access Tokens* tab. If you don't already have a token, click on *Create Token* and create a new token with the default settings. Copy the token into an environment variable named `AEROSIM_CESIUM_TOKEN` in the shell where you will execute the launch script:

```sh
export AEROSIM_CESIUM_TOKEN=<cesium_token>
```

You may want to add this to your `.bashrc` profile or to a virtual environment

## Verify installation

Once the build process has completed successfully, try launching AeroSim with the launch script. Open a terminal in the repository root directory:

```sh
./launch_aerosim.sh --unreal-editor
```

This should launch the Unreal Editor and the AeroSim project. Next, in a new terminal activate the AeroSim virtual environment, which has all the Python dependencies installed:

```sh
source .venv/bin/activate
```

Then run the `run_trajectories.py` Python script from within the examples folder:

```sh
cd examples
python run_trajectories.py
```

In the Unreal Editor viewport, you should then see an aircraft model follow a set trajectory which is visialized in the interface. If this example runs successfully, your installation has been successful.

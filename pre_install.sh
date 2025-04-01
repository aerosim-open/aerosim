#!/bin/bash
# AeroSim Interactive Setup Script
# This script checks for required packages and installs them if they are missing.


# ---------------------------
# Check if running as root; if not, use sudo for commands requiring administrative privileges.
# ---------------------------
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# ---------------------------
# Define Colors using printf for proper ANSI escape interpretation
# ---------------------------
RED=$(printf '\033[0;31m')
GREEN=$(printf '\033[0;32m')
YELLOW=$(printf '\033[1;33m')
BLUE=$(printf '\033[0;34m')
MAGENTA=$(printf '\033[0;35m')
NC=$(printf '\033[0m') # No Color

# ---------------------------
# Helper Function: Confirm prompt
# ---------------------------
confirm() {
    read -r -p "${YELLOW}$1 [Y/n]: ${NC}" response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY]|'')$ ]]; then
        return 0
    else
        return 1
    fi
}

# ---------------------------
# Starting Message: Account Setup
# ---------------------------
clear
echo -e "${BLUE}============================================================${NC}"
echo -e "${MAGENTA}           AeroSim Setup: Account & Package Installer${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "${GREEN}Step 1: Set Up Your Accounts${NC}"
echo -e "${BLUE}--------------------------------------------${NC}"
echo -e "${GREEN}Before you begin, please ensure you have set up the following accounts:${NC}"
echo -e "  • ${YELLOW}GitHub${NC}: AeroSim is hosted on GitHub."
echo -e "  • ${YELLOW}Epic Games${NC}: Required for accessing and building Unreal Engine."
echo -e "  • ${YELLOW}Cesium${NC}: AeroSim sources 3D assets from Cesium."
echo -e "${BLUE}--------------------------------------------${NC}"
echo ""
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo -e "${GREEN}Step 2: Install and Build Unreal Engine${NC}"
echo -e "${BLUE}--------------------------------------------${NC}"
echo -e "${GREEN}• Download Unreal Engine from Epic Games or clone it from the Epic Games Git repository.${NC}"
echo -e "${GREEN}• Follow the official build instructions to compile Unreal Engine.${NC}"
echo -e "${GREEN}• Set the environment variable AEROSIM_UNREAL_ENGINE_ROOT to your Unreal Engine installation directory."
echo -e "  (For example: export AEROSIM_UNREAL_ENGINE_ROOT=\"/opt/UnrealEngine-5.3\")${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo ""
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo -e "${GREEN}Step 3: Configure Cesium${NC}"
echo -e "${BLUE}--------------------------------------------${NC}"
echo -e "${GREEN}• After creating your Cesium account, generate a Cesium token for your project.${NC}"
echo -e "${GREEN}• Set the environment variable AEROSIM_CESIUM_TOKEN with your token to load photorealistic tiles from the Cesium server.${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo ""
read -rp "Press Enter to continue to the next step..."

# ---------------------------
# Check for apt Package Manager (Debian/Ubuntu based systems)
# ---------------------------
if ! command -v apt &>/dev/null; then
    echo -e "${RED}This script currently supports Debian-based systems (apt). Exiting.${NC}"
    exit 1
fi

# ---------------------------
# Step 4: Install Prerequisites
# ---------------------------
clear
echo -e "${GREEN}Step 4: Install Prerequisites${NC}"
echo -e "${BLUE}--------------------------------------------${NC}"
echo -e "${GREEN}This step will check for and, if necessary, install:${NC}"
echo -e "  - cmake    (${MAGENTA}https://cmake.org/download/${NC})"
echo -e "  - build-essential"
echo -e "  - libclang-dev"
echo -e "  - openjdk-21-jdk"
echo -e "  - wget"
echo -e "  - curl"
echo -e "  - clang"
echo -e "  - unzip"
echo -e "  - nasm"
echo ""
pause

echo ""
echo -e "${BLUE}Updating package lists...${NC}"
$SUDO apt update

# ---------------------------
# Array of Required Debian Packages
# ---------------------------
required_packages=("cmake" "build-essential" "libclang-dev" "openjdk-21-jdk" "wget" "curl" "clang" "unzip" "nasm")

# ---------------------------
# Function: Check and Install a Package
# ---------------------------
install_package() {
    package=$1
    if dpkg -s "$package" &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} $package is already installed."
    else
        if confirm "$package is not installed. Would you like to install $package?"; then
            echo -e "${BLUE}Installing $package...${NC}"
            $SUDO apt install -y "$package"
        else
            echo -e "${YELLOW}Skipping installation of $package.${NC}"
        fi
    fi
}

for pkg in "${required_packages[@]}"; do
    install_package "$pkg"
done

# ---------------------------
# Install Rust
# ---------------------------
echo ""
if command -v rustup &>/dev/null || command -v rustc &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Rust is already installed."
else
    if confirm "Rust (required for AeroSim simulation components) is not installed. Install Rust?"; then
        echo -e "${BLUE}Installing Rust using rustup...${NC}"
        curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
        echo -e "${GREEN}Rust installation initiated. Follow the on-screen instructions.${NC}"
    else
        echo -e "${YELLOW}Skipping Rust installation.${NC}"
    fi
fi

if command -v rustc &>/dev/null; then
    echo -e "${GREEN}Rust version: $(rustc --version)${NC}"
    if command -v cargo &>/dev/null; then
        echo -e "${GREEN}Cargo version: $(cargo --version)${NC}"
    fi
fi

# ---------------------------
# Install Git and Git Large File System (LFS)
# ---------------------------
echo ""
if command -v git &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Git is already installed."
    echo -e "${GREEN}Git version: $(git --version)${NC}"
else
    if confirm "Git is not installed. Would you like to install Git?"; then
        echo -e "${BLUE}Installing Git...${NC}"
        $SUDO apt install -y git
    else
        echo -e "${YELLOW}Skipping Git installation.${NC}"
    fi
fi

if command -v git-lfs &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Git LFS is already installed."
    echo -e "${GREEN}Git LFS version: $(git lfs version)${NC}"
else
    if confirm "Git LFS (required for downloading large 3D assets) is not installed. Install Git LFS?"; then
        echo -e "${BLUE}Installing Git LFS...${NC}"
        $SUDO apt install -y git-lfs
        git lfs install
        echo -e "${GREEN}Git LFS version: $(git lfs version)${NC}"
    else
        echo -e "${YELLOW}Skipping Git LFS installation.${NC}"
    fi
fi

# ---------------------------
# Install Rye (Python Project/Package Manager)
# ---------------------------
echo ""
if command -v rye &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Rye is already installed."
else
    if confirm "Rye (for managing Python projects) is not installed. Install Rye?"; then
        echo -e "${BLUE}Installing Rye...${NC}"
        curl -sSf https://rye.astral.sh/get | bash
        echo -e "${GREEN}Rye installation initiated. Follow the on-screen instructions.${NC}"
        if ! grep -q 'source "$HOME/.rye/env"' "$HOME/.bashrc"; then
            echo 'source "$HOME/.rye/env"' >> "$HOME/.bashrc"
            echo -e "${GREEN}Added Rye shims to your PATH in ~/.bashrc.${NC}"
        else
            echo -e "${GREEN}Rye shims are already present in ~/.bashrc.${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping Rye installation.${NC}"
    fi
fi

if command -v rye &>/dev/null; then
    echo -e "${GREEN}Rye version: $(rye --version)${NC}"
fi

# ---------------------------
# Install Bun
# ---------------------------
echo ""
if command -v bun &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Bun is already installed."
    echo -e "${GREEN}Bun version: $(bun --version)${NC}"
else
    if confirm "Bun is not installed. Would you like to install Bun?"; then
        echo -e "${BLUE}Installing Bun...${NC}"
        curl -fsSL https://bun.sh/install | bash
        echo -e "${GREEN}Bun installation initiated. Please follow the on-screen instructions if necessary.${NC}"
    else
        echo -e "${YELLOW}Skipping Bun installation.${NC}"
    fi
fi

# ---------------------------
# Install Docker
# ---------------------------
echo ""
if command -v docker &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Docker is already installed."
    echo -e "${GREEN}Docker version: $(docker --version)${NC}"
else
    echo -e "${BLUE}Docker is not installed. Installing Docker...${NC}"
    $SUDO apt-get update
    $SUDO apt-get install -y ca-certificates curl gnupg lsb-release
    $SUDO mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
    $SUDO apt-get update
    $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    echo -e "${GREEN}[OK]${NC} Docker installed successfully."
    echo -e "${GREEN}Docker version: $(docker --version)${NC}"
fi

# ---------------------------
# Completion Message
# ---------------------------
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${MAGENTA}Setup Completed!${NC}"
echo -e "${GREEN}Please restart your terminal or run 'source ~/.bashrc' to update your PATH.${NC}"
echo -e "${YELLOW}Enjoy using AeroSim!${NC}"
echo -e "${BLUE}============================================================${NC}"

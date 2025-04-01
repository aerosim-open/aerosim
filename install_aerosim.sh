#!/bin/bash
# AeroSim Interactive Installer
# This script interactively installs the AeroSim simulator environment.

# ----------------------------------
# Setup Colors using tput if stdout is a terminal
# ----------------------------------
if [ -t 1 ]; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    MAGENTA=$(tput setaf 5)
    NC=$(tput sgr0)
else
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    NC=""
fi

# ----------------------------------
# Define File Name and Paths
# ----------------------------------
INSTALL_SCRIPT="$(basename "$BASH_SOURCE")"
INSTALL_SCRIPT_PATH="$(realpath "$(dirname "$BASH_SOURCE")")"

# ----------------------------------
# Repository URLs and Git Prefix
# ----------------------------------
GIT_CLONE_PREFIX="https://github.com/"
AEROSIM_REPO_URL="aerosim-open/aerosim.git"
AEROSIM_UNREAL_PROJECT_REPO_URL="aerosim-open/aerosim-unreal-project.git"
AEROSIM_UNREAL_PLUGIN_URL="aerosim-open/aerosim-unreal-plugin.git"
AEROSIM_OMNIVERSE_KIT_APP_URL="aerosim-open/aerosim-omniverse-kit-app.git"
AEROSIM_OMNIVERSE_EXTENSION_URL="aerosim-open/aerosim-omniverse-extension.git"
AEROSIM_ASSETS_REPO_URL="aerosim-open/aerosim-assets.git"
AEROSIM_ASSETS_UNREAL_REPO_URL="aerosim-open/aerosim-assets-unreal.git"
AEROSIM_SIMULINK_REPO_URL="aerosim-open/aerosim-simulink.git"
AEROSIM_APP_REPO_URL="aerosim-open/aerosim-app.git"

# ----------------------------------
# Help Function
# ----------------------------------
show_help() {
    echo ""
    echo "Usage: $INSTALL_SCRIPT [-h|--help] [-dev] [-unreal] [-omniverse] [-assets] [-simulink] [-app] [-pixelstreaming] [-all]"
    echo ""
    echo "Parameters:"
    echo "   -h, --help       Show this help message and exit."
    echo "   -dev             Install development environment."
    echo "   -unreal          Install Unreal renderer integration."
    echo "   -omniverse       Install Omniverse integration."
    echo "   -assets          Install asset library."
    echo "   -simulink        Install Simulink integration."
    echo "   -app             Install application."
    echo "   -pixelstreaming  Install Pixel Streaming."
    echo "   -all             Install everything."
    echo ""
    exit 0
}

# ----------------------------------
# Detect Existing AeroSim Repo Folder
# ----------------------------------
if [ -f "$INSTALL_SCRIPT_PATH/.git/config" ]; then
    if grep -q "$AEROSIM_REPO_URL" "$INSTALL_SCRIPT_PATH/.git/config"; then
        AEROSIM_REPO_FOLDER=$(basename "$INSTALL_SCRIPT_PATH")
        echo -e "${GREEN}Existing AeroSim repo found: $AEROSIM_REPO_FOLDER/${NC}"
        if [ "$(pwd)" = "$INSTALL_SCRIPT_PATH" ]; then
            cd ..
            echo -e "${YELLOW}Script was run inside an AeroSim repo folder. Changing working directory to: $(pwd)${NC}"
        fi
    fi
else
    AEROSIM_REPO_FOLDER="aerosim"
fi

WORKING_DIR=$(pwd)
CREATED_ENV_VARS=()

# ----------------------------------
# Print Banner (ASCII Art like Windows)
# ----------------------------------
clear
echo -e "${MAGENTA}        ___                 _____  _          ${NC}"
echo -e "${MAGENTA}       /   | ___  ________ / ___/ (_)___ ___   ${NC}"
echo -e "${MAGENTA}      / /| |/ _ \/ ___/ __ \\__  \/ / __ \`__ \  ${NC}"
echo -e "${MAGENTA}     / ___ /  __/ /  / /_/ /__/ / / / / / / /  ${NC}"
echo -e "${MAGENTA}    /_/  |_\___/_/   \____/____/_/_/ /_/ /_/   ${NC}"
echo ""

# ----------------------------------
# Installation Functions
# ----------------------------------

install_dev() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Development Environment -----${NC}"
    if [ -d "$AEROSIM_REPO_FOLDER" ]; then
        echo -e "${GREEN}AeroSim repo already exists at '$AEROSIM_REPO_FOLDER/'. Skipping clone.${NC}"
        echo -e "${YELLOW}Updating repository...${NC}"
        (cd "$AEROSIM_REPO_FOLDER" && git pull)
    else
        echo -e "${YELLOW}Cloning AeroSim repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_REPO_URL}" "$AEROSIM_REPO_FOLDER"
    fi
    AEROSIM_ROOT="$WORKING_DIR/$AEROSIM_REPO_FOLDER"
    export AEROSIM_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_ROOT=$AEROSIM_ROOT")
    echo -e "${GREEN}AEROSIM_ROOT set to: $AEROSIM_ROOT${NC}"
    AEROSIM_WORLD_LINK_LIB="$AEROSIM_ROOT/aerosim-world-link/lib"
    export AEROSIM_WORLD_LINK_LIB
    CREATED_ENV_VARS+=("export AEROSIM_WORLD_LINK_LIB=$AEROSIM_WORLD_LINK_LIB")
    echo -e "${GREEN}AEROSIM_WORLD_LINK_LIB set to: $AEROSIM_WORLD_LINK_LIB${NC}"
}

install_unreal() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Unreal Integration -----${NC}"
    if [ -d "aerosim-unreal-project" ]; then
        echo -e "${GREEN}AeroSim Unreal project repo already exists. Skipping clone.${NC}"
    else
        echo -e "${YELLOW}Cloning AeroSim Unreal project repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_UNREAL_PROJECT_REPO_URL}" "aerosim-unreal-project"
    fi
    if [ -d "aerosim-unreal-project" ]; then
        pushd aerosim-unreal-project/Plugins > /dev/null
        if [ -d "aerosim-unreal-plugin" ]; then
            echo -e "${GREEN}AeroSim Unreal plugin repo already exists. Skipping clone.${NC}"
        else
            echo -e "${YELLOW}Cloning AeroSim Unreal plugin repository...${NC}"
            git clone "${GIT_CLONE_PREFIX}${AEROSIM_UNREAL_PLUGIN_URL}" "aerosim-unreal-plugin"
        fi
        popd > /dev/null
    fi
    AEROSIM_UNREAL_PROJECT_ROOT="$WORKING_DIR/aerosim-unreal-project"
    export AEROSIM_UNREAL_PROJECT_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_UNREAL_PROJECT_ROOT=$AEROSIM_UNREAL_PROJECT_ROOT")
    echo -e "${GREEN}AEROSIM_UNREAL_PROJECT_ROOT set to: $AEROSIM_UNREAL_PROJECT_ROOT${NC}"
}

install_omniverse() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Omniverse Integration -----${NC}"
    if [ -d "aerosim-omniverse-kit-app" ]; then
        echo -e "${GREEN}AeroSim Omniverse Kit App repo already exists. Skipping clone.${NC}"
    else
        echo -e "${YELLOW}Cloning AeroSim Omniverse Kit App repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_OMNIVERSE_KIT_APP_URL}" "aerosim-omniverse-kit-app"
    fi
    if [ -d "aerosim-omniverse-kit-app" ]; then
        mkdir -p aerosim-omniverse-kit-app/source/extensions
        pushd aerosim-omniverse-kit-app/source/extensions > /dev/null
        if [ -d "aerosim.omniverse.extension" ]; then
            echo -e "${GREEN}AeroSim Omniverse extension repo already exists. Skipping clone.${NC}"
        else
            echo -e "${YELLOW}Cloning AeroSim Omniverse extension repository...${NC}"
            git clone "${GIT_CLONE_PREFIX}${AEROSIM_OMNIVERSE_EXTENSION_URL}" "aerosim.omniverse.extension"
        fi
        popd > /dev/null
    fi
    AEROSIM_OMNIVERSE_ROOT="$WORKING_DIR/aerosim-omniverse-kit-app"
    export AEROSIM_OMNIVERSE_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_OMNIVERSE_ROOT=$AEROSIM_OMNIVERSE_ROOT")
    echo -e "${GREEN}AEROSIM_OMNIVERSE_ROOT set to: $AEROSIM_OMNIVERSE_ROOT${NC}"
}

install_assets() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Asset Library -----${NC}"
    if [ "$UNREAL_FLAG" = true ]; then
        echo -e "${GREEN}Installing Unreal-native assets to: $AEROSIM_UNREAL_PROJECT_ROOT/Plugins${NC}"
        if [ -d "$AEROSIM_UNREAL_PROJECT_ROOT/Plugins" ]; then
            pushd "$AEROSIM_UNREAL_PROJECT_ROOT/Plugins" > /dev/null
            if [ -d "aerosim-assets-unreal" ]; then
                echo -e "${GREEN}AeroSim asset library (Unreal) already exists. Skipping clone.${NC}"
            else
                echo -e "${YELLOW}Cloning AeroSim Unreal asset library repository...${NC}"
                git clone "${GIT_CLONE_PREFIX}${AEROSIM_ASSETS_UNREAL_REPO_URL}" "aerosim-assets-unreal"
            fi
            popd > /dev/null
            AEROSIM_ASSETS_UNREAL_ROOT="$AEROSIM_UNREAL_PROJECT_ROOT/Plugins/aerosim-assets-unreal"
            export AEROSIM_ASSETS_UNREAL_ROOT
            CREATED_ENV_VARS+=("export AEROSIM_ASSETS_UNREAL_ROOT=$AEROSIM_ASSETS_UNREAL_ROOT")
            echo -e "${GREEN}AEROSIM_ASSETS_UNREAL_ROOT set to: $AEROSIM_ASSETS_UNREAL_ROOT${NC}"
        fi
    fi
    echo ""
    echo -e "${GREEN}Installing USD assets to: $WORKING_DIR/aerosim-assets${NC}"
    if [ -d "aerosim-assets" ]; then
        echo -e "${GREEN}AeroSim USD asset library repo already exists. Skipping clone.${NC}"
    else
        echo -e "${YELLOW}Cloning AeroSim USD asset library repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_ASSETS_REPO_URL}" "aerosim-assets"
    fi
    AEROSIM_ASSETS_ROOT="$WORKING_DIR/aerosim-assets"
    export AEROSIM_ASSETS_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_ASSETS_ROOT=$AEROSIM_ASSETS_ROOT")
    echo -e "${GREEN}AEROSIM_ASSETS_ROOT set to: $AEROSIM_ASSETS_ROOT${NC}"
}

install_simulink() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Simulink Integration -----${NC}"
    if [ -d "aerosim-simulink" ]; then
        echo -e "${GREEN}AeroSim Simulink repo already exists. Skipping clone.${NC}"
    else
        echo -e "${YELLOW}Cloning AeroSim Simulink repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_SIMULINK_REPO_URL}" "aerosim-simulink"
    fi
    AEROSIM_SIMULINK_ROOT="$WORKING_DIR/aerosim-simulink"
    export AEROSIM_SIMULINK_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_SIMULINK_ROOT=$AEROSIM_SIMULINK_ROOT")
    echo -e "${GREEN}AEROSIM_SIMULINK_ROOT set to: $AEROSIM_SIMULINK_ROOT${NC}"
}

install_app() {
    echo ""
    echo -e "${BLUE}----- Installing AeroSim Application -----${NC}"
    if [ -d "aerosim-app" ]; then
        echo -e "${GREEN}AeroSim app repo already exists. Skipping clone.${NC}"
    else
        echo -e "${YELLOW}Cloning AeroSim app repository...${NC}"
        git clone "${GIT_CLONE_PREFIX}${AEROSIM_APP_REPO_URL}" "aerosim-app"
    fi
    echo -e "${YELLOW}Installing app dependencies...${NC}"
    (cd aerosim-app && bun install)
    AEROSIM_APP_ROOT="$WORKING_DIR/aerosim-app"
    export AEROSIM_APP_ROOT
    CREATED_ENV_VARS+=("export AEROSIM_APP_ROOT=$AEROSIM_APP_ROOT")
    AEROSIM_APP_WS_PORT=5001
    export AEROSIM_APP_WS_PORT
    CREATED_ENV_VARS+=("export AEROSIM_APP_WS_PORT=$AEROSIM_APP_WS_PORT")
    echo -e "${GREEN}AEROSIM_APP_ROOT set to: $AEROSIM_APP_ROOT${NC}"
    echo -e "${GREEN}AEROSIM_APP_WS_PORT set to: $AEROSIM_APP_WS_PORT${NC}"
}

install_pixelstreaming() {
    echo ""
    echo -e "${BLUE}----- Installing Pixel Streaming -----${NC}"
    echo -e "${YELLOW}TODO...${NC}"
    echo -e "${GREEN}Pixel Streaming dependencies installed.${NC}"
}

# ----------------------------------
# Main Menu Loop
# ----------------------------------
ALL_MODE=false

# Process command line arguments if any
if [ $# -gt 0 ]; then
    # Reset all flags
    DEV_FLAG=false
    UNREAL_FLAG=false
    OMNIVERSE_FLAG=false
    ASSETS_FLAG=false
    SIMULINK_FLAG=false
    APP_FLAG=false
    PIXEL_STREAMING_FLAG=false
    CLI_MODE=true

    # Parse arguments
    for arg in "$@"; do
        case $arg in
            -h|--help)
                show_help
                ;;
            -dev)
                DEV_FLAG=true
                ;;
            -unreal)
                UNREAL_FLAG=true
                ;;
            -omniverse)
                OMNIVERSE_FLAG=true
                ;;
            -assets)
                ASSETS_FLAG=true
                ;;
            -simulink)
                SIMULINK_FLAG=true
                ;;
            -app)
                APP_FLAG=true
                ;;
            -pixelstreaming)
                PIXEL_STREAMING_FLAG=true
                ;;
            -all)
                DEV_FLAG=true
                UNREAL_FLAG=true
                OMNIVERSE_FLAG=true
                ASSETS_FLAG=true
                SIMULINK_FLAG=true
                APP_FLAG=true
                PIXEL_STREAMING_FLAG=true
                ALL_MODE=true
                ;;
            *)
                echo -e "${RED}Unknown argument: $arg${NC}"
                show_help
                ;;
        esac
    done

    # If Unreal integration is selected, check AEROSIM_UNREAL_ENGINE_ROOT
    if [ "$UNREAL_FLAG" = true ]; then
        if [ -z "$AEROSIM_UNREAL_ENGINE_ROOT" ]; then
            echo -e "${RED}ERROR: Please set the AEROSIM_UNREAL_ENGINE_ROOT environment variable to your Unreal Engine installation path.${NC}"
            exit 1
        else
            echo -e "${GREEN}AEROSIM_UNREAL_ENGINE_ROOT is set to: $AEROSIM_UNREAL_ENGINE_ROOT${NC}"
        fi
    fi

    # Run Installations based on flags
    if [ "$DEV_FLAG" = true ]; then
        install_dev
    fi
    if [ "$UNREAL_FLAG" = true ]; then
        install_unreal
    fi
    if [ "$OMNIVERSE_FLAG" = true ]; then
        install_omniverse
    fi
    if [ "$ASSETS_FLAG" = true ]; then
        install_assets
    fi
    if [ "$SIMULINK_FLAG" = true ]; then
        install_simulink
    fi
    if [ "$APP_FLAG" = true ]; then
        install_app
    fi
    if [ "$PIXEL_STREAMING_FLAG" = true ]; then
        install_pixelstreaming
    fi

    # Display environment variables and exit
    echo ""
    echo -e "${BLUE}----- Installation Complete -----${NC}"
    echo -e "${GREEN}The following AeroSim environment variables have been set:${NC}"
    echo "--------------------------------------------"
    for var in "${CREATED_ENV_VARS[@]}"; do
        echo "$var"
    done
    echo "--------------------------------------------"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Add the above exports to your shell's rc file (e.g. ~/.bashrc or ~/.zshrc) to persist them.${NC}"
    exit 0
else
    # Interactive mode - continue with the existing menu loop
    while true; do
        echo ""
        echo -e "${BLUE}=============================================${NC}"
        echo -e "${MAGENTA}         AeroSim Interactive Installer       ${NC}"
        echo -e "${BLUE}=============================================${NC}"
        echo ""
        echo -e "${GREEN}Select the components to install:${NC}"
        echo -e "${YELLOW}[0] Install All Packages${NC}"
        echo -e "${YELLOW}[1] AeroSim Development Environment${NC}"
        echo -e "${YELLOW}[2] Unreal Integration${NC}"
        echo -e "${YELLOW}[3] Omniverse Integration${NC}"
        echo -e "${YELLOW}[4] AeroSim Asset Library${NC}"
        echo -e "${YELLOW}[5] Simulink Integration${NC}"
        echo -e "${YELLOW}[6] AeroSim Application${NC}"
        echo -e "${YELLOW}[7] Pixel Streaming${NC}"
        echo -e "${YELLOW}[8] Exit Installation${NC}"
        echo ""
        read -rp "${YELLOW}Enter option numbers separated by space: ${NC}" options

        # Reset all flags
        DEV_FLAG=false
        UNREAL_FLAG=false
        OMNIVERSE_FLAG=false
        ASSETS_FLAG=false
        SIMULINK_FLAG=false
        APP_FLAG=false
        PIXEL_STREAMING_FLAG=false

        if [[ " $options " =~ " 0 " ]]; then
            DEV_FLAG=true
            UNREAL_FLAG=true
            OMNIVERSE_FLAG=true
            ASSETS_FLAG=true
            SIMULINK_FLAG=true
            APP_FLAG=true
            PIXEL_STREAMING_FLAG=true
            ALL_MODE=true
        else
            for opt in $options; do
                case $opt in
                    1) DEV_FLAG=true ;;
                    2) UNREAL_FLAG=true ;;
                    3) OMNIVERSE_FLAG=true ;;
                    4) ASSETS_FLAG=true ;;
                    5) SIMULINK_FLAG=true ;;
                    6) APP_FLAG=true ;;
                    7) PIXEL_STREAMING_FLAG=true ;;
                    8) echo -e "${YELLOW}Exiting installation.${NC}"; exit 0 ;;
                    *) echo -e "${YELLOW}Unknown option: $opt. Skipping.${NC}" ;;
                esac
            done
        fi

        # If Unreal integration is selected, check AEROSIM_UNREAL_ENGINE_ROOT
        if [ "$UNREAL_FLAG" = true ]; then
            if [ -z "$AEROSIM_UNREAL_ENGINE_ROOT" ]; then
                echo -e "${RED}ERROR: Please set the AEROSIM_UNREAL_ENGINE_ROOT environment variable to your Unreal Engine installation path.${NC}"
                exit 1
            else
                echo -e "${GREEN}AEROSIM_UNREAL_ENGINE_ROOT is set to: $AEROSIM_UNREAL_ENGINE_ROOT${NC}"
            fi
        fi

        # Run Installations
        if [ "$DEV_FLAG" = true ]; then
            install_dev
        fi
        if [ "$UNREAL_FLAG" = true ]; then
            install_unreal
        fi
        if [ "$OMNIVERSE_FLAG" = true ]; then
            install_omniverse
        fi
        if [ "$ASSETS_FLAG" = true ]; then
            install_assets
        fi
        if [ "$SIMULINK_FLAG" = true ]; then
            install_simulink
        fi
        if [ "$APP_FLAG" = true ]; then
            install_app
        fi
        if [ "$PIXEL_STREAMING_FLAG" = true ]; then
            install_pixelstreaming
        fi

        # If ALL_MODE is true, exit without looping back.
        if [ "$ALL_MODE" = true ]; then
            break
        fi

        echo ""
        read -rp "${YELLOW}Press Enter to return to the Main Menu...${NC}"
    done

    # ----------------------------------
    # Final Message: Display Environment Variables
    # ----------------------------------
    echo ""
    echo -e "${BLUE}----- Installation Complete -----${NC}"
    echo -e "${GREEN}The following AeroSim environment variables have been set:${NC}"
    echo "--------------------------------------------"
    for var in "${CREATED_ENV_VARS[@]}"; do
        echo "$var"
    done
    echo "--------------------------------------------"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Add the above exports to your shell's rc file (e.g. ~/.bashrc or ~/.zshrc) to persist them.${NC}"
    exit 0
fi

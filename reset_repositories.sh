#!/bin/bash

echo "Reset aerosim and all related repositories by running 'git clean -fdx' and 'git reset --hard' in the following repositories:"
echo
echo "  aerosim repo: $AEROSIM_ROOT"
echo "  aerosim-app repo: $AEROSIM_APP_ROOT"
echo "  aerosim-assets repo: $AEROSIM_ASSETS_ROOT"
echo "  aerosim-omniverse-kit-app repo: $AEROSIM_OMNIVERSE_ROOT"
echo "  aerosim-omniverse-extension repo: $AEROSIM_OMNIVERSE_ROOT/source/extensions/aerosim.omniverse.extension"
echo "  aerosim-unreal-plugin repo: $AEROSIM_UNREAL_PLUGIN_ROOT"
echo "  aerosim-unreal-project repo: $AEROSIM_UNREAL_PROJECT_ROOT"
echo "  aerosim-assets-unreal repo: $AEROSIM_ASSETS_UNREAL_ROOT"
echo "  aerosim-simulink repo: $AEROSIM_SIMULINK_ROOT"
echo
echo "WARNING: This will delete any uncommitted changes in all repositories"
read -p "Do you want to continue? (Y/N): " choice

case $choice in
    [yY])
        ;;
    *)
        exit 1
        ;;
esac

# Function to perform git clean/reset in a repo
resetrepo () {
    echo
    echo "Resetting $1 repo..."
    if [ "$2" == "" ] || [ ! -d $2 ]; then
        echo "WARNING $1 repo not found at: $2"
        echo "Skipping $1 repo."
    else
        pushd $2 > /dev/null
        echo "Running 'git clean -fdx' in $PWD"
        git clean -fdx
        echo "Running 'git reset --hard' in $PWD"
        git reset --hard
        popd > /dev/null
    fi
}

resetrepo "aerosim" $AEROSIM_ROOT
resetrepo "aerosim-app" $AEROSIM_APP_ROOT
resetrepo "aerosim-assets" $AEROSIM_ASSETS_ROOT
resetrepo "aerosim-omniverse-kit-app" $AEROSIM_OMNIVERSE_ROOT
resetrepo "aerosim-omniverse-extension" $AEROSIM_OMNIVERSE_ROOT/source/extensions/aerosim.omniverse.extension
resetrepo "aerosim-unreal-plugin" $AEROSIM_UNREAL_PLUGIN_ROOT
resetrepo "aerosim-unreal-project" $AEROSIM_UNREAL_PROJECT_ROOT
resetrepo "aerosim-assets-unreal" $AEROSIM_ASSETS_UNREAL_ROOT
resetrepo "aerosim-simulink" $AEROSIM_SIMULINK_ROOT

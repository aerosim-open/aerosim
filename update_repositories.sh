#!/bin/bash

echo "Updating aerosim and related repositories"

# Function to perform git pull in a repo
pullrepo() {
    echo "$1"
    cd "$2" || exit
    echo "$(pwd)"
    git pull
    git branch
}

# Call the function for each repository
pullrepo "aerosim" "$AEROSIM_ROOT"
pullrepo "aerosim-app" "$AEROSIM_APP_ROOT"
pullrepo "aerosim-assets" "$AEROSIM_ASSETS_ROOT"
pullrepo "aerosim-omniverse-kit-app" "$AEROSIM_OMNIVERSE_ROOT"
pullrepo "aerosim-unreal-project" "$AEROSIM_UNREAL_PROJECT_ROOT"
pullrepo "aerosim-assets-unreal" "$AEROSIM_ASSETS_UNREAL_ROOT"
pullrepo "aerosim-unreal-plugin" "$AEROSIM_UNREAL_PLUGIN_ROOT"

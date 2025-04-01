#!/bin/bash

# Exit on error
set -e

# This script is used to launch Aerosim and all the required services
echo "AEROSIM_ROOT: $AEROSIM_ROOT"

# Define file name
FILE_N="$(basename "$0")"

# Print batch params (debug purpose)
# echo "$FILE_N params: $*"

# ============================================================================
# Parse arguments
# ============================================================================

DOC_STRING="Launch Aerosim."
USAGE_STRING="Usage: $FILE_N [--help] [--unreal] [--unreal-editor] [--unreal-editor-nogui] [--omniverse] [--pixel-streaming] [--pixel-streaming-ip={127.0.0.1}] [--pixel-streaming-port={8888}] [--config={Debug,Development,Shipping}] [--renderer-ids={\"0,1,2\"}] [--kafka-tmpfs] [--kafka-tmpfs-size={5G}]"

REMOVE_INTERMEDIATE=false
LAUNCH_UNREAL_EDITOR_NOGUI=false
LAUNCH_UNREAL_EDITOR=false
LAUNCH_UNREAL_PACKAGE=false
LAUNCH_OMNIVERSE=false
PACKAGE_CONFIG="Development"
PIXEL_STREAMING=false
PIXEL_STREAMING_IP="127.0.0.1"
PIXEL_STREAMING_PORT=8888
# Create tmpfs in RAM for Kafka to allow faster I/O operations
KAFKA_TMPFS=false
KAFKA_TMPFS_SIZE="5G"
# Default to a single renderer instance with ID="0"
RENDERER_IDS="0"

# Parse arguments
while [[ $# -gt 0 ]]; do
    i="$1"
    case $i in
        --unreal)
            LAUNCH_UNREAL_PACKAGE=true
            LAUNCH_UNREAL_EDITOR=false
            LAUNCH_UNREAL_EDITOR_NOGUI=false
            LAUNCH_OMNIVERSE=false
            shift
            ;;
        --unreal-editor)
            LAUNCH_UNREAL_PACKAGE=false
            LAUNCH_UNREAL_EDITOR=true
            LAUNCH_UNREAL_EDITOR_NOGUI=false
            LAUNCH_OMNIVERSE=false
            shift
            ;;
        --unreal-editor-nogui)
            LAUNCH_UNREAL_PACKAGE=false
            LAUNCH_UNREAL_EDITOR=false
            LAUNCH_UNREAL_EDITOR_NOGUI=true
            LAUNCH_OMNIVERSE=false
            shift
            ;;
        --omniverse)
            LAUNCH_UNREAL_PACKAGE=false
            LAUNCH_UNREAL_EDITOR=false
            LAUNCH_UNREAL_EDITOR_NOGUI=false
            LAUNCH_OMNIVERSE=true
            shift
            ;;
        --config=*)
            PACKAGE_CONFIG="${i#*=}"
            shift
            ;;
        --pixel-streaming)
            PIXEL_STREAMING=true
            shift
            ;;
        --pixel-streaming-ip=*)
            PIXEL_STREAMING_IP="${i#*=}"
            shift
            ;;
        --pixel-streaming-port=*)
            PIXEL_STREAMING_PORT="${i#*=}"
            shift
            ;;
        --renderer-ids=*)
            RENDERER_IDS="${i#*=}"
            shift
            ;;
        --kafka-tmpfs)
            KAFKA_TMPFS=true
            shift
            ;;
        --kafka-tmpfs-size=*)
            KAFKA_TMPFS_SIZE="${i#*=}"
            shift
            ;;
        --setup)
            FULL_SETUP=true
            shift
            ;;
        --help)
            echo "$DOC_STRING"
            echo "$USAGE_STRING"
            exit 0
            ;;
        *)
            echo "Unknown option: $i"
            echo "$USAGE_STRING"
            exit 1
            ;;
    esac
done


# Function to find an available terminal emulator
find_terminal_emulator() {
    # List of common terminal emulators to try
    terminals=("gnome-terminal" "konsole" "xfce4-terminal" "xterm")

    # First check if x-terminal-emulator exists and what it points to
    if command -v "x-terminal-emulator" >/dev/null 2>&1; then
        # Try to determine what x-terminal-emulator points to
        real_terminal=$(readlink -f $(which x-terminal-emulator) 2>/dev/null)
        if [ -n "$real_terminal" ]; then
            base_name=$(basename "$real_terminal")
            # Check if it's one of our known terminals
            for term in "${terminals[@]}"; do
                if [[ "$base_name" == "$term"* ]]; then
                    echo "$term"
                    return 0
                fi
            done
            # If it's terminator, prefer gnome-terminal if available
            if [[ "$base_name" == "terminator"* ]]; then
                if command -v "gnome-terminal" >/dev/null 2>&1; then
                    echo "gnome-terminal"
                    return 0
                fi
            fi
            # Otherwise, return the actual terminal name for special handling
            echo "$base_name"
            return 0
        fi
        # If we couldn't determine what it points to, just use x-terminal-emulator
        echo "x-terminal-emulator"
        return 0
    fi

    # Try each terminal until one is found
    for term in "${terminals[@]}"; do
        if command -v "$term" >/dev/null 2>&1; then
            echo "$term"
            return 0
        fi
    done

    return 1
}

# Function to launch a terminal with the given command
launch_terminal() {
    local title="$1"
    local cmd="$2"
    local instance_id="$3"
    local terminal
    local escaped_cmd
    
    local fallback_logfile=${title//[^a-zA-Z0-9]/_} # sanitize title to use as a filename
    fallback_logfile="${fallback_logfile,,}" # convert to lowercase
    if [ -n "$instance_id" ]; then
        fallback_logfile="${fallback_logfile}_${instance_id}"
    fi

    # Ensure critical environment variables are preserved
    local env_vars=""
    if [ -n "$AEROSIM_CESIUM_TOKEN" ]; then
        env_vars="AEROSIM_CESIUM_TOKEN='$AEROSIM_CESIUM_TOKEN' "
    fi

    # Add other important environment variables here if needed
    if [ -n "$AEROSIM_UNREAL_ENGINE_ROOT" ]; then
        env_vars+="AEROSIM_UNREAL_ENGINE_ROOT='$AEROSIM_UNREAL_ENGINE_ROOT' "
    fi

    # Modify command to include a pause after execution and preserve environment variables
    # This ensures the terminal stays open to show errors
    modified_cmd="${env_vars}$cmd"

    # Escape the command for shell interpretation
    escaped_cmd=$(printf "%q " "$modified_cmd")

    # Attempt to find an available terminal emulator. If this function fails (no terminal emulator available),
    # return an empty string to fall back to running the command directly in the background.
    terminal=$(find_terminal_emulator || echo "")

    if [ -n "$terminal" ]; then
        echo "Using terminal: $terminal"
        case "$terminal" in
            "gnome-terminal")
                # gnome-terminal handles quoting differently
                "$terminal" --title="$title $instance_id" -- bash -c "$modified_cmd" &
                ;;
            "konsole")
                # konsole needs explicit escaping
                "$terminal" --new-tab --title="$title $instance_id" -e bash -c "$escaped_cmd" &
                ;;
            "xfce4-terminal")
                # xfce4-terminal similar to konsole
                "$terminal" --title="$title $instance_id" -x bash -c "$escaped_cmd" &
                ;;
            "terminator")
                # terminator is similar to gnome-terminal
                "$terminal" --title="$title $instance_id" -e "$modified_cmd" &
                ;;
            "x-terminal-emulator")
                # If we couldn't determine the actual terminal, try the most compatible approach
                "$terminal" -e bash -c "$modified_cmd" &
                ;;
            *)
                # Default fallback for xterm and others
                "$terminal" -T "$title $instance_id" -e bash -c "$escaped_cmd" &
                ;;
        esac
        # Small sleep to ensure terminals don't conflict with each other on startup
        sleep 0.5
    else
        echo "Warning: No suitable terminal emulator found. Running command directly..."
        # Run in background with output redirected to file
        eval "${env_vars}$cmd" > "${fallback_logfile}.log" 2>&1 &
        echo "Command running in background. Output redirected to ${fallback_logfile}.log"
    fi
}

# ============================================================================
# Build UE5 from source if requested
# ============================================================================

if [ "$FULL_SETUP" = true ]; then
    # Check if AEROSIM_UNREAL_ENGINE_ROOT environment variable is set
    if [ -z "$AEROSIM_UNREAL_ENGINE_ROOT" ]; then
        echo "[launch_aerosim.sh] Error: AEROSIM_UNREAL_ENGINE_ROOT is not set. Unable to run UE5 setup process."
        exit 1
    else
        # Change directory to Unreal Engine setup path
        cd "$AEROSIM_UNREAL_ENGINE_ROOT"
        echo "[launch_aerosim.sh] Running UE5 setup process"

        # Run the UE5 setup and generate project files
        ./Setup.sh
        ./GenerateProjectFiles.sh
        make
    fi

    # Return to the original simulator directory
    cd $AEROSIM_ROOT
fi

# ============================================================================
# Start a local Kafka server
# ============================================================================

echo "Starting Kafka..."
pushd kafka > /dev/null
bash get_kafka.sh $KAFKA_TMPFS $KAFKA_TMPFS_SIZE
launch_terminal "AeroSim Kafka Server" "bash run_kafka_local.sh localhost $KAFKA_TMPFS"
popd > /dev/null

# ============================================================================
# Handle packaging Unreal binary and launching Pixel Streaming webservers
# ============================================================================

LAUNCH_UNREAL=false
if [ "$LAUNCH_UNREAL_PACKAGE" = true ] || [ "$LAUNCH_UNREAL_EDITOR" = true ] || [ "$LAUNCH_UNREAL_EDITOR_NOGUI" = true ]; then
    LAUNCH_UNREAL=true
fi

if [ "$LAUNCH_UNREAL" = true ]; then
    # Package the Unreal binary if it does not already exist
    if [ "$LAUNCH_UNREAL_PACKAGE" = true ]; then
        if [ -f "$AEROSIM_UNREAL_PROJECT_ROOT/package-$PACKAGE_CONFIG/Linux/AerosimUE5.sh" ]; then
            echo "AerosimUE5 is already packaged."
        else
            echo "Starting AerosimUE5 packaging..."
            pushd "$AEROSIM_UNREAL_PROJECT_ROOT" > /dev/null
            ./package.sh --config=$PACKAGE_CONFIG
            popd > /dev/null
        fi
    fi

    # Launch the Pixel Streaming webservers
    if [ "$PIXEL_STREAMING" = true ]; then
        SSSProcessName="Start_SignallingServer.sh"
        if pgrep -f "$SSSProcessName" > /dev/null; then
            echo "SignallingWebServer is already running. Please close the process before running the script."
            pkill -f "$SSSProcessName"
            if [ $? -eq 0 ]; then
                echo "Killed the process $SSSProcessName. Make sure next time to close the process before running the script."
            else
                echo "ERROR: Could not kill the process $SSSProcessName. Please make sure the process is not running."
                exit 2
            fi
        fi

        if [ "$LAUNCH_UNREAL_PACKAGE" = true ]; then
            # Launching Pixel Streaming webservers from an Unreal packaged binary
            WEBSERVERS_PATH=$AEROSIM_UNREAL_PROJECT_ROOT/package-$PACKAGE_CONFIG/Linux/AerosimUE5/Samples/PixelStreaming/WebServers
        else
            # Launching Pixel Streaming webservers from an Unreal Editor
            WEBSERVERS_PATH=$AEROSIM_UNREAL_ENGINE_ROOT/Engine/Plugins/Media/PixelStreaming/Resources/WebServers
        fi

        cd $WEBSERVERS_PATH

        # Download the SignallingWebServer if it does not already exist
        if [ -d "SignallingWebServer" ]; then
            echo "SignallingWebServer already exists. Skipping download."
        else
            echo "SignallingWebServer does not exist. Downloading SignallingWebServer"
            if [ ! -f "get_ps_servers.sh" ]; then
                echo "Error: get_ps_servers.sh not found at '$WEBSERVERS_PATH'"
                exit 1
            fi
            ./get_ps_servers.sh
        fi

        # Do a sudo echo first to let user type before launching the signalling server in the background
        launch_terminal "AeroSim Pixel Streaming Server" "echo 'Launching Signalling Server requires sudo permissions.' && sudo ./SignallingWebServer/platform_scripts/bash/Start_SignallingServer.sh"
        read -p "Press Enter to continue after granting sudo access in the Signalling Server terminal window..."
    fi
fi

cd "$AEROSIM_ROOT"

# ============================================================================
# Handle launching Unreal renderer
# ============================================================================

if [ "$LAUNCH_UNREAL" = true ]; then
    # Set up Pixel Streaming argument flags
    RENDERER="unreal"
    APP_ARGS="--renderer=$RENDERER"

    PIXEL_STREAMING_FLAGS=""
    if [ "$PIXEL_STREAMING" = true ]; then
        echo "Starting AerosimUE5 with Pixel Streaming enabled on $PIXEL_STREAMING_IP:$PIXEL_STREAMING_PORT"
        PIXEL_STREAMING_FLAGS="-PixelStreamingIP=$PIXEL_STREAMING_IP -PixelStreamingPort=$PIXEL_STREAMING_PORT"

        if [ "$LAUNCH_UNREAL_PACKAGE" = true ] || [ "$LAUNCH_UNREAL_EDITOR_NOGUI" = true ]; then
            PIXEL_STREAMING_FLAGS="$PIXEL_STREAMING_FLAGS -RenderOffScreen -log"
        fi
    fi

    if [ "$LAUNCH_UNREAL_PACKAGE" = true ]; then
        cd "$AEROSIM_UNREAL_PROJECT_ROOT/package-$PACKAGE_CONFIG/Linux"
        launch_terminal "AeroSim Unreal Renderer" "./AerosimUE5.sh -game -ResX=1280 -ResY=720 $PIXEL_STREAMING_FLAGS"
        cd "$AEROSIM_ROOT"
    fi

    if [ "$LAUNCH_UNREAL_EDITOR_NOGUI" = true ]; then
        cd $AEROSIM_UNREAL_PROJECT_ROOT
        # Build the project
        ./build.sh
        # Launch in the editor's stand-alone game mode
        echo "./build.sh game IDS=$RENDERER_IDS $PIXEL_STREAMING_FLAGS"
        ./build.sh game IDS=$RENDERER_IDS $PIXEL_STREAMING_FLAGS
        cd "$AEROSIM_ROOT"
    fi

    if [ "$LAUNCH_UNREAL_EDITOR" = true ]; then
        cd $AEROSIM_UNREAL_PROJECT_ROOT
        # Build the project
        ./build.sh
        # Launch in editor mode
        echo "./build.sh launch IDS=$RENDERER_IDS $PIXEL_STREAMING_FLAGS"
        ./build.sh launch IDS=$RENDERER_IDS $PIXEL_STREAMING_FLAGS
        cd "$AEROSIM_ROOT"
    fi
fi

# ============================================================================
# Handle launching Omniverse renderer
# ============================================================================

if [ "$LAUNCH_OMNIVERSE" = true ]; then
    # Save the renderer choice to a JSON file
    RENDERER="omniverse"
    APP_ARGS="--renderer=$RENDERER"

    cd "$AEROSIM_OMNIVERSE_ROOT"
    ./build.sh
    if [ "$PIXEL_STREAMING" = true ]; then
        launch_terminal "AeroSim Omniverse Renderer" "./launch_aerosim_dev_kit_app.sh --no-window"
    else
        launch_terminal "AeroSim Omniverse Renderer" "./launch_aerosim_dev_kit_app.sh"
    fi
    cd "$AEROSIM_ROOT"
fi

# ============================================================================
# Handle no renderer selected
# ============================================================================

cd "$AEROSIM_ROOT"

if [ "$LAUNCH_UNREAL" = false ] && [ "$LAUNCH_OMNIVERSE" = false ]; then
    echo "No renderer was selected to be launched."
fi

# ============================================================================
# Handle launching the AeroSim App
# ============================================================================

cd "$AEROSIM_APP_ROOT"
echo "Launching AeroSim App..."
# Remove quotes if present in the RENDERER variable
CLEAN_RENDERER="${RENDERER//\"/}"
bun run dev:$CLEAN_RENDERER > aerosim_app.log 2>&1 &
cd "$AEROSIM_ROOT"

# ============================================================================
# Wait for user to end the simulator
# ============================================================================

echo
echo "Launched Aerosim. Press 'Q' key to end the simulator..."
while true; do
    read -rsn1 input
    if [ "$input" = "q" ] || [ "$input" = "Q" ]; then
        break
    fi
done

# ============================================================================
# End the simulator
# ============================================================================

echo "[launch_aerosim.sh] Ending simulator, stopping local kafka server..."
bash ./kafka/bin/kafka-server-stop.sh
echo "Done."

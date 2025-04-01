#!/bin/bash

# Enable error tracing for debugging in CI
set -ex

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"
echo "Current directory: $(pwd)"

# Check if header file exists, if not force a clean build
if [ ! -f "$SCRIPT_DIR/lib/aerosim_world_link.h" ]; then
  echo "Header file aerosim_world_link.h is missing, performing clean build..."
  cargo clean --manifest-path="$SCRIPT_DIR/Cargo.toml"
fi

if [ -n "$CI" ] || [ "$(uname)" == "Linux" ]; then
  echo "Forcing Linux target for CI or Linux environment"
  # Create .cargo/config.toml if it doesn't exist
  mkdir -p .cargo
  cat > .cargo/config.toml << EOL
[build]
incremental = true
jobs = 8

[target.x86_64-unknown-linux-gnu]
linker = "cc"
rustflags = ["-C", "target-feature=-crt-static"]
EOL
  # Make sure we use the Linux target explicitly
  RUSTFLAGS='-C target-feature=-crt-static'
  export RUSTFLAGS
  TARGET_FLAG="--target x86_64-unknown-linux-gnu"
else
  TARGET_FLAG=""
fi

echo "Building aerosim-world-link library for $(uname)..."
echo "Using manifest path: $SCRIPT_DIR/Cargo.toml"

# Check if Cargo.toml exists
if [ ! -f "$SCRIPT_DIR/Cargo.toml" ]; then
    echo "Error: Cargo.toml not found at $SCRIPT_DIR/Cargo.toml"
    echo "Contents of $SCRIPT_DIR:"
    ls -la "$SCRIPT_DIR"
    exit 1
fi

# Check Rust/Cargo version for diagnostics
echo "Rust version:"
rustc --version || echo "Rust not found"
echo "Cargo version:"
cargo --version || echo "Cargo not found"

# Make sure we're in the script directory for the build
cd "$SCRIPT_DIR" || { echo "Failed to cd to $SCRIPT_DIR"; exit 1; }

# Create target directory explicitly to avoid permission issues
mkdir -p "$SCRIPT_DIR/target"

# Check if we need to install the Linux target
rustup target list --installed | grep -q "x86_64-unknown-linux-gnu" || {
    echo "Installing Linux target..."
    rustup target add x86_64-unknown-linux-gnu
}

# Build specifically for Linux target with explicit flags
cargo build --release $TARGET_FLAG -v

# Verify the build created something
echo "Contents of target directory:"
find "$SCRIPT_DIR/target" -type d -maxdepth 3 || echo "No target directory found"

# Create lib directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/lib"

echo "Copying library files to output lib folder..."

# First check for target-specific directory (this should be the primary path)
TARGET_RELEASE_DIR="$SCRIPT_DIR/target/x86_64-unknown-linux-gnu/release"
STANDARD_RELEASE_DIR="$SCRIPT_DIR/target/release"

if [ -d "$TARGET_RELEASE_DIR" ]; then
    RELEASE_DIR="$TARGET_RELEASE_DIR"
    echo "Using target-specific release directory: $RELEASE_DIR"
elif [ -d "$STANDARD_RELEASE_DIR" ]; then
    RELEASE_DIR="$STANDARD_RELEASE_DIR"
    echo "Using standard release directory: $RELEASE_DIR"
else
    echo "Error: No release directory found"
    echo "Contents of target directory:"
    find "$SCRIPT_DIR/target" -type d || echo "Target directory is empty or not found"
    
    # Try to locate any .so files in the project
    echo "Searching for library files in the project:"
    find "$SCRIPT_DIR" -name "*.so" || echo "No library files found"
    
    exit 1
fi

# Find all library files 
echo "All files in release directory:"
ls -la "$RELEASE_DIR/" || echo "Cannot list release directory"

# Check for the expected library files - look for both naming conventions
if [ -f "$RELEASE_DIR/libaerosim_message_handler.so" ]; then
    echo "Found libaerosim_message_handler.so in $RELEASE_DIR"
    cp "$RELEASE_DIR/libaerosim_message_handler.so" "$SCRIPT_DIR/lib/libaerosim_world_link.so"
    echo "Copied to lib/libaerosim_world_link.so"
elif [ -f "$RELEASE_DIR/libaerosim_world_link.so" ]; then
    echo "Found libaerosim_world_link.so in $RELEASE_DIR"
    cp "$RELEASE_DIR/libaerosim_world_link.so" "$SCRIPT_DIR/lib/libaerosim_world_link.so"
    echo "Copied to lib/libaerosim_world_link.so"
else
    echo "Searching for libraries in all target directories..."
    
    # Search for any .so or .dll files as fallback
    SO_FILE=$(find "$SCRIPT_DIR/target" -name "libaerosim_message_handler.so" -o -name "libaerosim_world_link.so" | head -1)
    DLL_FILE=$(find "$SCRIPT_DIR/target" -name "aerosim_message_handler.dll" -o -name "aerosim_world_link.dll" | head -1)
    
    if [ -n "$SO_FILE" ]; then
        echo "Found library at: $SO_FILE"
        cp "$SO_FILE" "$SCRIPT_DIR/lib/libaerosim_world_link.so"
        echo "Copied to lib/libaerosim_world_link.so"
    elif [ -n "$DLL_FILE" ]; then
        echo "WARNING: Only found Windows DLL. This indicates the build system is targeting Windows even in Linux container."
        echo "This is likely caused by mounted Windows files in the container. Creating symbolic link as fallback..."
        ln -sf "$DLL_FILE" "$SCRIPT_DIR/lib/libaerosim_world_link.so"
        echo "Created symbolic link from DLL to .so file"
    else
        # Print more diagnostic information about the build environment
        echo "ERROR: No suitable library file found"
        echo "Build environment:"
        echo "- Target: $(rustc --print target-list | grep -F $(rustc --print cfg | grep target_arch | cut -d':' -f2) | head -1)"
        echo "- CI environment: ${CI:-false}"
        echo "- OS: $(uname -a)"
        
        # Useful debug output for troubleshooting CI failures
        if [ -n "$CI" ]; then
            echo "CI diagnostic information:"
            find "$SCRIPT_DIR/target" -type f -name "*.so" -o -name "*.dll" | head -10
            find "$SCRIPT_DIR/target" -type d | head -10
            echo "Cargo metadata:"
            cargo metadata --format-version=1 | grep -E "name|version" | head -20
        fi
        
        echo "Build failed: No library file was generated"
        exit 1
    fi
fi

# Final verification
if [ -f "$SCRIPT_DIR/lib/libaerosim_world_link.so" ]; then
    echo "Success: lib/libaerosim_world_link.so created"
    if [ -z "$CI" ]; then
        ls -la "$SCRIPT_DIR/lib/"
    fi
    echo "Build completed successfully"
else
    echo "ERROR: aerosim-world-link library not found"
    exit 1
fi

echo "Build completed successfully"

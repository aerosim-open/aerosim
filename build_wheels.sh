#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Define color codes for better output
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

# Script is being executed from the directory where it resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure system dependencies are available in CI environments
if [ "$CI" = true ]; then
    echo -e "${YELLOW}Checking for system dependencies...${NC}"
    # Avoid apt-get errors by redirecting stderr
    apt-get update &>/dev/null || true
    apt-get install -y zlib1g-dev pkg-config libssl-dev &>/dev/null || true
    
    # Fix directory permissions if running in CI
    echo -e "${YELLOW}Setting permissions for build directories...${NC}"
    mkdir -p target dist
    chmod -R 777 target dist 2>/dev/null || true
fi

echo -e "${YELLOW}Ensuring shell scripts have correct line endings...${NC}"
for file in $(find . -name "*.sh"); do
    if [[ -f "$file" ]]; then
        sed -i "s/\r$//" "$file" 2>/dev/null || echo "Warning: Could not fix line endings for $file"
    fi
done

echo -e "${YELLOW}Setting correct permissions for shell scripts...${NC}"
find . -name "*.sh" -exec chmod +x {} \; 2>/dev/null || echo "Warning: Could not set permissions for shell scripts"

# Display working directory for debugging
echo -e "${YELLOW}Working directory: $(pwd)${NC}"

# Create necessary directories
mkdir -p aerosim-world-link/lib target dist

# Check for existing build artifacts to determine if we need to rebuild
NEED_REBUILD=false
if [ ! -d "dist" ] || [ "$(find dist -name "*.whl" | wc -l)" -eq 0 ]; then
    echo -e "${YELLOW}No wheel files found in dist directory, need to build${NC}"
    NEED_REBUILD=true
fi

# Only build if needed
if [ "$NEED_REBUILD" = true ]; then
    # Ensure all build dependencies including maturin are installed via rye
    # This reads from pyproject.toml [build-system] section
    echo -e "${YELLOW}Ensuring build dependencies are installed...${NC}"
    rye sync

    # Activate the virtual environment if not already activated
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        source .venv/bin/activate || { echo -e "${RED}Failed to activate virtual environment${NC}"; exit 1; }
    fi

    # Install maturin directly to ensure it's available
    echo -e "${YELLOW}Ensuring maturin is available...${NC}"
    rye add maturin>=1.5,\<2.0

    # Print Python and tool versions for debugging
    echo -e "${YELLOW}Python version: $(python --version)${NC}"
    echo -e "${YELLOW}Maturin version: $(maturin --version 2>/dev/null || echo "Not installed")${NC}"
    echo -e "${YELLOW}Rye version: $(rye --version 2>/dev/null || echo "Not installed")${NC}"

    # Build all Rust components using our optimized build script
    # Note: This already handles aerosim-world-link through build.py
    echo -e "${YELLOW}Building Rust components with build.py...${NC}"
    rye run build -v || { echo -e "${RED}Error running build.py${NC}"; exit 1; }

    # Now generate wheels from the existing builds
    echo -e "${YELLOW}Generating wheels from existing builds...${NC}"
    # Use --clean to clean the output directory first
    rye build --wheel --all --clean || { echo -e "${RED}Error generating wheels${NC}"; exit 1; }
else
    echo -e "${GREEN}Wheel files already exist, skipping build step${NC}"
fi

# Print the contents of the dist directory
echo -e "${YELLOW}Contents of dist directory:${NC}"
ls -la dist/ || echo "dist directory not found or empty"

# Verify wheels were generated
if [ -d "dist" ] && [ "$(find dist -name "*.whl" | wc -l)" -gt 0 ]; then
    echo -e "${GREEN}Successfully generated wheels:${NC}"
    find dist -name "*.whl" | sort
    echo -e "${GREEN}Build completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Error: No wheels were generated. Build failed.${NC}"
    # Provide more diagnostic information
    echo -e "${YELLOW}=== Build Diagnostic Information ===${NC}"
    echo -e "${YELLOW}Rust version: $(rustc --version 2>/dev/null || echo "Not available")${NC}"
    echo -e "${YELLOW}Cargo version: $(cargo --version 2>/dev/null || echo "Not available")${NC}"
    echo -e "${YELLOW}Python version: $(python --version 2>/dev/null || echo "Not available")${NC}"
    echo -e "${YELLOW}Directory permissions:${NC}"
    ls -la . | head -n 10
    echo -e "${YELLOW}Target directory contents:${NC}"
    ls -la target/ 2>/dev/null || echo "Target directory not found or empty"
    exit 1
fi

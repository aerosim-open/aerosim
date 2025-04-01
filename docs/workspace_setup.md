# AeroSim Workspace Setup

This guide explains how to work with the integrated Cargo workspace and Rye/UV Python setup in AeroSim.

## Overview

AeroSim uses a Virtual Manifest Pattern to coordinate Cargo workspaces and PyO3/maturin builds within a Rye/UV Python project. This approach:

- Reduces build time and disk space usage by sharing dependencies
- Ensures consistent versions across all Rust components
- Integrates seamlessly with Python packaging via maturin
- Provides a simple developer experience with unified build commands

## Directory Structure

```
aerosim/
├── .cargo/
│   └── config.toml         # Global Rust settings
├── Cargo.toml              # Virtual manifest for Rust workspace
├── Cargo.lock              # Locked dependencies for Rust workspace
├── pyproject.toml          # Python project configuration with maturin integration
├── build.py                # Build coordination script
├── aerosim-core/           # Rust component
│   └── Cargo.toml          # References workspace dependencies
├── aerosim-data/           # Rust component
│   └── Cargo.toml          # References workspace dependencies
└── ... other components
```

## Building the Project

### Initial Setup

1. Install Rye and required tools:

```bash
# Install Rye if you haven't already
curl -sSf https://rye-up.com/get | bash

# Initialize the environment
rye sync
```

2. Build everything (Python and Rust components):

```bash
# Using the Rye script
rye run build

# Or directly
python build.py
```

### Development Workflow

When working on the project:

1. For Rust changes: Edit the Rust code in the respective crates, then run `rye run build` to rebuild
2. For Python changes: Edit the Python code normally, no rebuild necessary

### Adding Dependencies

- **For Rust components**: Add common dependencies to the root `Cargo.toml` under `[workspace.dependencies]` section
- **For Python components**: Add dependencies to `pyproject.toml` using Rye commands (`rye add <package>`)

## Cargo Workspace Benefits

The Cargo workspace offers several advantages:

1. **Shared Dependencies**: All crates share the same version of common dependencies, reducing compilation time and binary size
2. **Single Lock File**: One `Cargo.lock` file ensures consistent builds across the entire project
3. **Parallel Compilation**: Cargo can optimize the build process across all components
4. **Simplified Version Management**: Update versions in one place for all crates

## Troubleshooting

If you encounter issues with the build:

1. **Clean the build**: `cargo clean && rm -rf target/`
2. **Regenerate Rye environment**: `rye sync --force`
3. **Check for dependency conflicts**: Review the `Cargo.lock` file for conflicts

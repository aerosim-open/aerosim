#!/usr/bin/env python
"""Build script for coordinating Rye/UV Python package management with maturin Rust builds.

This script ensures proper sequencing of dependencies and compilation across the project.
"""

import os
import subprocess
import sys
import argparse
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, verbose=False):
    """Run a command and return its output."""
    print(f"Running: {' '.join(cmd if isinstance(cmd, list) else [cmd])}")
    try:
        if verbose:
            # Run with live output for verbose mode
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            process.communicate()
            if process.returncode != 0:
                print(f"Command failed with return code {process.returncode}")
                sys.exit(1)
            return ""
        else:
            # Capture output for normal mode
            result = subprocess.run(
                cmd, 
                cwd=cwd,
                check=True, 
                text=True, 
                capture_output=True,
                encoding='utf-8',  # Explicitly set encoding to utf-8
                errors='replace'   # Replace any invalid characters
            )
            return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)

def clean_build_artifacts(project_root, verbose=False):
    """Clean up build artifacts."""
    print("Cleaning build artifacts...")
    
    # Clean Rust build artifacts
    run_command(["cargo", "clean"], cwd=project_root, verbose=verbose)
    
    # Clean Python build artifacts
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        print(f"Removing {dist_dir}")
        shutil.rmtree(dist_dir)
    
    # Clean aerosim-world-link artifacts
    world_link_dir = project_root / "aerosim-world-link"
    world_link_lib_dir = world_link_dir / "lib"
    if world_link_lib_dir.exists():
        print(f"Removing {world_link_lib_dir}")
        shutil.rmtree(world_link_lib_dir)
    
    # Clean target directories in all packages
    packages = [
        "aerosim-controllers",
        "aerosim-core",
        "aerosim-data",
        "aerosim-dynamics-models",
        "aerosim-scenarios",
        "aerosim-sensors",
        "aerosim-world",
        "aerosim-world-link"
    ]
    
    for package in packages:
        package_target = project_root / package / "target"
        if package_target.exists():
            print(f"Removing {package_target}")
            shutil.rmtree(package_target)
    
    print("Clean completed successfully!")

def main():
    """Main build function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Build AeroSim components')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-f', '--force', action='store_true', help='Force rebuilding even if wheels exist')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean up build artifacts before building')

    # Add arguments that might be passed by rye build
    parser.add_argument('--outdir', help='Output directory for built packages (used by rye build)', nargs='?')
    parser.add_argument('--installer', help='Installer to use (used by rye build)', nargs='?')
    parser.add_argument('--wheel', action='store_true', help='Build wheel package (used by rye build)')
    
    # Allow any additional positional arguments without error
    parser.add_argument('additional_args', nargs='*', help='Additional arguments passed by rye build')

    args = parser.parse_args()

    project_root = Path(__file__).parent.absolute()

    # Clean build artifacts if requested
    if args.clean:
        clean_build_artifacts(project_root, args.verbose)
    
    # Step 1: Ensure Rye/UV environment is set up
    if not (project_root / ".venv").exists():
        print("Setting up Rye virtual environment...")
        run_command(["rye", "sync"], cwd=project_root, verbose=args.verbose)
    
    # Step 2: Build all Rust crates using maturin
    print("Building Rust crates with maturin...")
    
    # Path to maturin in the virtual environment
    venv_path = project_root / ".venv"
    if sys.platform == "win32":
        maturin_path = venv_path / "Scripts" / "maturin.exe"
    else:
        maturin_path = venv_path / "bin" / "maturin"
    
    if not maturin_path.exists():
        print(f"Maturin not found at {maturin_path}. Installing...")
        run_command(["rye", "run", "pip", "install", "maturin>=1.5,<2.0"], cwd=project_root, verbose=args.verbose)
    
    # Build each package individually
    packages = [
        "aerosim-controllers",
        "aerosim-core",
        "aerosim-data",
        "aerosim-dynamics-models",
        "aerosim-scenarios",
        "aerosim-sensors",
        "aerosim-world"
    ]

    # Check if we can skip builds
    skip_builds = False
    if os.getenv("CI") and (project_root / "dist").exists():
        # If we're in CI and wheels already exist, check if we need to rebuild
        wheel_count = len(list((project_root / "dist").glob("*.whl")))
        if wheel_count >= len(packages):
            print(f"Found {wheel_count} wheels in dist directory, may skip building if not requested")
            if not args.force:
                skip_builds = True
    
    if not skip_builds:
        total_packages = len(packages)
        for i, package in enumerate(packages):
            print(f"Building package {i+1}/{total_packages} {package}...")
            package_path = project_root / package / "Cargo.toml"
            if package_path.exists():
                run_command(
                    [str(maturin_path), "develop", "--skip-install", "-m", str(package_path)],
                    cwd=project_root, verbose=args.verbose
                )
            else:
                print(f"Warning: {package_path} does not exist, skipping")
    else:
        print("Skipping package builds as wheels already exist (use --force or -f to force rebuild)")

    # Step 3: Build aerosim-world-link explicitly
    world_link_dir = project_root / "aerosim-world-link"
    print("Building aerosim-world-link...")

    # Ensure lib directory exists
    (world_link_dir / "lib").mkdir(exist_ok=True)

    # Always build aerosim-world-link regardless of existing files
    if sys.platform == "win32":
        bat_file = world_link_dir / "build.bat"
        if bat_file.exists():
            print(f"Running batch file: {bat_file}")
            run_command(f"cmd /c {bat_file}", cwd=world_link_dir, verbose=args.verbose)
        else:
            print(f"Warning: build.bat not found at {bat_file}")
            print("Files in directory:")
            for file in world_link_dir.iterdir():
                print(f"  {file}")
    else:
        # Make the script executable
        shell_file = world_link_dir / "build.sh"
        if shell_file.exists():
            run_command(["chmod", "+x", str(shell_file)], cwd=world_link_dir, verbose=args.verbose)
            run_command(["./build.sh"], cwd=world_link_dir, verbose=args.verbose)
        else:
            print(f"Warning: build.sh not found at {shell_file}")
            print("Files in directory:")
            for file in world_link_dir.iterdir():
                print(f"  {file}")

    # Step 4: Additional Python package setup if needed
    print("Installing additional Python dependencies...")
    run_command(
        ["rye", "sync", "--no-lock"], 
        cwd=project_root, verbose=args.verbose
    )

    # Step 5: Handle rye build arguments if present
    if args.outdir and args.wheel:
        print(f"Rye build detected with outdir: {args.outdir}")
        print("Note: These arguments are handled by rye directly and don't need processing here.")

    print("Build completed successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to convert PNG images to JPEG with good compression and analyze size savings.
Also provides recommendations for Git LFS configuration.
"""

import os
import glob
import time
import subprocess
from PIL import Image
import shutil
from pathlib import Path
import sys

# Configuration
# Determine the repository root and image directory regardless of where the script is run from
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# If script is run from docs/scripts, go up two levels to get to repo root
# If script is run from repo root with docs/scripts/convert_images.py, REPO_ROOT will be correct
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
IMG_DIR = os.path.join(SCRIPT_DIR, "..", "img")  # docs/img relative to docs/scripts
IMG_DIR = os.path.normpath(IMG_DIR)  # Normalize the path

# Verify paths are correct
if not os.path.exists(IMG_DIR):
    print(f"Error: Image directory not found at {IMG_DIR}")
    print("Make sure you're running the script from the repository root or the docs/scripts directory")
    sys.exit(1)

print(f"Repository root: {REPO_ROOT}")
print(f"Image directory: {IMG_DIR}")

JPEG_QUALITY = 85  # Adjust this for quality vs size (0-100)
WEBP_QUALITY = 80  # For WebP files if needed

def get_file_size_mb(file_path):
    """Get file size in MB"""
    return os.path.getsize(file_path) / (1024 * 1024)

def estimate_load_time(total_size_mb, connection_speed_mbps=5):
    """Estimate page load time based on total image size and connection speed"""
    # Convert MB to Mb (megabytes to megabits)
    total_size_mb_bits = total_size_mb * 8
    # Calculate load time in seconds
    return total_size_mb_bits / connection_speed_mbps

def analyze_current_images():
    """Analyze current images in the docs/img directory"""
    print("\n=== Current Image Analysis ===")
    
    png_files = glob.glob(os.path.join(IMG_DIR, "*.png"))
    webp_files = glob.glob(os.path.join(IMG_DIR, "*.webp"))
    all_images = png_files + webp_files
    
    if not all_images:
        print("No images found in", IMG_DIR)
        return []
    
    total_size_mb = 0
    image_data = []
    
    print(f"{'Filename':<40} {'Size (MB)':<15} {'Dimensions':<20}")
    print("-" * 75)
    
    for img_path in all_images:
        filename = os.path.basename(img_path)
        size_mb = get_file_size_mb(img_path)
        total_size_mb += size_mb
        
        try:
            with Image.open(img_path) as img:
                dimensions = f"{img.width}x{img.height}"
                image_data.append({
                    'path': img_path,
                    'filename': filename,
                    'size_mb': size_mb,
                    'dimensions': dimensions,
                    'format': img.format
                })
        except Exception as e:
            print(f"Error opening {filename}: {e}")
            dimensions = "Unknown"
            image_data.append({
                'path': img_path,
                'filename': filename,
                'size_mb': size_mb,
                'dimensions': dimensions,
                'format': 'Unknown'
            })
        
        print(f"{filename:<40} {size_mb:.6f} MB    {dimensions:<20}")
    
    # Calculate estimated load times
    slow_3g = estimate_load_time(total_size_mb, 0.4)  # 0.4 Mbps for Slow 3G
    fast_3g = estimate_load_time(total_size_mb, 1.5)  # 1.5 Mbps for Fast 3G
    slow_4g = estimate_load_time(total_size_mb, 5)    # 5 Mbps for Slow 4G
    fast_4g = estimate_load_time(total_size_mb, 20)   # 20 Mbps for Fast 4G
    
    print("\n=== Summary ===")
    print(f"Total images: {len(all_images)}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print("\nEstimated page load times (images only):")
    print(f"Slow 3G (0.4 Mbps): {slow_3g:.2f} seconds")
    print(f"Fast 3G (1.5 Mbps): {fast_3g:.2f} seconds")
    print(f"Slow 4G (5 Mbps):   {slow_4g:.2f} seconds")
    print(f"Fast 4G (20 Mbps):  {fast_4g:.2f} seconds")
    
    return image_data

def convert_images(image_data):
    """Convert PNG images to JPEG with compression"""
    print("\n=== Converting Images ===")
    
    # Create backup directory
    backup_dir = os.path.join(IMG_DIR, "backup_png")
    os.makedirs(backup_dir, exist_ok=True)
    
    total_original_mb = 0
    total_converted_mb = 0
    conversion_results = []
    
    for img_info in image_data:
        if not img_info['path'].lower().endswith('.png'):
            print(f"Skipping {img_info['filename']} (not a PNG file)")
            continue
        
        original_path = img_info['path']
        original_size_mb = img_info['size_mb']
        total_original_mb += original_size_mb
        
        # Create backup
        backup_path = os.path.join(backup_dir, os.path.basename(original_path))
        shutil.copy2(original_path, backup_path)
        
        # Convert to JPEG
        jpeg_path = os.path.splitext(original_path)[0] + '.jpg'
        
        try:
            with Image.open(original_path) as img:
                # If image has transparency, use white background
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    background.save(jpeg_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                else:
                    img.convert('RGB').save(jpeg_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                
                jpeg_size_mb = get_file_size_mb(jpeg_path)
                total_converted_mb += jpeg_size_mb
                
                savings_percent = (1 - (jpeg_size_mb / original_size_mb)) * 100
                
                conversion_results.append({
                    'original': img_info['filename'],
                    'converted': os.path.basename(jpeg_path),
                    'original_size_mb': original_size_mb,
                    'converted_size_mb': jpeg_size_mb,
                    'savings_percent': savings_percent
                })
                
                print(f"Converted {img_info['filename']} to JPEG:")
                print(f"  Original: {original_size_mb:.6f} MB")
                print(f"  Converted: {jpeg_size_mb:.6f} MB")
                print(f"  Savings: {savings_percent:.2f}%")
                
                # Remove original PNG after successful conversion
                os.remove(original_path)
                
        except Exception as e:
            print(f"Error converting {img_info['filename']}: {e}")
    
    total_savings_percent = (1 - (total_converted_mb / total_original_mb)) * 100 if total_original_mb > 0 else 0
    
    print("\n=== Conversion Summary ===")
    print(f"Total original size (PNG only): {total_original_mb:.2f} MB")
    print(f"Total converted size (JPEG): {total_converted_mb:.2f} MB")
    print(f"Total savings: {total_savings_percent:.2f}%")
    print(f"Backup of original PNG files saved to: {backup_dir}")
    
    return conversion_results, total_original_mb, total_converted_mb, total_savings_percent

def check_git_lfs_status():
    """Check Git LFS status and provide recommendations"""
    print("\n=== Git LFS Analysis ===")
    
    # Save current directory to restore it later
    current_dir = os.getcwd()
    
    try:
        # Change to repository root directory for Git LFS operations
        os.chdir(REPO_ROOT)
        
        # Check if Git LFS is installed
        try:
            subprocess.run(['git', 'lfs', 'version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            lfs_installed = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            lfs_installed = False
        
        if not lfs_installed:
            print("Git LFS is not installed. Install it with:")
            print("  git lfs install")
            return
        
        # Check if Git LFS is initialized in the repository
        try:
            result = subprocess.run(['git', 'lfs', 'install', '--local'], check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error initializing Git LFS: {e.stderr.strip()}")
            return
        
        # Check current tracked patterns
        try:
            result = subprocess.run(['git', 'lfs', 'track'], check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            current_patterns = result.stdout.strip()
            
            if current_patterns:
                print("Currently tracked patterns:")
                print(current_patterns)
            else:
                print("No patterns are currently being tracked by Git LFS.")
        except subprocess.CalledProcessError as e:
            print(f"Error checking tracked patterns: {e.stderr.strip()}")
        
        # Provide recommendations
        print("\nRecommendations for Git LFS:")
        print("1. Track image files with:")
        print("   git lfs track \"*.jpg\" \"*.jpeg\" \"*.png\" \"*.webp\"")
        print("2. Add .gitattributes to Git:")
        print("   git add .gitattributes")
        print("3. Add and commit the converted images:")
        print("   git add docs/img/")
        print("   git commit -m \"Convert PNG images to JPEG and configure Git LFS\"")
    finally:
        # Restore original directory
        os.chdir(current_dir)

def setup_git_lfs():
    """Set up Git LFS for image files"""
    print("\n=== Setting up Git LFS ===")
    
    # Save current directory to restore it later
    current_dir = os.getcwd()
    
    try:
        # Change to repository root directory for Git LFS operations
        os.chdir(REPO_ROOT)
        
        # Track image files
        subprocess.run(['git', 'lfs', 'track', '*.jpg', '*.jpeg', '*.png', '*.webp'], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Configured Git LFS to track image files.")
        
        # Check if .gitattributes was created/modified
        if os.path.exists('.gitattributes'):
            print("Updated .gitattributes file with tracking patterns.")
        else:
            print("Warning: .gitattributes file was not created.")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Git LFS: {e.stderr.strip() if hasattr(e, 'stderr') else str(e)}")
    finally:
        # Restore original directory
        os.chdir(current_dir)

def main():
    """Main function to analyze and convert images"""
    print("=== Image Conversion and Git LFS Analysis Tool ===")
    
    # Analyze current images
    image_data = analyze_current_images()
    
    if not image_data:
        print("No images to process. Exiting.")
        return
    
    # Count PNG files
    png_files = [img for img in image_data if img['path'].lower().endswith('.png')]
    
    if not png_files:
        print("\nNo PNG files found to convert. If you want to analyze Git LFS status only, continue.")
        response = input("\nDo you want to check Git LFS status? (y/n): ")
        if response.lower() == 'y':
            check_git_lfs_status()
            
            response = input("\nDo you want to set up Git LFS for image files? (y/n): ")
            if response.lower() == 'y':
                setup_git_lfs()
                
                print("\n=== Next Steps ===")
                print("1. Add and commit the .gitattributes file:")
                print("   git add .gitattributes")
                print("   git commit -m \"Configure Git LFS for image files\"")
        return
    
    # Ask for confirmation before converting
    response = input(f"\nFound {len(png_files)} PNG files. Do you want to convert them to JPEG? (y/n): ")
    
    if response.lower() == 'y':
        # Convert images
        conversion_results, total_original_mb, total_converted_mb, total_savings_percent = convert_images(image_data)
        
        # Check Git LFS status
        check_git_lfs_status()
        
        # Ask if user wants to set up Git LFS
        response = input("\nDo you want to set up Git LFS for image files? (y/n): ")
        
        if response.lower() == 'y':
            setup_git_lfs()
            
            print("\n=== Next Steps ===")
            print("1. Review the converted images to ensure quality is acceptable")
            print("2. Add and commit the changes:")
            print("   git add .gitattributes docs/img/")
            print("   git commit -m \"Convert PNG images to JPEG and configure Git LFS\"")
            print("\nNote: The original PNG files have been backed up to:")
            print(f"  {os.path.join(IMG_DIR, 'backup_png')}")
    else:
        print("Image conversion cancelled.")
        
        # Still check Git LFS status
        check_git_lfs_status()

if __name__ == "__main__":
    main()

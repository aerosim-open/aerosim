#!/usr/bin/env python3
"""
Script to clean up whitespace and ensure LF line endings in Markdown files.
"""

import os
import glob
import sys

def clean_file(file_path):
    """
    Clean a file by:
    1. Removing trailing whitespace
    2. Ensuring LF line endings
    3. Ensuring a single newline at the end of the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            lines = f.readlines()
        
        # Remove trailing whitespace and ensure LF line endings
        cleaned_lines = [line.rstrip() + '\n' for line in lines]
        
        # Ensure a single newline at the end of the file
        while cleaned_lines and cleaned_lines[-1].strip() == '':
            cleaned_lines.pop()
        cleaned_lines.append('\n')
        
        # Write the cleaned content back to the file
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(cleaned_lines)
        
        print(f"Cleaned {file_path}")
        return True
    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False

def main():
    """
    Clean whitespace in specified files.
    """
    if len(sys.argv) > 1:
        # Clean specific files provided as arguments
        files = sys.argv[1:]
    else:
        # Default to cleaning all Markdown files in the docs directory
        docs_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
    
    success_count = 0
    for file_path in files:
        if clean_file(file_path):
            success_count += 1
    
    print(f"\nCleaned {success_count} out of {len(files)} files.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to update PNG image references to JPG in Markdown files.
"""

import os
import re
import glob
from pathlib import Path

def update_markdown_files(docs_dir):
    """
    Update all Markdown files in the docs directory to use JPG instead of PNG.
    """
    # Find all Markdown files
    md_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
    
    # Pattern to match PNG image references in Markdown
    # This handles various Markdown image formats:
    # ![alt text](path/to/image.png) - Standard Markdown
    # <img src="path/to/image.png" /> - HTML in Markdown
    # Also handles both relative and absolute paths
    png_pattern = re.compile(r'(\!\[.*?\]\(|\<img\s+src=["\']{1})([^)"\']*)\.png([)"\'])', re.IGNORECASE)
    
    files_updated = 0
    references_updated = 0
    
    print(f"Scanning {len(md_files)} Markdown files for PNG references...")
    
    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count PNG references before replacement
        png_count = len(re.findall(png_pattern, content))
        
        if png_count == 0:
            continue
        
        # Replace PNG with JPG
        updated_content = re.sub(png_pattern, r'\1\2.jpg\3', content)
        
        # Write the updated content back to the file
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        files_updated += 1
        references_updated += png_count
        
        print(f"Updated {png_count} references in {os.path.basename(md_file)}")
    
    print(f"\nSummary: Updated {references_updated} PNG references in {files_updated} files.")
    return files_updated, references_updated

if __name__ == "__main__":
    # Get the docs directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.dirname(script_dir)  # Parent of scripts directory is docs
    
    print(f"Docs directory: {docs_dir}")
    
    # Update Markdown files
    files_updated, references_updated = update_markdown_files(docs_dir)
    
    if files_updated > 0:
        print("\nNext steps:")
        print("1. Build and render the docs to verify changes")
        print("2. Commit the changes with:")
        print("   git add docs/")
        print("   git commit -m \"Update image references from PNG to JPG in documentation\"")
    else:
        print("\nNo PNG references found in Markdown files. No changes made.")

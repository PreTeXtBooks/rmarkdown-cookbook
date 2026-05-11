#!/usr/bin/env python3
"""
Copy and convert images to PreTeXt generated-assets directory.
This script prepares images for the PreTeXt build process.
"""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    # Define paths
    script_dir = Path(__file__).parent
    source_images_dir = script_dir / "images"
    # Put images in pretext/assets/images/ directory.
    # publication.ptx sets external="../assets", so PreTeXt resolves source paths
    # relative to that directory. PTX source files reference images as
    # source="images/filename.png" which resolves to pretext/assets/images/filename.png
    # and renders as external/images/filename.png in the HTML output.
    pretext_assets = script_dir / "pretext" / "assets" / "images"
    
    print("Preparing images for PreTeXt book...")
    print(f"Source: {source_images_dir}")
    print(f"Target: {pretext_assets}")
    
    # Create assets/images directory
    pretext_assets.mkdir(parents=True, exist_ok=True)
    
    # Check if ImageMagick convert is available
    convert_available = shutil.which("convert") is not None
    
    if convert_available:
        print("ImageMagick found - will convert EPS to PNG")
    else:
        print("ImageMagick not found - will only copy existing image files")
    
    images_copied = 0
    images_converted = 0
    
    # Copy existing image files (PNG, JPG, JPEG, GIF)
    for img_file in sorted(source_images_dir.rglob("*")):
        # Skip defunct images and non-image files
        if "defunct_images" in str(img_file):
            continue
        if img_file.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
            continue
            
        target_file = pretext_assets / img_file.name
        shutil.copy2(img_file, target_file)
        images_copied += 1
        print(f"  Copied: {img_file.name}")
    
    # Convert EPS files to PNG if ImageMagick is available
    if convert_available:
        for eps_file in source_images_dir.rglob("*.eps"):
            # Get the base filename without extension
            base_name = eps_file.stem
            target_file = pretext_assets / f"{base_name}.png"
            
            # Skip if PNG already exists
            if target_file.exists():
                continue
            
            try:
                # Convert EPS to PNG using ImageMagick
                subprocess.run([
                    "convert",
                    "-density", "300",
                    "-quality", "90",
                    str(eps_file),
                    str(target_file)
                ], check=True, capture_output=True, text=True)
                
                images_converted += 1
                print(f"  Converted: {base_name}.eps -> {base_name}.png")
            except subprocess.CalledProcessError as e:
                print(f"  Warning: Failed to convert {eps_file.name}: {e}")
                continue
            except Exception as e:
                print(f"  Warning: Error processing {eps_file.name}: {e}")
                continue
    
    # Summary
    total_images = (
        len(list(pretext_assets.glob("*.png")))
        + len(list(pretext_assets.glob("*.jpg")))
        + len(list(pretext_assets.glob("*.jpeg")))
        + len(list(pretext_assets.glob("*.gif")))
    )
    print(f"\nComplete!")
    print(f"  Copied: {images_copied} PNG files")
    print(f"  Converted: {images_converted} EPS files")
    print(f"  Total images in assets/images: {total_images}")
    
    if total_images == 0:
        print("\nNote: No images were found in the source directory.")

    return 0

if __name__ == "__main__":
    exit(main())

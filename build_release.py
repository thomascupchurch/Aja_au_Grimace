#!/usr/bin/env python3
import os, sys, shutil, subprocess
import datetime

def build_for_platform():
    """Build executable for current platform"""
    platform = "Windows" if sys.platform.startswith('win') else "Mac"
    
    # Clean previous build
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build executable
    cmd = [
        'pyinstaller', 
        '--onefile', 
        '--windowed',
        '--name', 'ProjectPlanner',
        'main.py'
    ]
    
    subprocess.run(cmd, check=True)
    
    # Copy to platform-specific folder
    os.makedirs(f'release/{platform}', exist_ok=True)
    
    if platform == "Windows":
        shutil.copy('dist/ProjectPlanner.exe', f'release/{platform}/')
    else:
        shutil.copytree('dist/ProjectPlanner.app', f'release/{platform}/ProjectPlanner.app')
    
    # Copy VERSION and docs
    shutil.copy('VERSION', f'release/{platform}/')
    
    print(f"Built for {platform} in release/{platform}/")

if __name__ == "__main__":
    build_for_platform()
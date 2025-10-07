#!/usr/bin/env python3
"""
Setup script for ProjectPlanner development environment
Ensures compatible Qt binding installation
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is compatible with Qt bindings"""
    version = sys.version_info
    if version.major == 3 and 8 <= version.minor <= 12:
        print(f"[OK] Python {version.major}.{version.minor} is compatible")
        return True
    else:
        print(f"[WARNING] Python {version.major}.{version.minor} may have compatibility issues")
        print("Recommended: Python 3.8-3.12 for Qt binding compatibility")
        return False

def install_dependencies():
    """Install required dependencies for ProjectPlanner"""
    
    commands = [
        "pip install --upgrade pip",
        "pip install PySide6==6.6.3",
        "pip install openpyxl python-dateutil pyinstaller"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"[ERROR] Failed: {cmd}")
            return False
    
    return True

def test_installation():
    """Test Qt binding installation"""
    print("Testing Qt binding installation...")
    
    test_script = """
try:
    from PySide6.QtWidgets import QApplication
    print('[OK] PySide6 working!')
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
        print('[OK] PyQt6 working!')
    except ImportError:
        print('[ERROR] No Qt binding found')
        exit(1)
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], 
                          capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print(result.stdout.strip())
        return True
    else:
        print(result.stderr.strip())
        return False

def main():
    """Main setup function"""
    print("ProjectPlanner Environment Setup")
    print("=" * 40)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    print("\nInstalling dependencies...")
    if not install_dependencies():
        print("[ERROR] Dependency installation failed")
        return False
    
    # Test installation
    print("\nTesting installation...")
    if not test_installation():
        print("[ERROR] Installation test failed")
        return False
    
    print("\n[SUCCESS] Environment setup complete!")
    print("Run your app with: python main.py")
    print("Build executable with: pyinstaller --onefile --windowed --name ProjectPlanner main.py")
    
    return True

if __name__ == "__main__":
    main()
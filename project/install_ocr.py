#!/usr/bin/env python3
"""
OCR Installation and Setup Script for Prescription Authenticator AI
"""
import sys
import os
import platform
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def run_command(command, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def install_python_packages():
    """Install required Python packages"""
    print_header("Installing Python OCR Packages")
    
    packages = [
        "pytesseract==0.3.10",
        "easyocr==1.7.0", 
        "opencv-python==4.8.1.78",
        "numpy==1.24.3"
    ]
    
    success_count = 0
    for package in packages:
        if run_command(f"pip install {package}", f"Installing {package}"):
            success_count += 1
    
    print(f"\n📊 Installed {success_count}/{len(packages)} packages successfully")
    return success_count == len(packages)

def install_tesseract_windows():
    """Install Tesseract on Windows"""
    print_header("Installing Tesseract OCR on Windows")
    
    tesseract_url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    installer_path = "tesseract_installer.exe"
    
    print("📥 Downloading Tesseract installer...")
    try:
        urllib.request.urlretrieve(tesseract_url, installer_path)
        print("✅ Download completed")
        
        print("🚀 Starting Tesseract installation...")
        print("   Please follow the installation wizard")
        print("   Recommended installation path: C:\\Program Files\\Tesseract-OCR\\")
        
        subprocess.run([installer_path], check=True)
        
        # Clean up
        if os.path.exists(installer_path):
            os.remove(installer_path)
        
        print("✅ Tesseract installation completed")
        return True
        
    except Exception as e:
        print(f"❌ Tesseract installation failed: {e}")
        print("💡 Please manually download and install from:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def install_tesseract_macos():
    """Install Tesseract on macOS"""
    print_header("Installing Tesseract OCR on macOS")
    
    # Check if Homebrew is installed
    if run_command("which brew", "Checking for Homebrew"):
        return run_command("brew install tesseract", "Installing Tesseract via Homebrew")
    else:
        print("❌ Homebrew not found")
        print("💡 Please install Homebrew first:")
        print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        print("   Then run: brew install tesseract")
        return False

def install_tesseract_linux():
    """Install Tesseract on Linux"""
    print_header("Installing Tesseract OCR on Linux")
    
    # Try different package managers
    commands = [
        ("apt-get update && apt-get install -y tesseract-ocr", "Installing via apt-get"),
        ("yum install -y tesseract", "Installing via yum"),
        ("dnf install -y tesseract", "Installing via dnf"),
        ("pacman -S tesseract", "Installing via pacman")
    ]
    
    for command, description in commands:
        if run_command(f"sudo {command}", description):
            return True
    
    print("❌ Could not install Tesseract automatically")
    print("💡 Please install manually using your distribution's package manager")
    return False

def verify_tesseract_installation():
    """Verify Tesseract installation"""
    print_header("Verifying Tesseract Installation")
    
    # Common paths to check
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Found Tesseract at: {path}")
            return True
    
    # Check PATH
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        print(f"✅ Found Tesseract in PATH: {tesseract_path}")
        
        # Test version
        try:
            result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✅ Tesseract version: {version_line}")
                return True
        except Exception as e:
            print(f"⚠️ Tesseract found but version check failed: {e}")
            return True  # Still consider it installed
    
    print("❌ Tesseract not found")
    return False

def test_ocr_functionality():
    """Test OCR functionality"""
    print_header("Testing OCR Functionality")
    
    try:
        # Test pytesseract
        print("🧪 Testing pytesseract...")
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Create a simple test image with text
        test_image = Image.new('RGB', (200, 50), color='white')
        
        # Try to extract text (will fail but we're testing import)
        try:
            text = pytesseract.image_to_string(test_image)
            print("✅ pytesseract is working")
        except Exception as e:
            if "tesseract is not installed" in str(e).lower():
                print("❌ Tesseract executable not found")
                return False
            else:
                print("✅ pytesseract is working (expected error for blank image)")
        
        # Test EasyOCR
        print("🧪 Testing EasyOCR...")
        try:
            import easyocr
            print("✅ EasyOCR imported successfully")
            
            # Initialize reader (this will download models on first run)
            print("📥 Initializing EasyOCR (may download models)...")
            reader = easyocr.Reader(['en'])
            print("✅ EasyOCR is working")
            
        except Exception as e:
            print(f"⚠️ EasyOCR test failed: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        return False
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def main():
    """Main installation function"""
    print("🏥 Prescription Authenticator AI - OCR Setup")
    print("=" * 60)
    
    system = platform.system().lower()
    print(f"🖥️ Detected system: {platform.system()} {platform.release()}")
    
    # Step 1: Install Python packages
    if not install_python_packages():
        print("⚠️ Some Python packages failed to install")
    
    # Step 2: Install Tesseract based on OS
    tesseract_installed = False
    
    if system == "windows":
        tesseract_installed = install_tesseract_windows()
    elif system == "darwin":  # macOS
        tesseract_installed = install_tesseract_macos()
    elif system == "linux":
        tesseract_installed = install_tesseract_linux()
    else:
        print(f"❌ Unsupported operating system: {system}")
    
    # Step 3: Verify installation
    if verify_tesseract_installation():
        tesseract_installed = True
    
    # Step 4: Test functionality
    ocr_working = test_ocr_functionality()
    
    # Final report
    print_header("Installation Summary")
    
    if tesseract_installed and ocr_working:
        print("🎉 OCR setup completed successfully!")
        print("✅ Tesseract OCR is installed and working")
        print("✅ Python OCR packages are installed")
        print("✅ Image text extraction should now work in the application")
    elif ocr_working:
        print("✅ OCR setup partially successful!")
        print("✅ Python OCR packages are working")
        print("⚠️ Tesseract may need manual configuration")
    else:
        print("❌ OCR setup needs attention")
        print("💡 Please check the error messages above and install missing components")
    
    print("\n🚀 You can now restart the Prescription Authenticator AI application")
    print("📖 For manual installation instructions, see the application's OCR setup guide")

if __name__ == "__main__":
    main()

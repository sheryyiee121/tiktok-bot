#!/usr/bin/env python3
"""
Chrome WebDriver Installation Script for TikTok DM Bot
This script helps install ChromeDriver automatically
"""

import os
import sys
import platform
import requests
import zipfile
import shutil
from pathlib import Path

def get_chrome_version():
    """Get installed Chrome version"""
    system = platform.system()
    
    if system == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version.split('.')[0]
        except:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                return version.split('.')[0]
            except:
                return None
    
    elif system == "Darwin":  # macOS
        try:
            import subprocess
            result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], 
                                  capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]
            return version.split('.')[0]
        except:
            return None
    
    elif system == "Linux":
        try:
            import subprocess
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]
            return version.split('.')[0]
        except:
            try:
                result = subprocess.run(['chromium-browser', '--version'], capture_output=True, text=True)
                version = result.stdout.strip().split()[-1]
                return version.split('.')[0]
            except:
                return None
    
    return None

def download_chromedriver(version, system):
    """Download ChromeDriver for the specified version and system"""
    
    # ChromeDriver download URLs
    base_url = "https://chromedriver.storage.googleapis.com"
    
    # Get latest version for major version
    try:
        response = requests.get(f"{base_url}/LATEST_RELEASE_{version}")
        if response.status_code == 200:
            driver_version = response.text.strip()
        else:
            print(f"Could not find ChromeDriver for Chrome version {version}")
            return False
    except Exception as e:
        print(f"Error getting ChromeDriver version: {e}")
        return False
    
    # Determine platform
    if system == "Windows":
        platform_name = "win32"
        executable_name = "chromedriver.exe"
    elif system == "Darwin":
        platform_name = "mac64"
        executable_name = "chromedriver"
    else:  # Linux
        platform_name = "linux64"
        executable_name = "chromedriver"
    
    # Download URL
    download_url = f"{base_url}/{driver_version}/chromedriver_{platform_name}.zip"
    
    print(f"Downloading ChromeDriver {driver_version} for {system}...")
    
    try:
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Save zip file
        zip_path = f"chromedriver_{platform_name}.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall()
        
        # Move to appropriate location
        current_dir = Path.cwd()
        driver_path = current_dir / executable_name
        
        # Make executable on Unix systems
        if system != "Windows":
            os.chmod(driver_path, 0o755)
        
        # Clean up
        os.remove(zip_path)
        
        print(f"✅ ChromeDriver installed successfully at: {driver_path}")
        print(f"📝 Make sure this location is in your PATH or update your script to use this path")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading ChromeDriver: {e}")
        return False

def main():
    """Main installation function"""
    print("🚀 TikTok DM Bot - ChromeDriver Installation")
    print("=" * 50)
    
    system = platform.system()
    print(f"Detected system: {system}")
    
    # Check if Chrome is installed
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ Google Chrome not found!")
        print("📥 Please install Google Chrome first:")
        print("   - Windows/Mac: https://www.google.com/chrome/")
        print("   - Linux: sudo apt install google-chrome-stable")
        return False
    
    print(f"✅ Found Chrome version: {chrome_version}")
    
    # Check if ChromeDriver already exists
    driver_name = "chromedriver.exe" if system == "Windows" else "chromedriver"
    if os.path.exists(driver_name):
        print(f"⚠️  ChromeDriver already exists: {driver_name}")
        response = input("Do you want to download a fresh copy? (y/n): ")
        if response.lower() != 'y':
            print("Installation cancelled.")
            return True
    
    # Download ChromeDriver
    success = download_chromedriver(chrome_version, system)
    
    if success:
        print("\n🎉 Installation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Install Python dependencies: pip install -r requirements.txt")
        print("2. Run the bot: python app.py")
        print("3. Visit: http://localhost:5000")
        print("\n⚠️  Important notes:")
        print("- Only use accounts you own")
        print("- Respect TikTok's Terms of Service")
        print("- Use responsibly and avoid spamming")
    else:
        print("\n❌ Installation failed!")
        print("📝 Manual installation:")
        print("1. Visit: https://chromedriver.chromium.org/downloads")
        print(f"2. Download ChromeDriver for Chrome version {chrome_version}")
        print("3. Extract and place in your project folder")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please try manual installation or report this issue.")

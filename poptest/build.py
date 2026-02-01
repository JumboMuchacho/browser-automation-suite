import os
import shutil
import subprocess
import sys
import glob

def run_command(command):
    print(f"Running: {command}")
    subprocess.check_call(command, shell=True)

def clean():
    print("Cleaning build directories and Chrome profile...")
    
    # 0. Force kill Chrome/Driver so the profile folder isn't "in use"
    print("Closing any active Chrome instances...")
    os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
    os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")

    # 1. Standard build folders
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Removed {folder}")
    
    # 2. Clear Selenium Profile (Test data/Cookies/History)
    profile_path = os.path.join(os.path.expanduser("~"), ".popup_detector_profile")
    if os.path.exists(profile_path):
        try:
            shutil.rmtree(profile_path)
            print(f"Successfully wiped test data: {profile_path}")
        except Exception as e:
            print(f"Warning: Could not clear profile: {e}")

    # 3. Clean spec file
    if os.path.exists("poptest.spec"):
        os.remove("poptest.spec")

def build():
    clean()
    os.makedirs("build/obfuscated", exist_ok=True)
    
    # 1. Obfuscate
    print("\n" + "="*50)
    print("STEP 1: Obfuscating code with PyArmor")
    print("="*50)
    run_command("pyarmor gen -O build/obfuscated main.py license.py")
    
    # 2. Identify the PyArmor Runtime folder
    runtime_folders = glob.glob(os.path.join("build", "obfuscated", "pyarmor_runtime_*"))
    runtime_arg = ""
    if runtime_folders:
        runtime_name = os.path.basename(runtime_folders[0])
        runtime_arg = f'--collect-all {runtime_name}'
        print(f"Found Runtime: {runtime_name}")

    # 3. Build with PyInstaller
    print("\n" + "="*50)
    print("STEP 2: Compiling with PyInstaller")
    print("="*50)
    
    add_data = ["chrome", "chromedriver", "alarm_sounds"]
    sep = ";" if os.name == 'nt' else ":"
    add_data_args = " ".join([f'--add-data "{item}{sep}{item}"' for item in add_data])
    
    collect_packages = ["selenium", "requests", "urllib3", "websocket"]
    collect_str = " ".join([f"--collect-all {pkg}" for pkg in collect_packages])
    
    hidden_imports = [
        "license", "psutil", "platform", "uuid", "json", 
        "hmac", "hashlib", "ctypes", "winsound", "logging", "typing_extensions"
    ]
    hidden_str = " ".join([f"--hidden-import {mod}" for mod in hidden_imports])
    
    cmd = (
        f'pyinstaller --clean --onefile --noconfirm --name poptest '
        f'{runtime_arg} '
        f'{collect_str} '
        f'{add_data_args} '
        f'{hidden_str} '
        f'--paths build/obfuscated '
        f'build/obfuscated/main.py'
    )
    
    run_command(cmd)
    
    print("\n" + "="*50)
    print("Build Complete!")
    print(f"Location: {os.path.abspath('dist/poptest.exe')}")
    print("="*50)

if __name__ == "__main__":
    build()
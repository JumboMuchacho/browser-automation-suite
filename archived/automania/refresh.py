import subprocess
import platform
import sys

def kill_all_windows():
    print("Killing all running Chrome windows...")
    if platform.system() == "Linux" or platform.system() == "Darwin":
        subprocess.run(["pkill", "-f", "/chrome$"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["killall", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif platform.system() == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Unsupported OS for killing Chrome processes.")
        sys.exit(1)
    print("All Chrome windows closed.")

if __name__ == "__main__":
    kill_all_windows()
    while True:
        print("\nWhat would you like to do next?")
        print("1. Launch Chrome in debugging mode (launch_chrome_debug.py)")
        print("2. Run deposit automation (deposit_automation.py)")
        print("3. Run interactive controller (chrome_controller.py)")
        print("4. Exit")
        choice = input("Select an option (1-4): ").strip()
        if choice == "1":
            print("\nLaunching Chrome in debugging mode...\n")
            subprocess.run([sys.executable, "launch_chrome_debug.py"])
        elif choice == "2":
            print("\nRunning deposit_automation.py ...\n")
            subprocess.run([sys.executable, "deposit_automation.py"])
        elif choice == "3":
            print("\nRunning chrome_controller.py ...\n")
            subprocess.run([sys.executable, "chrome_controller.py"])
        elif choice == "4":
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option. Please select 1, 2, 3, or 4.") 
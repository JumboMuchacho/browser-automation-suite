import os
import sys
import subprocess

# List of (description, script filename)
SCRIPTS = [
    ("One-Click Full Automation (Kill Chrome, Launch Debug, Run Automation)", "__one_click__"),
    ("Launch Chrome with Debugging", "launch_chrome_debug.py"),
    ("Deposit Automation", "deposit_automation.py"),
    ("Chrome Controller", "chrome_controller.py"),
    ("Test Popup Automation (poptest.py)", "poptest.py"),
    ("Get Chrome Profile Names", "get_chrome_profile_names.py"),
    ("Refresh Automation (Kill all Chrome windows)", "refresh.py"),
]

def in_venv():
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )

def one_click_full_automation():
    print("\n[Step 1/3] Killing all Chrome windows...")
    subprocess.run([sys.executable, "refresh.py"])
    print("\n[Step 2/3] Launching Chrome in debugging mode...")
    subprocess.run([sys.executable, "launch_chrome_debug.py"])
    input("\nPlease log in and set up your Chrome tabs as needed, then press Enter to continue to automation...")
    print("\n[Step 3/3] Running main automation (chrome_controller.py)...")
    subprocess.run([sys.executable, "chrome_controller.py"])
    print("\nAutomation complete.")

def main():
    if not in_venv():
        print("WARNING: You are not running inside a virtual environment!\nPlease activate your venv before running this script.")
        sys.exit(1)

    while True:
        print("\n=== Main Menu ===")
        for i, (desc, _) in enumerate(SCRIPTS, 1):
            print(f"{i}. {desc}")
        print("0. Exit")

        try:
            choice = int(input("Select an option: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if choice == 0:
            print("Exiting.")
            break
        elif 1 <= choice <= len(SCRIPTS):
            desc, script = SCRIPTS[choice - 1]
            if script == "__one_click__":
                one_click_full_automation()
            else:
                if not os.path.exists(script):
                    print(f"Script '{script}' not found.")
                    continue
                print(f"\n--- Running: {script} ---\n")
                subprocess.run([sys.executable, script])
                print(f"\n--- Finished: {script} ---\n")
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main() 
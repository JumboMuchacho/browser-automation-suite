import os
import sys
import time
import psutil
import logging

from license import ensure_valid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# ------------------------------
# Configuration
# ------------------------------
LICENSE_SERVER_URL = "https://license-server-lewp.onrender.com"

def resource_path(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)

# ------------------------------
# Browser & Popup Helpers
# ------------------------------
def detect_popup(driver, selectors):
    for sel in selectors:
        try:
            if sel["type"] == "css":
                return driver.find_element(By.CSS_SELECTOR, sel["value"])
            if sel["type"] == "xpath":
                return driver.find_element(By.XPATH, sel["value"])
        except NoSuchElementException:
            pass
    return None

def play_alarm(path):
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME)
    except Exception as e:
        print(f"Audio Error: {e}")

def close_existing_chrome():
    chrome_exe = resource_path("chrome/chrome.exe")
    for proc in psutil.process_iter(["exe"]):
        try:
            if proc.info["exe"] and os.path.exists(chrome_exe) and os.path.samefile(proc.info["exe"], chrome_exe):
                proc.kill()
        except:
            pass

def create_driver():
    close_existing_chrome()
    chrome_bin = resource_path("chrome/chrome.exe")
    driver_bin = resource_path("chromedriver/chromedriver.exe")

    profile = os.path.join(os.path.expanduser("~"), ".poptest_profile")
    os.makedirs(profile, exist_ok=True)

    options = Options()
    options.binary_location = chrome_bin
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("detach", False)

    service = Service(driver_bin)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def run_automation():
    selectors = [
        # 🔔 Error Message (Alarm Trigger)
        {
            "type": "xpath",
            "value": "//div[contains(@class, 'commonModal-wrap')]"
                     "//div[contains(@class, 'message') and contains(., 'no USDT transaction')]"
        },

        # 🔁 Try Again Later Button
        {
            "type": "xpath",
            "value": "//div[contains(@class, 'commonModal-wrap')]"
                     "//div[contains(@class, 'buttonBox')]"
                     "//div[contains(., 'Try Again Later')]"
        }
    ]

    alarm_file = resource_path("alarm_sounds/carrousel.wav")
   
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*65)
    print(" >> TAPTAP 2.0  << ".center(65))
    print("="*65)
    print("\n  STEPS TO CONFIGURE:")
    print("  [1]  Click 'Add +' then 'continue without account'\n       If add + is missing try click the profile icon on top right of the window \n       Then select Manage Chromium Profiles")
    print("  [2]  Your created accounts will be there next time you visit")
    print("  [3]  Log into the website and navigate to submit page")
    print("  [4]  A notification will sound when deposit address lands")
    print("-" * 65)
    print("  [X] Engage Autoclicker")
    print("  [X] Adjust volume!")
    print("-" * 65)
    print("  (i) STATUS: Monitoring...")
    print("  [#] For support, Whatsapp: +254725766022")
    print("\n" + "="*65)

    driver = create_driver()
    start_time = time.time()
    cleared = False

    try:
        while True:
            if not cleared and (time.time() - start_time) > 180:
                os.system('cls' if os.name == 'nt' else 'clear')
                # Use simple characters for the running status
                print(f"[{time.strftime('%H:%M:%S')}] (*) SCRIPT RUNNING...\nClosing this window will terminate it!\nYou may minimize this window and proceed.")
                print("Bonne chasse! >>")
                cleared = True

            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if detect_popup(driver, selectors):
                    if not cleared:
                        os.system('cls' if os.name == 'nt' else 'clear')
                        cleared = True
                    # '!' is the safest alert icon for terminal
                    print(f"{time.strftime('%H:%M:%S')} ! ALERT: Address just landed, Check it out...")
                    play_alarm(alarm_file)
            
            time.sleep(45) 

    except (WebDriverException, KeyboardInterrupt):
        print("\nExiting script...")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    # Using simple brackets for the loading state

    if not ensure_valid(LICENSE_SERVER_URL):
        
        max_attempts = 3
        authenticated = False

        for attempt in range(1, max_attempts + 1):
            user_key = input(f"Input your issued Key and click enter to proceed\n:").strip()

            print("\nVerifying...", end="\r")

            if ensure_valid(LICENSE_SERVER_URL, user_key):
                authenticated = True
                break
            else:
                print(f"✗ Verify failed!")
                if attempt < max_attempts:
                    print(" Please try again.\n")

        if not authenticated:
            print("\n[!] Authorization Failed... Contact admin for queries: +254725766022")
            input("\nClick Enter to exit...")
            sys.exit(1)

    run_automation()
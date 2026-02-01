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
    """ Get absolute path to resource, works for dev and for PyInstaller """
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
    """Kills any chrome instances running from our specific bundle folder"""
    chrome_exe = resource_path("chrome/chrome.exe")
    for proc in psutil.process_iter(["exe"]):
        try:
            # os.path.samefile ensures we don't kill the user's personal Chrome
            if proc.info["exe"] and os.path.exists(chrome_exe) and os.path.samefile(proc.info["exe"], chrome_exe):
                proc.kill()
        except:
            pass

def create_driver():
    close_existing_chrome()

    chrome_bin = resource_path("chrome/chrome.exe")
    driver_bin = resource_path("chromedriver/chromedriver.exe")

    # Local profile so login sessions persist
    profile = os.path.join(os.path.expanduser("~"), ".popup_detector_profile")
    os.makedirs(profile, exist_ok=True)

    options = Options()
    options.binary_location = chrome_bin
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("detach", True)

    service = Service(driver_bin)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

# ------------------------------
# Execution Loop
# ------------------------------
def run_automation():
    selectors = [
        {"type": "css", "value": "#app div.commonModal-wrap div.normal div.message"},
        {"type": "css", "value": "#app div.commonModal-wrap div.normal div.title"},
    ]
    
    alarm_file = resource_path("alarm_sounds/carrousel.wav")
    
    print("🚀 Launching Browser...")
    print("In the opened Chromium Tab navigate as you would and create profiles and login to gamemania, copy paste the website URL from the browser address bar to the other open tabs log in and start clicking...")
    print("You will be notified if an address lands, adjust volume accordingly.")       
    driver = create_driver()

    try:
        while True:
            # Check all open tabs
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if detect_popup(driver, selectors):
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠ Address detected!")
                    play_alarm(alarm_file)
            time.sleep(60)
    except (WebDriverException, KeyboardInterrupt):
        print("\nBye Bye...")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("🔐 Validating credentials...")

    # 1. Check cache first (silent check)
    if not ensure_valid(LICENSE_SERVER_URL):
        print("❗ Please Enter valid license key")
        
        max_attempts = 3
        authenticated = False

        # 2. Loop for 3 attempts
        for attempt in range(1, max_attempts + 1):
            user_key = input(f"Input valid credentials(Attempt {attempt}/{max_attempts}) or 'q' to quit: ").strip()

            if user_key.lower() == 'q' or not user_key:
                sys.exit(0)

            if ensure_valid(LICENSE_SERVER_URL, user_key):
                authenticated = True
                break  # Exit loop on success
            else:
                print(f"❌ Your authentication is invalid.")
                if attempt < max_attempts:
                    print("Please try again.\n")

        if not authenticated:
            print("🚫 Auth Failed... Do contact admin for aid\nTel:0725766022")
            input("\nClick Enter to exit...")
            sys.exit(1)

    # 3. Success
    print("✅ Access Granted.")
    run_automation()
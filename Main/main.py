import os
import sys
import time
import psutil

from license import ensure_valid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# ------------------------------
# Configuration (NO .env)
# ------------------------------
LICENSE_SERVER_URL = "https://license-server-lewp.onrender.com"

# ------------------------------
# PyInstaller-safe paths
# ------------------------------
def resource_path(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)

# ------------------------------
# License validation
# ------------------------------
print("🔐 Validating license...")

if not ensure_valid(LICENSE_SERVER_URL):
    print("❗ License not activated on this device.")
    user_key = input("Enter license key (or q to quit): ").strip()

    if user_key.lower() == "q":
        sys.exit(1)

    if not ensure_valid(LICENSE_SERVER_URL, user_key):
        print("❌ Invalid or revoked license.")
        sys.exit(1)

print("✅ License valid")

# ------------------------------
# Browser helpers
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
    except:
        pass

def close_existing_chrome():
    chrome_exe = resource_path("chrome/chrome.exe")
    for proc in psutil.process_iter(["exe"]):
        try:
            if proc.info["exe"] and os.path.samefile(proc.info["exe"], chrome_exe):
                proc.kill()
        except:
            pass

def create_driver():
    close_existing_chrome()

    chrome = resource_path("chrome/chrome.exe")
    driver_bin = resource_path("chromedriver/chromedriver.exe")

    profile = os.path.join(os.path.expanduser("~"), ".popup_detector_profile")
    os.makedirs(profile, exist_ok=True)

    options = Options()
    options.binary_location = chrome
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
# Main loop
# ------------------------------
def run_browser():
    selectors = [
        {"type": "css", "value": "#app div.commonModal-wrap div.normal div.message"},
        {"type": "css", "value": "#app div.commonModal-wrap div.normal div.title"},
    ]

    alarm = resource_path("alarm_sounds/carrousel.wav")
    driver = create_driver()

    try:
        while True:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if detect_popup(driver, selectors):
                    print("⚠ Popup detected")
                    play_alarm(alarm)
            time.sleep(30)
    except WebDriverException:
        pass
    finally:
        driver.quit()

if __name__ == "__main__":
    run_browser()

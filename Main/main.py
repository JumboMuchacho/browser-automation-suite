import os
import sys
import time
import psutil
from dotenv import load_dotenv

# Load .env for license info
load_dotenv()

from license import ensure_valid, make_fingerprint

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# ---------- PYINSTALLER SAFE PATH ----------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# -------------------------------
# LICENSE CHECK
# -------------------------------
LICENSE_SERVER = os.getenv("LICENSE_SERVER_URL")
LICENSE_KEY = os.getenv("LICENSE_KEY")

if not LICENSE_SERVER or not LICENSE_KEY:
    print("LICENSE_SERVER_URL or LICENSE_KEY not set in .env. Exiting.")
    sys.exit(1)

if not ensure_valid(LICENSE_SERVER, LICENSE_KEY):
    print("License invalid or not usable. Exiting.")
    sys.exit(1)

print("License valid. Starting application...")

# -------------------------------
# Browser functions
# -------------------------------
def detect_popup(driver, selectors):
    for sel in selectors:
        try:
            if sel["type"] == "css":
                elem = driver.find_element(By.CSS_SELECTOR, sel["value"])
            elif sel["type"] == "xpath":
                elem = driver.find_element(By.XPATH, sel["value"])
            else:
                continue
            if elem:
                return elem
        except NoSuchElementException:
            continue
    return None

def play_alarm(audio_file):
    try:
        import winsound
        winsound.PlaySound(audio_file, winsound.SND_FILENAME)
    except Exception as e:
        print(f"Could not play alarm: {e}")

def close_existing_chrome():
    chrome_exe = resource_path(os.path.join("chrome", "chrome.exe"))
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            if proc.info['exe'] and os.path.samefile(proc.info['exe'], chrome_exe):
                proc.kill()
        except Exception:
            continue

def create_driver():
    close_existing_chrome()

    chrome_path = resource_path(os.path.join("chrome", "chrome.exe"))
    chromedriver_path = resource_path(os.path.join("chromedriver", "chromedriver.exe"))

    profile_dir = os.path.join(os.path.expanduser("~"), ".popup_detector_profile")
    os.makedirs(profile_dir, exist_ok=True)

    if not os.path.exists(chrome_path) or not os.path.exists(chromedriver_path):
        raise FileNotFoundError("Chrome or ChromeDriver not found.")

    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("detach", True)

    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def run_browser():
    # -------------------------------
    # Combined popup selectors (old + new)
    # -------------------------------
    selectors = [
        # Old selectors
        {"type": "css", "value": ".popup"},
        {"type": "xpath", "value": "//div[contains(@class, 'modal')]"},
        {"type": "xpath", "value": "//*[@id='app']/div[4]/div[2]/div[1]/div[2]/div/div[3]"},

        # New selectors
        {"type": "css", "value": "#app > div.flexcc.commonModal-wrap > div > div.normal > div.message"},
        {"type": "xpath", "value": "//*[@id=\"app\"]/div[2]/div/div[2]/div[2]"},
        {"type": "css", "value": ".bsbb.modifyAvatarBox"},
    ]

    alarm_file = resource_path(os.path.join("alarm_sounds", "carrousel.wav"))

    driver = None
    try:
        print("Launching Chrome...")
        driver = create_driver()
        print("Monitoring for popups... Press CTRL+C to stop.")

        while True:
            try:
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if detect_popup(driver, selectors):
                        print("[Popup detected]")
                        play_alarm(alarm_file)
                time.sleep(30)
            except WebDriverException:
                print("Browser session ended.")
                break

    except KeyboardInterrupt:
        print("User stopped the script.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# -------------------------------
# MAIN
# -------------------------------
def main():
    run_browser()


if __name__ == "__main__":
    main()


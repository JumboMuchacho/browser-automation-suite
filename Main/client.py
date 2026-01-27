import os
import sys
import time
import json
import uuid
import platform
import hashlib

from license import ensure_valid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import psutil

# ---------- PYINSTALLER SAFE PATH ----------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def make_fingerprint():
    """Generate a device fingerprint for licensing"""
    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xFF:02x}" for ele in range(0, 8*6, 8)][::-1])
    cpu = platform.processor() or ""
    disk = ""
    if platform.system() == "Windows":
        try:
            import subprocess
            disk = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True, text=True)
            for line in disk.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("serialnumber"):
                    disk = line
                    break
        except Exception:
            disk = ""
    seed = "|".join([cpu, disk, mac])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


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
    """Kill any Chrome processes using our bundled Chrome"""
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

    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Chrome not found: {chrome_path}")
    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(f"ChromeDriver not found: {chromedriver_path}")

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
    selectors = [
        {"type": "css", "value": ".popup"},
        {"type": "xpath", "value": "//div[contains(@class, 'modal')]"},
        {"type": "xpath", "value": "//*[@id='app']/div[4]/div[2]/div[1]/div[2]/div/div[3]"},
        {"type": "css", "value": "#app > div.reviseAvatar-wrap > div.gmRA > div.drawer-wrap.drawer-middle > div.drawer-box > div > div.bsbb.modifyAvatarBox"},
        {"type": "xpath", "value": "//div[contains(@class, 'normal')][.//div[contains(@class, 'title') and contains(text(), 'Verify Completed')]]"},
    ]

    alarm_file = resource_path(os.path.join("alarm_sounds", "carrousel.wav"))

    driver = None
    try:
        print("Launching Chrome...")
        driver = create_driver()
        print("===== Hi, welcome to POPTEST =====")
        print("Monitoring for popups... Press CTRL+C to stop.\n")
        while True:
            try:
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if detect_popup(driver, selectors):
                        print("[Popup detected]")
                        play_alarm(alarm_file)
                time.sleep(30)
            except WebDriverException:
                print("Browser session ended. Exiting cleanly.")
                break
    except KeyboardInterrupt:
        print("User stopped the script.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    license_server = os.getenv(
        "LICENSE_SERVER_URL",
        "https://license-server-production-c88f.up.railway.app",
    )
    license_key = os.getenv("LICENSE_KEY", "YOUR_LICENSE_KEY_HERE")
    device_id = make_fingerprint()

    if not ensure_valid(license_server, license_key, device_id, offline_days=2, recheck_hours=1):
        print("License invalid or not usable. Exiting.")
        sys.exit(1)

    run_browser()


if __name__ == "__main__":
    main()

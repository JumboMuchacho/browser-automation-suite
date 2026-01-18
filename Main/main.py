import os
import sys
import time

from license import ensure_valid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import psutil  # for process check


# ---------- PYINSTALLER SAFE PATH ----------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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
    """Kill any Chrome process pointing to our bundled Chrome to prevent DevTools port crash"""
    chrome_exe = resource_path(os.path.join("chrome", "chrome.exe"))
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            if proc.info['exe'] and os.path.samefile(proc.info['exe'], chrome_exe):
                proc.kill()
        except Exception: # nosec
            continue

def create_driver():
    close_existing_chrome()

    chrome_path = resource_path(os.path.join("chrome", "chrome.exe"))
    chromedriver_path = resource_path(os.path.join("chromedriver", "chromedriver.exe"))

    # Chrome profile must live outside EXE
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
        {
            "type": "css",
            "value": "#app > div.reviseAvatar-wrap > div.gmRA > div.drawer-wrap.drawer-middle > div.drawer-box > div > div.bsbb.modifyAvatarBox",
        },
        {
            "type": "xpath",
            "value": "//div[contains(@class, 'normal')][.//div[contains(@class, 'title') and contains(text(), 'Verify Completed')]]",
        },
    ]

    alarm_file = resource_path(os.path.join("alarm_sounds", "carrousel.wav"))

    driver = None
    try:
        print("Launching Chrome...")
        driver = create_driver()
        print("===== Hi, welcome to POPTEST Free Trial. Test out our tool tell If you'd like to purchase =====")
        print("This tool monitors for the deposit address popup on your screen.")
        print("Instructions:")
        print("1. Chrome will launch automatically.")
        print("2. You MUST manually navigate to the website all through to auto clicking submit.")
        print("3. Keep Chrome open && this Terminal window open; closing it will kill the script.")
        print("4. If Chrome is already running, the script will close the previous instance first. So save your work!!")
        print("5. Press CTRL+C here in this terminal to stop the script at any time.\n")
        print("+++ On Trial Expiry date Jan 15th you'll have to Cash in to use +++")
        print("     For any querries call/whatsapp admin 0725766022     ")
        while True:
            try:
                handles = driver.window_handles
                for handle in handles:
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
            except Exception: # nosec
                pass


def main():
    license_server = os.getenv(
        "LICENSE_SERVER_URL",
        "https://license-server-production-c88f.up.railway.app",
    )

    if not ensure_valid(
        license_server,
        app_dir=None,
        recheck_hours=1,
        offline_days=2,
    ):
        print("License invalid or not usable. Exiting.")
        sys.exit(1)

    run_browser()


if __name__ == "__main__":
    main()

# Poptest - Clean Local Version
# Popup Detection Script with VNC Support
# Place this file, requirements.txt, and alarm_sounds/carrousel.wav in the same directory for plug-and-play use.

import os
import sys
import time
import subprocess
import socket
import tempfile
import logging
import json
import re
from typing import Any, Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
import requests
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
import io
from PIL import Image
from shutil import which

import os
import sys

def check_binaries():
    paths = [
        "chromendriver/chrome-win64/chrome.exe",
        "chromendriver/chromedriver-win64/chromedriver.exe"
    ]
    for p in paths:
        if not os.path.exists(p):
            print(f"❌ ERROR: Missing {p}")
            print("Please follow the README to install browser binaries.")
            sys.exit(1)

check_binaries()

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Config loading/validation ---
def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def validate_config(config: Dict[str, Any]) -> None:
    required = ["bot_token", "chat_id", "alarm_sound", "popup_selectors"]
    for key in required:
        if key not in config or not config[key]:
            raise ValueError(f"Missing required config field: {key}")
    if not isinstance(config["popup_selectors"], list):
        raise ValueError("popup_selectors must be a list of selector dicts")
    for sel in config["popup_selectors"]:
        if not isinstance(sel, dict) or "type" not in sel or "value" not in sel:
            raise ValueError(f"Invalid selector in popup_selectors: {sel}")
    
    # Validate refresh configuration
    if config.get("refresh_enabled", False):
        refresh_interval = config.get("refresh_interval_minutes", 10)
        if refresh_interval < 1:
            raise ValueError("refresh_interval_minutes must be at least 1 minute")
        if refresh_interval > 1440:  # 24 hours
            raise ValueError("refresh_interval_minutes cannot exceed 1440 minutes (24 hours)")
        logger.info(f"Refresh enabled: every {refresh_interval} minutes")
    else:
        logger.info("Refresh functionality disabled")

# --- Chrome launching and popup detection ---
def launch_chrome_with_vnc(user_data_dir: str, vnc_port: int = 5900, use_vnc: bool = False) -> tuple[subprocess.Popen | None, subprocess.Popen | None]:
    """Launch Chrome with optional VNC support for remote viewing"""
    xvfb_proc, vnc_proc = None, None
    
    if use_vnc:
        # Start Xvfb (virtual display) for VNC
        try:
            xvfb_cmd = ["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-ac"]
            xvfb_proc = subprocess.Popen(xvfb_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            # Start VNC server
            vnc_cmd = ["x11vnc", "-display", ":99", "-nopw", "-listen", "localhost", "-xkb", "-ncache", "10", "-ncache_cr", "-forever"]
            vnc_proc = subprocess.Popen(vnc_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            logger.info(f"VNC server started on port {vnc_port}")
            logger.info(f"Connect with: vncviewer localhost:{vnc_port}")
        except Exception as e:
            logger.warning(f"Could not start VNC: {e}")
            xvfb_proc, vnc_proc = None, None
    else:
        logger.info("Running Chrome on local display (no VNC)")
    
    return xvfb_proc, vnc_proc

def detect_popup(driver: WebDriver, selectors: List[Dict[str, str]]) -> Optional[object]:
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

def extract_popup_text(popup_elem, config: Dict[str, Any]) -> Dict[str, str]:
    """Extract text content from popup element using precise HTML parsing"""
    extracted_data = {
        "full_text": "",
        "deposit_address": "",
        "summary": "",
        "raw_html": ""
    }
    
    try:
        # Get the outer HTML for precise extraction
        raw_html = popup_elem.get_attribute('outerHTML')
        extracted_data["raw_html"] = raw_html
        
        # Get the full text content
        full_text = popup_elem.text.strip()
        extracted_data["full_text"] = full_text
        
        # Extract deposit address using precise text parsing
        if config.get("text_extraction", {}).get("extract_deposit_address", False):
            # Method 1: Look for "deposit address is" and extract everything after it
            deposit_address = extract_deposit_address_precise(full_text)
            if deposit_address:
                extracted_data["deposit_address"] = deposit_address
            else:
                # Method 2: Fallback to regex if precise method fails
                pattern = config.get("text_extraction", {}).get("deposit_address_pattern", "deposit address is\\s*([A-Za-z0-9]+)")
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    extracted_data["deposit_address"] = match.group(1)
        
        # Create a summary for Telegram
        lines = full_text.split('\n')
        if len(lines) >= 4:
            # Get first line (usually the main message)
            first_line = lines[0].strip()
            # Get the deposit address line if found
            deposit_line = ""
            for line in lines:
                if "deposit address" in line.lower():
                    deposit_line = line.strip()
                    break
            
            summary_parts = []
            if first_line:
                summary_parts.append(f"📋 Message: {first_line}")
            if extracted_data["deposit_address"]:
                summary_parts.append(f"💰 Deposit Address: {extracted_data['deposit_address']}")
            elif deposit_line:
                summary_parts.append(f"💰 {deposit_line}")
            
            extracted_data["summary"] = "\n".join(summary_parts)
        else:
            extracted_data["summary"] = f"📋 Popup Text: {full_text[:200]}..."
            
    except Exception as e:
        logger.error(f"Error extracting popup text: {e}")
        extracted_data["summary"] = "❌ Error extracting popup text"
    
    return extracted_data

def extract_deposit_address_precise(full_text: str) -> str:
    """Extract deposit address using precise text parsing, preserving original case"""
    try:
        # Look for various forms of the phrase, but match in a case-insensitive way, then extract from the original text
        search_phrases = [
            "deposit address is",
            "the deposit address is",
            "address is",
            "deposit address:",
            "the address is"
        ]
        
        for phrase in search_phrases:
            # Use regex to find the phrase in a case-insensitive way, but extract from the original text
            import re
            match = re.search(phrase, full_text, re.IGNORECASE)
            if match:
                # Find the position in the original text
                phrase_pos = match.start()
                # Get the text after the phrase, preserving original case
                after_phrase = full_text[phrase_pos + len(match.group(0)):].strip()
                # Extract the address (alphanumeric characters)
                address_match = re.search(r'([A-Za-z0-9]+)', after_phrase)
                if address_match:
                    return address_match.group(1)
                # If no alphanumeric sequence found, take the first word
                words = after_phrase.split()
                if words:
                    clean_word = re.sub(r'[^\w]', '', words[0])
                    if clean_word:
                        return clean_word
        return ""
    except Exception as e:
        logger.error(f"Error in precise address extraction: {e}")
        return ""

# --- Telegram notification ---
def send_telegram_photo(bot_token: str, chat_id: str, image_path: str, caption: Optional[str] = None) -> bool:
    if not os.path.exists(image_path):
        logger.warning(f"Screenshot file {image_path} not found")
        return False
    
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    try:
        with open(image_path, 'rb') as photo:
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            files = {'photo': photo}
            response = requests.post(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                logger.info("Telegram API call successful")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending Telegram photo: {e}")
        return False

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    try:
        data = {'chat_id': chat_id, 'text': message}
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            logger.info(f"Telegram message sent: {message}")
            return True
        else:
            logger.error(f"Telegram API error sending message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

# --- Alarm sound playback ---
def play_alarm(audio_file: str) -> None:
    try:
        if sys.platform == "win32":
            if which("ffplay") is not None:
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", audio_file])
            elif audio_file.lower().endswith('.wav'):
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            else:
                logger.warning("Alarm sound must be .wav for winsound on Windows, or install ffplay.")
        else:
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", audio_file])
    except Exception as e:
        logger.warning(f"Could not play alarm: {e}")

# --- Main orchestration ---
def main() -> None:
    config = load_config()
    try:
        validate_config(config)
    except ValueError as e:
        logger.error(f"Config validation error: {e}")
        return

    user_data_dir = os.path.abspath("./automation_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Check if VNC is requested via environment variable
    use_vnc = os.environ.get("USE_VNC", "false").lower() == "true"
    
    # Start VNC server if requested
    xvfb_proc, vnc_proc = launch_chrome_with_vnc(user_data_dir, use_vnc=use_vnc)
    
    max_retries = config.get("max_retries", 3)
    for attempt in range(max_retries):
        try:
            # Use local Chromium and ChromeDriver with persistent user data
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--enable-unsafe-swiftshader")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            # Set persistent user data directory for session consistency
            options.add_argument(f"--user-data-dir={user_data_dir}")
            if use_vnc:
                options.add_argument("--display=:99")  # Use VNC display
            # Set binary location to local Chromium
            options.binary_location = os.path.abspath("./chromendriver/chrome-win64/chrome.exe")
            # Set service to local chromedriver
            service = Service(os.path.abspath("./chromendriver/chromedriver-win64/chromedriver.exe"))
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(10)
            # Keep Chrome running when script exits
            options.add_experimental_option("detach", True)
            # Don't automatically open any URL - let user navigate manually
            logger.info("Chrome browser launched successfully")
            logger.info("Please navigate to your desired website manually")
            logger.info("Press 'y' and Enter when ready to start automation...")
            break
        except Exception as e:
            logger.error(f"Attempt {attempt+1}: WebDriver failed to start or connect: {e}")
            if attempt == max_retries-1:
                print("[FATAL] Could not start WebDriver after multiple attempts. Exiting.")
                return
            time.sleep(config.get("retry_delay", 5))
    else:
        logger.error("Failed to launch WebDriver after retries.")
        return

    try:
        last_popup_time = 0
        popup_present = False
        screenshot_sent = False
        screenshot_count = 0
        
        # Wait for user input before starting automation
        user_input = input("Press 'y' and Enter when ready to start automation: ").strip().lower()
        if user_input != 'y':
            logger.info("User did not confirm. Exiting...")
            return
        
        logger.info("User confirmed. Starting automation...")
        
        # Start continuous submit button clicking loop
        logger.info("Starting continuous submit button clicking workflow...")
        
        while True:
            window_handles = driver.window_handles
            n_windows = max(1, len(window_handles))
            
            # Submit button clicking DISABLED - only checking for popups
            for handle in window_handles:
                try:
                    driver.switch_to.window(handle)
                    
                    # Submit button clicking is disabled for now
                    # logger.info(f"Clicking submit button in window {handle[:8]}")
                    # submit_clicked = False
                    # submit_selectors = config.get("submit_button_selectors", [])
                    
                    # for submit_selector in submit_selectors:
                    #     try:
                    #         if submit_selector["type"] == "css":
                    #             submit_button = driver.find_element(By.CSS_SELECTOR, submit_selector["value"])
                    #         elif submit_selector["type"] == "xpath":
                    #             submit_button = driver.find_element(By.XPATH, submit_selector["value"])
                    #         else:
                    #             continue
                            
                    #         if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    #             logger.info(f"Found submit button with selector: {submit_selector}")
                    #             submit_button.click()
                    #             logger.info(f"Successfully clicked submit button in window {handle[:8]}")
                    #             submit_clicked = True
                    #             break
                    #     except NoSuchElementException:
                    #         continue
                    #     except Exception as e:
                    #         logger.warning(f"Error clicking submit button with selector {submit_selector}: {e}")
                    #         continue
                    
                    # if not submit_clicked:
                    #     logger.info(f"No submit button found in window {handle[:8]}")
                    
                    # Check for popup (priority check)
                    selectors = config["popup_selectors"]
                    popup_elem = detect_popup(driver, selectors)
                    if popup_elem:
                        now = time.time()
                        throttle = config.get("throttle_seconds", config.get("throttle_minutes", 5)*60)
                        if not popup_present or (now - last_popup_time) >= throttle:
                            logger.info(f"Popup found in window {handle[:8]} - stopping submit loop")
                            
                            # Extract text from popup
                            extracted_text = extract_popup_text(popup_elem, config)
                            logger.info(f"Extracted text: {extracted_text['summary']}")
                            
                            play_alarm(config["alarm_sound"])
                            if not screenshot_sent:
                                # Extract actual Chrome profile name from user data directory
                                def get_chrome_profile_name(user_data_dir: str) -> str:
                                    """Extract exact Chrome profile name from Local State"""
                                    try:
                                        # Read from Chrome's Local State file to get exact profile name
                                        local_state_path = os.path.join(user_data_dir, "Local State")
                                        if os.path.exists(local_state_path):
                                            with open(local_state_path, 'r', encoding='utf-8') as f:
                                                local_state = json.load(f)
                                                profile_info = local_state.get('profile', {}).get('info_cache', {})
                                                last_active_profile = local_state.get('profile', {}).get('last_active_profiles', [])
                                                
                                                if profile_info:
                                                    # Try to get the last active profile first
                                                    if last_active_profile and len(last_active_profile) > 0:
                                                        active_profile = last_active_profile[0]
                                                        if active_profile in profile_info:
                                                            logger.info(f"Active profile name found: {active_profile}")
                                                            return active_profile
                                                    
                                                    # Fallback to first profile if no active profile found
                                                    profile_name = list(profile_info.keys())[0]
                                                    logger.info(f"First profile name found: {profile_name}")
                                                    return profile_name
                                                else:
                                                    logger.error("No profile info found in Local State")
                                                    raise Exception("No profile info available")
                                        else:
                                            logger.error("Local State file not found")
                                            raise Exception("Local State file missing")
                                    except Exception as e:
                                        logger.error(f"Failed to extract exact profile name: {e}")
                                        # Return a clear error indicator instead of fallback
                                        return f"ERROR_NO_PROFILE_{handle[:8]}"
                                
                                # Get the actual profile name
                                profile_name = get_chrome_profile_name(user_data_dir)
                                
                                # Instead of saving screenshot to disk, capture it in memory
                                screenshot_png = driver.get_screenshot_as_png()

                                # Send the screenshot directly to Telegram with profile name as caption
                                def send_telegram_photo_bytes(bot_token, chat_id, image_bytes, caption=None):
                                    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
                                    files = {'photo': ('screenshot.png', image_bytes, 'image/png')}
                                    data = {'chat_id': chat_id}
                                    if caption:
                                        data['caption'] = caption
                                    response = requests.post(url, data=data, files=files, timeout=30)
                                    if response.status_code == 200:
                                        logger.info("Telegram API call successful (in-memory screenshot)")
                                        return True
                                    else:
                                        logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                                        return False

                                if send_telegram_photo_bytes(config["bot_token"], config["chat_id"], screenshot_png, f"Profile: {profile_name}"):

                                        # 2. Extract the code after 'deposit address is' (case-insensitive, but extract as-is)
                                        def extract_code_after_deposit_address_is(text: str) -> str:
                                            match = re.search(r'deposit address is\s*([A-Za-z0-9]+)', text, re.IGNORECASE)
                                            if match:
                                                return match.group(1)
                                            return ''

                                        if isinstance(popup_elem, WebElement):
                                            code = extract_code_after_deposit_address_is(popup_elem.text)
                                            if code:
                                                send_telegram_message(config["bot_token"], config["chat_id"], code)
                                        else:
                                            logger.error("popup_elem is not a WebElement; cannot extract .text")

                                        # 3. Profile name is now sent as caption with screenshot, so no separate message needed
                                        
                                        # 4. Click "try again later" button after notifications are sent
                                        try:
                                            logger.info("Attempting to click 'try again later' button...")
                                            # Look for the try again later button using various selectors
                                            try_again_selectors = config.get("try_again_selectors", [
                                                {"type": "css", "value": "button:contains('try again later')"},
                                                {"type": "xpath", "value": "//button[contains(text(), 'try again later')]"},
                                                {"type": "xpath", "value": "//button[contains(text(), 'Try Again Later')]"},
                                                {"type": "css", "value": ".try-again-button"},
                                                {"type": "xpath", "value": "//*[contains(text(), 'try again later')]"}
                                            ])
                                            
                                            try_again_clicked = False
                                            for selector in try_again_selectors:
                                                try:
                                                    if selector["type"] == "css":
                                                        button = driver.find_element(By.CSS_SELECTOR, selector["value"])
                                                    elif selector["type"] == "xpath":
                                                        button = driver.find_element(By.XPATH, selector["value"])
                                                    else:
                                                        continue
                                                    
                                                    if button and button.is_displayed() and button.is_enabled():
                                                        logger.info(f"Found 'try again later' button with selector: {selector}")
                                                        button.click()
                                                        logger.info("Successfully clicked 'try again later' button")
                                                        try_again_clicked = True
                                                        break
                                                except NoSuchElementException:
                                                    continue
                                                except Exception as e:
                                                    logger.warning(f"Error clicking button with selector {selector}: {e}")
                                                    continue
                                            
                                            if try_again_clicked:
                                                # Wait for page to load after clicking
                                                time.sleep(3)
                                                logger.info("Waiting for page to load after clicking 'try again later'")
                                                
                                                # Extract create time from the new page
                                                create_time = ""
                                                try:
                                                    logger.info("Looking for create time on the new page...")
                                                    create_time_selectors = config.get("create_time_selectors", [
                                                        {"type": "css", "value": "#app > div.USDT-wrap > div.routerViewBox > div > div.width > div.infoBox > div:nth-child(2) .right"},
                                                        {"type": "xpath", "value": "//*[@id=\"app\"]/div[1]/div[1]/div/div[4]/div[5]/div[2]//div[contains(@class, 'right')]"},
                                                        {"type": "xpath", "value": "//div[contains(@class, 'right') and contains(text(), '2025-')]"},
                                                        {"type": "css", "value": "div[data-v-5e11442c].right"}
                                                    ])
                                                    
                                                    for selector in create_time_selectors:
                                                        try:
                                                            if selector["type"] == "css":
                                                                time_element = driver.find_element(By.CSS_SELECTOR, selector["value"])
                                                            elif selector["type"] == "xpath":
                                                                time_element = driver.find_element(By.XPATH, selector["value"])
                                                            else:
                                                                continue
                                                            
                                                            if time_element and time_element.is_displayed():
                                                                create_time = time_element.text.strip()
                                                                logger.info(f"Found create time: {create_time}")
                                                                break
                                                        except NoSuchElementException:
                                                            continue
                                                        except Exception as e:
                                                            logger.warning(f"Error finding create time with selector {selector}: {e}")
                                                            continue
                                                    
                                                    if create_time:
                                                        # Send create time to Telegram
                                                        send_telegram_message(config["bot_token"], config["chat_id"], f"Create Time: {create_time}")
                                                        logger.info(f"Sent create time to Telegram: {create_time}")
                                                    else:
                                                        logger.warning("Could not find create time on the new page")
                                                        
                                                except Exception as e:
                                                    logger.error(f"Error extracting create time: {e}")
                                                
                                                # Start transaction monitoring loop
                                                logger.info("Starting transaction monitoring loop...")
                                                transaction_attempts = 0
                                                max_transaction_attempts = config.get("max_transaction_attempts", 10)
                                                
                                                while transaction_attempts < max_transaction_attempts:
                                                    try:
                                                        # Wait 3 minutes before clicking "Completed Transaction"
                                                        logger.info(f"Waiting 3 minutes before transaction attempt {transaction_attempts + 1}...")
                                                        time.sleep(180)  # 3 minutes
                                                        
                                                        # Look for "Completed Transaction" button
                                                        completed_transaction_clicked = False
                                                        completed_transaction_selectors = config.get("completed_transaction_selectors", [
                                                            {"type": "css", "value": "#app > div.USDT-wrap > div.routerViewBox > div > div.buttonBox.status1 > div.button.rightB"},
                                                            {"type": "xpath", "value": "//*[@id=\"app\"]/div[1]/div[1]/div/div[7]/div[3]"},
                                                            {"type": "xpath", "value": "//div[contains(@class, 'button') and contains(@class, 'rightB') and contains(text(), 'Completed Transaction')]"},
                                                            {"type": "css", "value": "div[data-v-5e11442c].button.rightB"}
                                                        ])
                                                        
                                                        for selector in completed_transaction_selectors:
                                                            try:
                                                                if selector["type"] == "css":
                                                                    button = driver.find_element(By.CSS_SELECTOR, selector["value"])
                                                                elif selector["type"] == "xpath":
                                                                    button = driver.find_element(By.XPATH, selector["value"])
                                                                else:
                                                                    continue
                                                                
                                                                if button and button.is_displayed() and button.is_enabled():
                                                                    logger.info(f"Found 'Completed Transaction' button with selector: {selector}")
                                                                    button.click()
                                                                    logger.info("Successfully clicked 'Completed Transaction' button")
                                                                    completed_transaction_clicked = True
                                                                    break
                                                            except NoSuchElementException:
                                                                continue
                                                            except Exception as e:
                                                                logger.warning(f"Error clicking 'Completed Transaction' button with selector {selector}: {e}")
                                                                continue
                                                        
                                                        if completed_transaction_clicked:
                                                            # Wait 3 seconds to avoid bot detection
                                                            time.sleep(3)
                                                            logger.info("Waiting 3 seconds after clicking 'Completed Transaction'")
                                                            
                                                            # Check for popup reappearance
                                                            popup_reappeared = False
                                                            for sel in config["popup_selectors"]:
                                                                try:
                                                                    if sel["type"] == "css":
                                                                        popup_elem = driver.find_element(By.CSS_SELECTOR, sel["value"])
                                                                    elif sel["type"] == "xpath":
                                                                        popup_elem = driver.find_element(By.XPATH, sel["value"])
                                                                    else:
                                                                        continue
                                                                    
                                                                    if popup_elem and popup_elem.is_displayed():
                                                                        logger.info("Popup reappeared after clicking 'Completed Transaction'")
                                                                        popup_reappeared = True
                                                                        
                                                                        # Click "Try Again Later" again
                                                                        try_again_clicked = False
                                                                        for try_selector in config.get("try_again_selectors", []):
                                                                            try:
                                                                                if try_selector["type"] == "css":
                                                                                    try_button = driver.find_element(By.CSS_SELECTOR, try_selector["value"])
                                                                                elif try_selector["type"] == "xpath":
                                                                                    try_button = driver.find_element(By.XPATH, try_selector["value"])
                                                                                else:
                                                                                    continue
                                                                                
                                                                                if try_button and try_button.is_displayed() and try_button.is_enabled():
                                                                                    logger.info(f"Clicking 'Try Again Later' again with selector: {try_selector}")
                                                                                    try_button.click()
                                                                                    logger.info("Successfully clicked 'Try Again Later' again")
                                                                                    try_again_clicked = True
                                                                                    time.sleep(3)  # Wait 3 seconds
                                                                                    break
                                                                            except NoSuchElementException:
                                                                                continue
                                                                            except Exception as e:
                                                                                logger.warning(f"Error clicking 'Try Again Later' again with selector {try_selector}: {e}")
                                                                                continue
                                                                        
                                                                        if not try_again_clicked:
                                                                            # Try clicking any other button in popup
                                                                            logger.info("Looking for any clickable button in popup...")
                                                                            any_button_selectors = config.get("any_button_selectors", [
                                                                                {"type": "xpath", "value": "//button"},
                                                                                {"type": "xpath", "value": "//div[contains(@class, 'button')]"},
                                                                                {"type": "css", "value": "button"},
                                                                                {"type": "css", "value": "[class*='button']"}
                                                                            ])
                                                                            
                                                                            for any_selector in any_button_selectors:
                                                                                try:
                                                                                    if any_selector["type"] == "css":
                                                                                        any_button = driver.find_element(By.CSS_SELECTOR, any_selector["value"])
                                                                                    elif any_selector["type"] == "xpath":
                                                                                        any_button = driver.find_element(By.XPATH, any_selector["value"])
                                                                                    else:
                                                                                        continue
                                                                                    
                                                                                    if any_button and any_button.is_displayed() and any_button.is_enabled():
                                                                                        logger.info(f"Clicking any button in popup with selector: {any_selector}")
                                                                                        any_button.click()
                                                                                        logger.info("Successfully clicked any button in popup")
                                                                                        time.sleep(3)  # Wait 3 seconds
                                                                                        break
                                                                                except NoSuchElementException:
                                                                                    continue
                                                                                except Exception as e:
                                                                                    logger.warning(f"Error clicking any button with selector {any_selector}: {e}")
                                                                                    continue
                                                                        
                                                                        break
                                                                except NoSuchElementException:
                                                                    continue
                                                                except Exception as e:
                                                                    logger.warning(f"Error checking for popup reappearance: {e}")
                                                                    continue
                                                            
                                                            if not popup_reappeared:
                                                                # Check for successful transaction
                                                                success_detected = False
                                                                success_selectors = config.get("success_selectors", [
                                                                    {"type": "css", "value": "#app > div.USDT-wrap > div.routerViewBox > div > div.buttonBox.status3 > div.congratulations"},
                                                                    {"type": "xpath", "value": "//*[@id=\"app\"]/div[1]/div[1]/div/div[7]/div[2]"},
                                                                    {"type": "xpath", "value": "//div[contains(@class, 'congratulations')]"},
                                                                    {"type": "css", "value": "div[data-v-5e11442c].congratulations"}
                                                                ])
                                                                
                                                                for success_selector in success_selectors:
                                                                    try:
                                                                        if success_selector["type"] == "css":
                                                                            success_elem = driver.find_element(By.CSS_SELECTOR, success_selector["value"])
                                                                        elif success_selector["type"] == "xpath":
                                                                            success_elem = driver.find_element(By.XPATH, success_selector["value"])
                                                                        else:
                                                                            continue
                                                                        
                                                                        if success_elem and success_elem.is_displayed():
                                                                            logger.info("Successful transaction detected!")
                                                                            success_detected = True
                                                                            
                                                                            # Click "Back" button
                                                                            back_clicked = False
                                                                            back_selectors = config.get("back_selectors", [
                                                                                {"type": "css", "value": "#app > div.USDT-wrap > div.routerViewBox > div > div.topBox > div > div.headBack-left > div > div"},
                                                                                {"type": "xpath", "value": "//*[@id=\"app\"]/div[1]/div[1]/div/div[1]/div/div[1]/div/div"},
                                                                                {"type": "xpath", "value": "//div[contains(@class, 'headBack-icon')]"},
                                                                                {"type": "css", "value": "div[data-v-f57f7708].headBack-icon"}
                                                                            ])
                                                                            
                                                                            for back_selector in back_selectors:
                                                                                try:
                                                                                    if back_selector["type"] == "css":
                                                                                        back_button = driver.find_element(By.CSS_SELECTOR, back_selector["value"])
                                                                                    elif back_selector["type"] == "xpath":
                                                                                        back_button = driver.find_element(By.XPATH, back_selector["value"])
                                                                                    else:
                                                                                        continue
                                                                                    
                                                                                    if back_button and back_button.is_displayed() and back_button.is_enabled():
                                                                                        logger.info(f"Clicking 'Back' button with selector: {back_selector}")
                                                                                        back_button.click()
                                                                                        logger.info("Successfully clicked 'Back' button")
                                                                                        back_clicked = True
                                                                                        break
                                                                                except NoSuchElementException:
                                                                                    continue
                                                                                except Exception as e:
                                                                                    logger.warning(f"Error clicking 'Back' button with selector {back_selector}: {e}")
                                                                                    continue
                                                                            
                                                                            if back_clicked:
                                                                                logger.info("Transaction monitoring completed successfully")
                                                                                
                                                                                # Wait for page to load after clicking back
                                                                                time.sleep(3)
                                                                                logger.info("Waiting for USDT network selection page to load...")
                                                                                
                                                                                # Detect USDT network selection page and restart process
                                                                                try:
                                                                                    logger.info("Detecting USDT network selection page...")
                                                                                    usdt_page_selectors = config.get("usdt_page_selectors", [])
                                                                                    
                                                                                    usdt_page_detected = False
                                                                                    for selector in usdt_page_selectors:
                                                                                        try:
                                                                                            if selector["type"] == "css":
                                                                                                usdt_elem = driver.find_element(By.CSS_SELECTOR, selector["value"])
                                                                                            elif selector["type"] == "xpath":
                                                                                                usdt_elem = driver.find_element(By.XPATH, selector["value"])
                                                                                            else:
                                                                                                continue
                                                                                            
                                                                                            if usdt_elem and usdt_elem.is_displayed():
                                                                                                logger.info("USDT network selection page detected")
                                                                                                usdt_page_detected = True
                                                                                                break
                                                                                        except NoSuchElementException:
                                                                                            continue
                                                                                        except Exception as e:
                                                                                            logger.warning(f"Error detecting USDT page with selector {selector}: {e}")
                                                                                            continue
                                                                                    
                                                                                    if usdt_page_detected:
                                                                                        # Select network (BNB Smart Chain by default, or Tron if configured)
                                                                                        network_to_select = config.get("preferred_network", "BNB Smart Chain(BEP20)")
                                                                                        logger.info(f"Selecting network: {network_to_select}")
                                                                                        
                                                                                        if network_to_select == "Tron(TRC20)":
                                                                                            # First click BNB to show dropdown, then select Tron
                                                                                            bnb_selectors = config.get("bnb_selectors", [])
                                                                                            
                                                                                            bnb_clicked = False
                                                                                            for bnb_selector in bnb_selectors:
                                                                                                try:
                                                                                                    if bnb_selector["type"] == "css":
                                                                                                        bnb_elem = driver.find_element(By.CSS_SELECTOR, bnb_selector["value"])
                                                                                                    elif bnb_selector["type"] == "xpath":
                                                                                                        bnb_elem = driver.find_element(By.XPATH, bnb_selector["value"])
                                                                                                    else:
                                                                                                        continue
                                                                                                    
                                                                                                    if bnb_elem and bnb_elem.is_displayed() and bnb_elem.is_enabled():
                                                                                                        logger.info("Clicking BNB Smart Chain to show dropdown")
                                                                                                        bnb_elem.click()
                                                                                                        time.sleep(2)  # Wait for dropdown
                                                                                                        bnb_clicked = True
                                                                                                        break
                                                                                                except NoSuchElementException:
                                                                                                    continue
                                                                                                except Exception as e:
                                                                                                    logger.warning(f"Error clicking BNB with selector {bnb_selector}: {e}")
                                                                                                    continue
                                                                                            
                                                                                            if bnb_clicked:
                                                                                                # Now select Tron from dropdown
                                                                                                tron_selectors = config.get("tron_selectors", [])
                                                                                                
                                                                                                for tron_selector in tron_selectors:
                                                                                                    try:
                                                                                                        if tron_selector["type"] == "css":
                                                                                                            tron_elem = driver.find_element(By.CSS_SELECTOR, tron_selector["value"])
                                                                                                        elif tron_selector["type"] == "xpath":
                                                                                                            tron_elem = driver.find_element(By.XPATH, tron_selector["value"])
                                                                                                        else:
                                                                                                            continue
                                                                                                        
                                                                                                        if tron_elem and tron_elem.is_displayed() and tron_elem.is_enabled():
                                                                                                            logger.info("Selecting Tron(TRC20) from dropdown")
                                                                                                            tron_elem.click()
                                                                                                            break
                                                                                                    except NoSuchElementException:
                                                                                                        continue
                                                                                                    except Exception as e:
                                                                                                        logger.warning(f"Error selecting Tron with selector {tron_selector}: {e}")
                                                                                                        continue
                                                                                        else:
                                                                                            # Select BNB Smart Chain directly
                                                                                            bnb_selectors = config.get("bnb_selectors", [])
                                                                                            
                                                                                            for bnb_selector in bnb_selectors:
                                                                                                try:
                                                                                                    if bnb_selector["type"] == "css":
                                                                                                        bnb_elem = driver.find_element(By.CSS_SELECTOR, bnb_selector["value"])
                                                                                                    elif bnb_selector["type"] == "xpath":
                                                                                                        bnb_elem = driver.find_element(By.XPATH, bnb_selector["value"])
                                                                                                    else:
                                                                                                        continue
                                                                                                    
                                                                                                    if bnb_elem and bnb_elem.is_displayed() and bnb_elem.is_enabled():
                                                                                                        logger.info("Selecting BNB Smart Chain(BEP20)")
                                                                                                        bnb_elem.click()
                                                                                                        break
                                                                                                except NoSuchElementException:
                                                                                                    continue
                                                                                                except Exception as e:
                                                                                                    logger.warning(f"Error selecting BNB with selector {bnb_selector}: {e}")
                                                                                                    continue
                                                                                        
                                                                                        # Wait for network selection to complete
                                                                                        time.sleep(2)
                                                                                        
                                                                                        # Select first deposit amount
                                                                                        logger.info("Selecting first deposit amount...")
                                                                                        amount_selectors = config.get("amount_selectors", [])
                                                                                        
                                                                                        amount_selected = False
                                                                                        for amount_selector in amount_selectors:
                                                                                            try:
                                                                                                if amount_selector["type"] == "css":
                                                                                                    amount_elem = driver.find_element(By.CSS_SELECTOR, amount_selector["value"])
                                                                                                elif amount_selector["type"] == "xpath":
                                                                                                    amount_elem = driver.find_element(By.XPATH, amount_selector["value"])
                                                                                                else:
                                                                                                    continue
                                                                                                
                                                                                                if amount_elem and amount_elem.is_displayed() and amount_elem.is_enabled():
                                                                                                    logger.info("Selecting first deposit amount")
                                                                                                    amount_elem.click()
                                                                                                    amount_selected = True
                                                                                                    break
                                                                                            except NoSuchElementException:
                                                                                                continue
                                                                                            except Exception as e:
                                                                                                logger.warning(f"Error selecting amount with selector {amount_selector}: {e}")
                                                                                                continue
                                                                                        
                                                                                        if amount_selected:
                                                                                            # Wait for amount selection to complete
                                                                                            time.sleep(2)
                                                                                            
                                                                                            # Click "Deposit Now" button
                                                                                            logger.info("Clicking 'Deposit Now' button...")
                                                                                            deposit_now_selectors = config.get("deposit_now_selectors", [])
                                                                                            
                                                                                            deposit_now_clicked = False
                                                                                            for deposit_selector in deposit_now_selectors:
                                                                                                try:
                                                                                                    if deposit_selector["type"] == "css":
                                                                                                        deposit_elem = driver.find_element(By.CSS_SELECTOR, deposit_selector["value"])
                                                                                                    elif deposit_selector["type"] == "xpath":
                                                                                                        deposit_elem = driver.find_element(By.XPATH, deposit_selector["value"])
                                                                                                    else:
                                                                                                        continue
                                                                                                    
                                                                                                    if deposit_elem and deposit_elem.is_displayed() and deposit_elem.is_enabled():
                                                                                                        logger.info("Clicking 'Deposit Now' button")
                                                                                                        deposit_elem.click()
                                                                                                        deposit_now_clicked = True
                                                                                                        break
                                                                                                except NoSuchElementException:
                                                                                                    continue
                                                                                                except Exception as e:
                                                                                                    logger.warning(f"Error clicking 'Deposit Now' with selector {deposit_selector}: {e}")
                                                                                                    continue
                                                                                            
                                                                                            if deposit_now_clicked:
                                                                                                logger.info("Successfully clicked 'Deposit Now' - waiting for popup to appear...")
                                                                                                # The script will now continue monitoring for the popup to appear again
                                                                                                break
                                                                                            else:
                                                                                                logger.warning("Could not click 'Deposit Now' button")
                                                                                        else:
                                                                                            logger.warning("Could not select deposit amount")
                                                                                    else:
                                                                                        logger.warning("USDT network selection page not detected")
                                                                                        
                                                                                except Exception as e:
                                                                                    logger.error(f"Error during network selection process: {e}")
                                                                                
                                                                                break
                                                                            else:
                                                                                logger.warning("Could not click 'Back' button")
                                                                                break
                                                                        else:
                                                                            continue
                                                                    except NoSuchElementException:
                                                                        continue
                                                                    except Exception as e:
                                                                        logger.warning(f"Error checking for success with selector {success_selector}: {e}")
                                                                        continue
                                                                
                                                                if not success_detected:
                                                                    logger.info("No success detected, continuing monitoring...")
                                                        else:
                                                            logger.warning("Could not find 'Completed Transaction' button")
                                                        
                                                        transaction_attempts += 1
                                                        logger.info(f"Transaction attempt {transaction_attempts} completed")
                                                        
                                                    except Exception as e:
                                                        logger.error(f"Error in transaction monitoring loop: {e}")
                                                        transaction_attempts += 1
                                                
                                                if transaction_attempts >= max_transaction_attempts:
                                                    logger.warning(f"Reached maximum transaction attempts ({max_transaction_attempts})")
                                                
                                                logger.info("Transaction monitoring loop completed")
                                            else:
                                                logger.warning("Could not find or click 'try again later' button")
                                                
                                        except Exception as e:
                                            logger.error(f"Error during try again later process: {e}")
                                        
                                        screenshot_count += 1
                                        if screenshot_count >= 5:
                                            with open('automation.log', 'w') as logf:
                                                logf.truncate(0)
                                        screenshot_sent = True
                                else:
                                    logger.error("Failed to send screenshot to Telegram")
                            last_popup_time = now
                            popup_present = True
                        else:
                            logger.info("Popup still present, throttling alarm/notification.")
                    else:
                        popup_present = False
                        screenshot_sent = False
                except Exception as e:
                    logger.error(f"Error processing window {handle}: {e}")
            
            # Wait 3 seconds before next submit button clicking cycle
            logger.info("Completed submit button cycle - waiting 3 seconds...")
            time.sleep(3)
    except Exception as e:
        logger.error(f"Popup detection failed: {e}")
    finally:
        # Don't quit Chrome - let it keep running
        logger.info("Script exiting - Chrome will continue running")
        
        # Clean up VNC processes
        if xvfb_proc:
            try:
                xvfb_proc.terminate()
                logger.info("Xvfb process terminated")
            except:
                pass
        if vnc_proc:
            try:
                vnc_proc.terminate()
                logger.info("VNC process terminated")
            except:
                pass

if __name__ == "__main__":
    main() 
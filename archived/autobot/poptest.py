# poptest.py - Clean Local Version
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
            # Use local Chromium and ChromeDriver
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--enable-unsafe-swiftshader")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            # Anti-detection flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
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
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            start_url = os.environ.get("START_URL", config.get("start_url"))
            if start_url:
                logger.info(f"Opening start URL: {start_url}")
                # driver.get(start_url) # Commented out to stop auto-launching
            # --- Add refresh logic ---
            refresh_interval = config.get('refresh_interval_seconds', 600)
            last_refresh_time = time.time()
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
        while True:
            # Refresh the page every 10 minutes
            if time.time() - last_refresh_time >= refresh_interval:
                logger.info("Refreshing the page after 10 minutes.")
                driver.refresh()
                last_refresh_time = time.time()
            window_handles = driver.window_handles
            n_windows = max(1, len(window_handles))
            window_check_period = config.get("window_check_period", 60)
            per_window_interval = window_check_period / n_windows
            for handle in window_handles:
                try:
                    driver.switch_to.window(handle)
                    selectors = config["popup_selectors"]
                    popup_elem = detect_popup(driver, selectors)
                    if popup_elem:
                        now = time.time()
                        throttle = config.get("throttle_seconds", config.get("throttle_minutes", 5)*60)
                        if not popup_present or (now - last_popup_time) >= throttle:
                            logger.info(f"Popup found in window {handle[:8]}")
                            
                            # Extract text from popup
                            extracted_text = extract_popup_text(popup_elem, config)
                            logger.info(f"Extracted text: {extracted_text['summary']}")
                            
                            play_alarm(config["alarm_sound"])
                            if not screenshot_sent:
                                # 1. Send screenshot
                                screenshot_png = driver.get_screenshot_as_png()
                                def send_telegram_photo_bytes(bot_token, chat_id, image_bytes):
                                    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
                                    files = {'photo': ('screenshot.png', image_bytes, 'image/png')}
                                    data = {'chat_id': chat_id}
                                    response = requests.post(url, data=data, files=files, timeout=30)
                                    if response.status_code == 200:
                                        logger.info("Telegram API call successful (in-memory screenshot)")
                                        return True
                                    else:
                                        logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                                        return False
                                if send_telegram_photo_bytes(config["bot_token"], config["chat_id"], screenshot_png):
                                    # 2. Send profile name
                                    profile_name = get_chrome_profile_name()
                                    send_telegram_message(config["bot_token"], config["chat_id"], f"Profile Name: {profile_name}")
                                    # 3. Send deposit address if found
                                    def extract_code_after_deposit_address_is(text: str) -> str:
                                        import re
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
                                    screenshot_count += 1
                                    if screenshot_count >= 5:
                                        with open('automation.log', 'w') as logf:
                                            logf.truncate(0)
                                    screenshot_sent = True
                            last_popup_time = now
                            popup_present = True
                        else:
                            logger.info("Popup still present, throttling alarm/notification.")
                    else:
                        popup_present = False
                        screenshot_sent = False
                except Exception as e:
                    logger.error(f"Error processing window {handle}: {e}")
                time.sleep(per_window_interval)
            time.sleep(config["check_interval"])
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

def get_chrome_profile_name(profile_dir: str = './automation_profile/Default/Preferences') -> str:
    try:
        with open(profile_dir, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
            return prefs.get('profile', {}).get('name', 'Unknown Profile')
    except Exception as e:
        logger.warning(f"Could not read Chrome profile name: {e}")
        return 'Unknown Profile'

if __name__ == "__main__":
    main() 
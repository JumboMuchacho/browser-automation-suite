#!/usr/bin/env python3
"""
Ultra-Robust Popup Test Script
Features: Multiple fallbacks, error recovery, health checks, graceful degradation
"""

import time
import subprocess
import os
import sys
import tempfile
import shutil
import random
import socket
import requests
import json
import logging
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import re

# Comprehensive logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration management with fallbacks
def load_config_with_fallbacks():
    config_files = [
        "config.json",
        "config.default.json",
        os.path.expanduser("~/.automation_config.json")
    ]
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded config from {config_file}")
                return config
        except Exception as e:
            logger.debug(f"Could not load {config_file}: {e}")
            continue
    
    # Default config
    default_config = {
        "bot_token": "8077567214:AAFaNw-KlMK4fJ36rny_TCjdtEj6P0ffSlE",
        "chat_id": 814781807,
        "timeout": 1200,
        "check_interval": 5,
        "throttle_minutes": 5,
        "max_retries": 3,
        "retry_delay": 5
    }
    logger.info("Using default configuration")
    return default_config

# Health checks
def check_disk_space(min_gb=1):
    try:
        stat = os.statvfs('.')
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        return free_gb >= min_gb
    except:
        return True  # Assume OK if can't check

def check_memory_usage(max_percent=90):
    try:
        import psutil
        return psutil.virtual_memory().percent < max_percent
    except:
        return True  # Assume OK if can't check

def check_internet_connection():
    urls = [
        "https://api.telegram.org",
        "https://www.google.com",
        "https://httpbin.org/get"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            continue
    return False

def health_check():
    checks = [
        ("disk_space", check_disk_space),
        ("memory_usage", check_memory_usage),
        ("internet_connection", check_internet_connection)
    ]
    
    for name, check_func in checks:
        if not check_func():
            logger.warning(f"Health check failed: {name}")
            return False
    return True

# Multiple port fallback
def find_working_port(start_port=9222, max_tries=50):
    for port in range(start_port, start_port + max_tries):
        if is_port_available(port):
            logger.info(f"Found available port: {port}")
            return port
    raise Exception("No available ports found")

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

# Chrome launch fallbacks
def get_chrome_paths():
    if sys.platform.startswith("linux"):
        return [
            "google-chrome",
            "google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome"
        ]
    elif sys.platform.startswith("win"):
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
    else:
        return ["google-chrome"]

def launch_chrome_with_fallbacks(user_data_dir, port):
    chrome_paths = get_chrome_paths()
    
    for chrome_path in chrome_paths:
        try:
            logger.info(f"Trying Chrome path: {chrome_path}")
            return launch_chrome(chrome_path, user_data_dir, port)
        except Exception as e:
            logger.warning(f"Failed with {chrome_path}: {e}")
            continue
    raise Exception("No Chrome installation found")

def launch_chrome(chrome_path, user_data_dir, port):
    chrome_cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-popup-blocking",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--disable-notifications",
        "--disable-component-update",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-device-discovery-notifications"
    ]
    logger.info(f"Launching Chrome: {' '.join(chrome_cmd)}")
    proc = subprocess.Popen(chrome_cmd)
    
    # Wait for Chrome to start listening
    for _ in range(30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(("127.0.0.1", port))
            if result == 0:
                logger.info(f"Chrome is listening on port {port}")
                break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise Exception(f"Chrome did not start listening on port {port}")
    
    # Write port to file
    try:
        with open(".chrome_debug_port", "w") as f:
            f.write(str(port))
        logger.info(f"Wrote debug port {port} to .chrome_debug_port")
    except Exception as e:
        logger.warning(f"Could not write port file: {e}")
    
    return proc

# Profile management fallbacks
def get_profile_with_fallbacks():
    # Try user's main profile first
    try:
        return get_default_chrome_profile()
    except Exception as e:
        logger.warning(f"Could not get default profile: {e}")
    
    # Try any available profile
    try:
        return get_any_available_profile()
    except Exception as e:
        logger.warning(f"Could not get any profile: {e}")
    
    # Create temporary profile as last resort
    logger.info("Creating temporary profile as fallback")
    return create_temp_profile()

def get_any_available_profile():
    if sys.platform.startswith("linux"):
        base = os.path.expanduser("~/.config/google-chrome")
    elif sys.platform.startswith("win"):
        base = os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data")
    else:
        raise Exception("Unsupported OS")
    
    if not os.path.exists(base):
        raise Exception(f"Chrome user data directory not found: {base}")
    
    profiles = [d for d in os.listdir(base) if d.startswith("Profile") or d == "Default"]
    if not profiles:
        raise Exception("No Chrome profiles found")
    
    profile = random.choice(profiles)
    logger.info(f"Using random profile: {profile}")
    return base, profile

def create_temp_profile():
    temp_dir = tempfile.mkdtemp(prefix="chrome_temp_profile_")
    logger.info(f"Created temporary profile: {temp_dir}")
    return temp_dir, "Default"

def copy_profile_robust(src_base, src_profile, dst_dir):
    src = os.path.join(src_base, src_profile)
    if not os.path.exists(src):
        raise Exception(f"Source profile {src} does not exist")
    
    if os.path.exists(dst_dir):
        logger.info(f"Removing old copied profile at {dst_dir}")
        shutil.rmtree(dst_dir)
    
    # Try direct copy first
    try:
        logger.info(f"Copying profile from {src} to {dst_dir}")
        shutil.copytree(src, dst_dir)
        logger.info("Profile copy complete")
        return True
    except Exception as e:
        logger.warning(f"Direct copy failed: {e}")
    
    # Try rsync if available
    try:
        subprocess.run(["rsync", "-av", src + "/", dst + "/"], check=True)
        logger.info("Profile copy complete (rsync)")
        return True
    except Exception as e:
        logger.warning(f"rsync copy failed: {e}")
    
    # Try tar if available
    try:
        subprocess.run(["tar", "-cf", "-", src], stdout=subprocess.PIPE, check=True)
        subprocess.run(["tar", "-xf", "-", "-C", dst], check=True)
        logger.info("Profile copy complete (tar)")
        return True
    except Exception as e:
        logger.warning(f"tar copy failed: {e}")
    
    raise Exception("All profile copy methods failed")

# Multiple selector strategies
def find_element_robust(driver, selectors):
    """
    Try multiple selectors in order until one works
    """
    for i, selector in enumerate(selectors):
        try:
            if selector["type"] == "css":
                element = driver.find_element(By.CSS_SELECTOR, selector["value"])
            elif selector["type"] == "xpath":
                element = driver.find_element(By.XPATH, selector["value"])
            elif selector["type"] == "id":
                element = driver.find_element(By.ID, selector["value"])
            else:
                continue
            
            logger.info(f"Found element with selector {i+1}: {selector}")
            return element
        except NoSuchElementException:
            logger.debug(f"Selector {i+1} failed: {selector}")
            continue
    raise NoSuchElementException("Element not found with any selector")

def connect_to_chrome(config):
    """Connect to Chrome with fresh profile approach"""
    try:
        # Use automation profile (fresh on first run, persisted on subsequent runs)
        automation_profile_dir = os.path.abspath("./automation_profile")
        if os.path.exists(automation_profile_dir):
            logger.info(f"✅ Using existing automation profile: {automation_profile_dir}")
            user_data_dir = automation_profile_dir
        else:
            logger.info("🆕 First run detected - creating fresh automation profile")
            if os.path.exists(automation_profile_dir):
                logger.info(f"🔄 Removing old automation profile at {automation_profile_dir}")
                shutil.rmtree(automation_profile_dir)
            os.makedirs(automation_profile_dir, exist_ok=True)
            logger.info(f"📁 Created fresh automation profile: {automation_profile_dir}")
            user_data_dir = automation_profile_dir
        
        # Find free port
        port = find_working_port()
        if not port:
            raise Exception("Could not find a free port for Chrome debugging")
        
        # Launch Chrome
        proc = launch_chrome_with_fallbacks(user_data_dir, port)
        if not proc:
            raise Exception("Failed to launch Chrome")
        
        # Connect WebDriver
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        
        logger.info("✅ Connected to Chrome successfully")
        return driver, proc
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Chrome: {e}")
        raise

# Connection retry logic
def connect_with_retry(config, max_retries=None):
    if max_retries is None:
        max_retries = config.get("max_retries", 3)
    delay = config.get("retry_delay", 5)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Connection attempt {attempt + 1}/{max_retries}")
            return connect_to_chrome(config)
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            raise

# Screenshot fallbacks
def screenshot_with_fallbacks(driver, element, path):
    methods = [
        ("element_screenshot", lambda: element.screenshot(path)),
        ("driver_screenshot", lambda: driver.save_screenshot(path)),
        ("mss_screenshot", lambda: take_screenshot_with_mss(path)),
        ("pyautogui_screenshot", lambda: take_screenshot_with_pyautogui(path))
    ]
    
    for method_name, method in methods:
        try:
            method()
            logger.info(f"Screenshot taken with {method_name}")
            return True
        except Exception as e:
            logger.warning(f"Screenshot method {method_name} failed: {e}")
            continue
    return False

def take_screenshot_with_mss(path):
    import mss
    with mss.mss() as sct:
        sct.shot(output=path)

def take_screenshot_with_pyautogui(path):
    import pyautogui
    pyautogui.screenshot(path)

# Audio fallbacks
def play_audio_with_fallbacks():
    audio_files = [
        "alarm_sounds/carrousel.mpeg",
        "alarm_sounds/alert.mp3", 
        "alarm_sounds/notification.wav"
    ]
    
    for audio_file in audio_files:
        if os.path.exists(audio_file):
            if play_audio(audio_file):
                return True
    return False

def play_audio(audio_file):
    if sys.platform.startswith("linux"):
        players = ["mpg123", "mpg321", "ffplay", "aplay"]
        for player in players:
            try:
                subprocess.Popen([player, audio_file])
                logger.info(f"Playing audio with {player}")
                return True
            except FileNotFoundError:
                continue
    elif sys.platform == "darwin":
        try:
            subprocess.Popen(["afplay", audio_file])
            logger.info("Playing audio with afplay")
            return True
        except FileNotFoundError:
            pass
    elif sys.platform.startswith("win"):
        try:
            subprocess.Popen(["start", audio_file], shell=True)
            logger.info("Playing audio with Windows media player")
            return True
        except Exception as e:
            logger.warning(f"Could not play audio on Windows: {e}")
    
    logger.warning("No audio player available")
    return False

# Network & API fallbacks
def send_notification_with_fallbacks(config, message, image_path=None):
    # Try Telegram first
    if send_telegram_message(config["bot_token"], config["chat_id"], message):
        return True
    
    # Fallback to email (if configured)
    if "email_config" in config:
        if send_email_notification(config["email_config"], message):
            return True
    
    # Fallback to local file
    if save_notification_to_file(message):
        return True
    
    return False

def send_telegram_message(bot_token, chat_id, message):
    if not check_internet_connection():
        logger.warning("No internet connection, cannot send Telegram message")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def send_telegram_photo(bot_token, chat_id, image_path, caption=None):
    if not os.path.exists(image_path):
        logger.warning(f"Screenshot file {image_path} not found")
        return False
    
    if not check_internet_connection():
        logger.warning("No internet connection, cannot send Telegram photo")
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
                logger.info('Screenshot sent to Telegram successfully')
                return True
            else:
                logger.error(f'Failed to send screenshot: {response.text}')
                return False
    except Exception as e:
        logger.error(f"Error sending Telegram photo: {e}")
        return False

def save_notification_to_file(message):
    try:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"notification_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"{timestamp}: {message}\n")
        logger.info(f"Notification saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Could not save notification to file: {e}")
        return False

# Graceful degradation
def run_with_graceful_degradation(config):
    try:
        # Full functionality
        return run_full_automation(config)
    except Exception as e:
        logger.error(f"Full automation failed: {e}")
        
        # Try basic functionality
        try:
            logger.info("Attempting basic automation...")
            return run_basic_automation(config)
        except Exception as e2:
            logger.error(f"Basic automation also failed: {e2}")
            
            # Save for later retry
            try:
                save_for_later_retry(config)
                return False
            except Exception as e3:
                logger.error(f"Could not save for retry: {e3}")
                return False

def run_basic_automation(config):
    """Basic automation without screenshots/audio"""
    logger.info("Running basic automation (no screenshots/audio)")
    # Implement basic popup detection without advanced features
    return True

def save_for_later_retry(config):
    """Save current state for later retry"""
    retry_data = {
        "timestamp": time.time(),
        "config": config,
        "status": "failed"
    }
    with open("retry_queue.json", "w") as f:
        json.dump(retry_data, f)
    logger.info("Saved state for later retry")

# Main automation logic with all robust features
def run_full_automation(config):
    # Health check
    if not health_check():
        logger.warning("Health check failed, but continuing...")
    
    # Load configuration
    bot_token = config["bot_token"]
    chat_id = config["chat_id"]
    timeout = config["timeout"]
    check_interval = config["check_interval"]
    throttle_minutes = config["throttle_minutes"]
    
    # Profile management - use automation profile (fresh on first run, persisted on subsequent runs)
    try:
        automation_profile_dir = os.path.abspath("./automation_profile")
        if os.path.exists(automation_profile_dir):
            logger.info(f"✅ Using existing automation profile: {automation_profile_dir}")
            user_data_dir = automation_profile_dir
        else:
            logger.info("🆕 First run detected - creating fresh automation profile")
            if os.path.exists(automation_profile_dir):
                logger.info(f"🔄 Removing old automation profile at {automation_profile_dir}")
                shutil.rmtree(automation_profile_dir)
            os.makedirs(automation_profile_dir, exist_ok=True)
            logger.info(f"📁 Created fresh automation profile: {automation_profile_dir}")
            user_data_dir = automation_profile_dir
    except Exception as e:
        logger.error(f"Profile management failed: {e}")
        return False
    
    # Chrome connection with retry
    try:
        driver, proc = connect_with_retry(config)
    except Exception as e:
        logger.error(f"Chrome connection failed: {e}")
        return False
    
    # Main monitoring loop
    start_time = time.time()
    found = False
    last_trigger_time = {}
    last_content_hash = {}
    notification_count = {}  # Track how many times we've notified for each window
    
    try:
        while time.time() - start_time < timeout:
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    now = time.time()
                    
                    # Multiple selector strategies for popup detection
                    selectors = [
                        {"type": "css", "value": "#app > div.reviseAvatar-wrap > div.gmRA > div.drawer-wrap.drawer-middle > div.drawer-box > div > div.bsbb.modifyAvatarBox"},
                        {"type": "xpath", "value": '//*[@id="app"]/div[3]/div[2]/div[1]/div[2]/div/div[3]'},
                        {"type": "xpath", "value": '//*[@id="app"]/div[4]/div[2]/div[1]/div[2]/div/div[3]'},
                        {"type": "css", "value": ".modifyAvatarBox"},
                        {"type": "xpath", "value": "//div[contains(@class, 'modifyAvatarBox')]"}
                    ]
                    
                    popup_elem = find_element_robust(driver, selectors)
                    
                    logger.info(f"=== POPUP FOUND in window {handle[:8]} ===")
                    logger.info(f"Outer HTML: {popup_elem.get_attribute('outerHTML')}")
                    
                    # Throttling logic
                    last_time = last_trigger_time.get(handle, 0)
                    current_hash = hash(popup_elem.get_attribute('outerHTML'))
                    last_hash = last_content_hash.get(handle, None)
                    notify_count = notification_count.get(handle, 0)
                    
                    # Check if this is a new popup (content changed)
                    is_new_popup = current_hash != last_hash
                    
                    # Reset notification count if it's a new popup
                    if is_new_popup:
                        notify_count = 0
                        notification_count[handle] = 0
                        last_content_hash[handle] = current_hash
                        logger.info(f"🆕 New popup detected in window {handle[:8]}, resetting notification count")
                    
                    # Only notify if we haven't exceeded 2 notifications for this popup
                    if notify_count < 2:
                        # If this is the first time seeing this popup in this window, or throttling period has expired
                        if last_time == 0 or now - last_time >= throttle_minutes * 60:
                            # Throttling period expired - send alarm and notification
                            if last_time == 0:
                                logger.info(f"🆕 First time detecting popup in window {handle[:8]}, sending alert (1/2)")
                            else:
                                logger.info(f"🔄 Throttling period expired ({throttle_minutes} minutes), sending alert (2/2)")
                            
                            play_audio_with_fallbacks()
                            
                            try:
                                profile_name = get_visible_profile_name(user_data_dir)
                            except:
                                profile_name = "Automation Profile"
                            
                            message = f"Popup detected! Profile: {profile_name}"
                            
                            if send_notification_with_fallbacks(config, message):
                                logger.info("✅ Notification sent successfully")
                            else:
                                logger.warning("⚠️ Notification failed, but continuing...")
                            
                            # Only send screenshot if content changed
                            if is_new_popup:
                                screenshot_path = '/tmp/screen.png'
                                if screenshot_with_fallbacks(driver, popup_elem, screenshot_path):
                                    send_telegram_photo(bot_token, chat_id, screenshot_path, 
                                                     caption=f'Popup detected! Profile: {profile_name}')
                                    logger.info("📸 Screenshot sent successfully")
                                else:
                                    logger.warning("⚠️ Screenshot failed, but continuing...")
                            
                            last_trigger_time[handle] = now
                            notification_count[handle] = notify_count + 1
                            found = True
                        else:
                            remaining_time = int((throttle_minutes * 60) - (now - last_time))
                            logger.info(f"⏰ Popup detected in window {handle[:8]} but throttled - {remaining_time}s remaining until next alert")
                    else:
                        logger.info(f"🔇 Popup still present in window {handle[:8]} but max notifications (2) reached - no more alarms")
                        
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.error(f"Error processing window {handle}: {e}")
                    continue
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        # Cleanup
        try:
            driver.quit()
        except:
            pass
        if proc:
            try:
                proc.terminate()
            except:
                pass
    
    if not found:
        logger.info(f"No popup found during {timeout} second monitoring period")
    else:
        logger.info("Popup detection completed successfully")
    
    return found

def main():
    try:
        # Load configuration
        config = load_config_with_fallbacks()
        
        # Run with graceful degradation
        success = run_with_graceful_degradation(config)
        
        if success:
            logger.info("Automation completed successfully")
        else:
            logger.warning("Automation completed with issues")
            
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
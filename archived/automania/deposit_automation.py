#!/usr/bin/env python3
"""
Robust Deposit Automation Script
Enhanced with configuration management, health checks, error recovery, and graceful degradation.
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
import signal
import atexit
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
import re

# Ensure running in venv
if os.environ.get('VIRTUAL_ENV') is None:
    print("❌ Not running inside a virtual environment! Please activate your venv with:")
    print("   source .venv/bin/activate")
    sys.exit(1)

# Configuration Management
class Config:
    """Centralized configuration management with fallbacks"""
    
    DEFAULT_CONFIG = {
        "chrome": {
            "connection_timeout": 30,
            "page_load_timeout": 30,
            "implicit_wait": 10,
            "max_retries": 3,
            "retry_delay": 2
        },
        "deposit": {
            "default_amount": "50",
            "default_network": "bnb",
            "amount_input_delay": 1,
            "confirmation_delay": 2
        },
        "telegram": {
            "enabled": True,
            "timeout": 10,
            "max_retries": 3
        },
        "audio": {
            "enabled": True,
            "volume": 0.8
        },
        "screenshots": {
            "enabled": True,
            "format": "png",
            "quality": 85
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "file": "deposit_automation.log"
        },
        "fallbacks": {
            "enable_profile_copy": True,
            "enable_port_detection": True,
            "enable_audio_fallback": True,
            "enable_screenshot_fallback": True
        }
    }
    
    def __init__(self):
        self.config_file = Path("deposit_config.json")
        self.config = self.load_config()
        self.setup_logging()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration with fallbacks"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    config = self.deep_merge(self.DEFAULT_CONFIG, user_config)
                    print(f"[INFO] Loaded configuration from {self.config_file}")
                    return config
            else:
                with open(self.config_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=2)
                print(f"[INFO] Created default configuration at {self.config_file}")
                return self.DEFAULT_CONFIG
        except Exception as e:
            print(f"[WARNING] Failed to load config, using defaults: {e}")
            return self.DEFAULT_CONFIG
    
    def deep_merge(self, default: Dict, user: Dict) -> Dict:
        """Deep merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config["logging"]
        log_level = getattr(logging, log_config["level"])
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format=log_config["format"],
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / log_config["file"])
            ]
        )

# Global configuration
config = Config()
logger = logging.getLogger(__name__)

# Health Check System
class HealthChecker:
    """System health monitoring and recovery"""
    
    def __init__(self):
        self.health_checks = []
        self.last_check_time = 0
        self.check_interval = 60  # Check every minute
    
    def register_health_check(self, check_func):
        """Register a health check function"""
        self.health_checks.append(check_func)
    
    def run_health_checks(self) -> bool:
        """Run all registered health checks"""
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return True  # Skip if too soon
        
        self.last_check_time = current_time
        logger.info("🔍 Running health checks...")
        
        all_passed = True
        for check_func in self.health_checks:
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                all_passed = False
        
        if all_passed:
            logger.debug("✅ All health checks passed")
        else:
            logger.warning("⚠️ Some health checks failed")
        
        return all_passed
    
    def check_internet_connection(self) -> bool:
        """Check internet connectivity"""
        try:
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except Exception:
            logger.warning("⚠️ Internet connection check failed")
            return False
    
    def check_telegram_api(self, bot_token: str) -> bool:
        """Check Telegram API connectivity"""
        if not config.config["telegram"]["enabled"]:
            return True
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=config.config["telegram"]["timeout"])
            return response.status_code == 200
        except Exception:
            logger.warning("⚠️ Telegram API check failed")
            return False

# Cross-platform utilities
class PlatformUtils:
    """Cross-platform utility functions"""
    
    @staticmethod
    def get_chrome_path() -> Optional[str]:
        """Get Chrome executable path for current platform"""
        if sys.platform.startswith("linux"):
            paths = ["google-chrome", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
            for path in paths:
                try:
                    subprocess.run([path, "--version"], capture_output=True, check=True)
                    return path
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            return None
        elif sys.platform.startswith("win"):
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return None
        else:
            return None
    
    @staticmethod
    def kill_chrome_processes():
        """Kill existing Chrome processes"""
        logger.info("🔄 Killing existing Chrome processes...")
        try:
            if sys.platform.startswith("linux"):
                subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
                subprocess.run(["killall", "chrome"], capture_output=True)
            elif sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            logger.info("✅ Chrome processes killed")
        except Exception as e:
            logger.warning(f"⚠️ Failed to kill Chrome processes: {e}")
    
    @staticmethod
    def play_alarm():
        """Cross-platform audio playback with fallbacks"""
        if not config.config["audio"]["enabled"]:
            return
        
        audio_file = "alarm_sounds/carrousel.mpeg"
        if not os.path.exists(audio_file):
            logger.warning(f"⚠️ Audio file not found: {audio_file}")
            return
        
        try:
            if sys.platform.startswith("linux"):
                players = ["mpg123", "mpg321", "ffplay", "aplay"]
                for player in players:
                    try:
                        subprocess.Popen([player, audio_file])
                        logger.info(f"🔊 Playing alarm with {player}")
                        break
                    except FileNotFoundError:
                        continue
                else:
                    logger.warning("⚠️ No audio player found. Install mpg123: sudo apt-get install mpg123")
            elif sys.platform == "darwin":
                subprocess.Popen(["afplay", audio_file])
                logger.info("🔊 Playing alarm with afplay")
            elif sys.platform.startswith("win"):
                subprocess.Popen(["start", audio_file], shell=True)
                logger.info("🔊 Playing alarm with Windows media player")
        except Exception as e:
            logger.error(f"❌ Failed to play alarm: {e}")

# Enhanced utility functions
class Utils:
    """Enhanced utility functions with error handling"""
    
    @staticmethod
    def find_free_port(start_port: int = 9222, max_tries: int = 20) -> Optional[int]:
        """Find a free port for remote debugging"""
        for i in range(max_tries):
            port = start_port + i
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    logger.info(f"✅ Found free port: {port}")
                    return port
            except OSError:
                continue
        
        logger.error(f"❌ Could not find a free port after {max_tries} attempts")
        return None
    
    @staticmethod
    def find_existing_debug_chrome() -> Tuple[Optional[int], Optional[str]]:
        """Find existing Chrome with remote debugging"""
        try:
            if sys.platform.startswith("win"):
                cmd = 'wmic process where "name like \'%chrome.exe%\'" get CommandLine'
            else:
                cmd = "ps aux | grep '[c]hrome'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            for line in result.stdout.splitlines():
                if '--remote-debugging-port=' in line:
                    port_match = re.search(r'--remote-debugging-port=(\d+)', line)
                    port = int(port_match.group(1)) if port_match else 9222
                    
                    udd_match = re.search(r'--user-data-dir=(["\']?)([^ "\']+)', line)
                    user_data_dir = udd_match.group(2) if udd_match else None
                    
                    logger.info(f"✅ Found existing Chrome debug session on port {port}")
                    return port, user_data_dir
        except Exception as e:
            logger.error(f"❌ Error finding existing Chrome: {e}")
        
        return None, None
    
    @staticmethod
    def get_default_chrome_profile() -> Tuple[Optional[str], Optional[str]]:
        """Get default Chrome profile directory"""
        try:
            if sys.platform.startswith("linux"):
                base = os.path.expanduser("~/.config/google-chrome")
                candidates = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
            elif sys.platform.startswith("win"):
                base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                candidates = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
            else:
                logger.error("Unsupported OS for Chrome profile detection")
                return None, None
            
            for candidate in candidates:
                path = os.path.join(base, candidate)
                if os.path.exists(path):
                    logger.info(f"✅ Found Chrome profile: {path}")
                    return base, candidate
            
            logger.error("❌ Could not find a Chrome profile directory")
            return None, None
        except Exception as e:
            logger.error(f"❌ Error finding Chrome profile: {e}")
            return None, None
    
    @staticmethod
    def copy_chrome_profile(src_base: str, src_profile: str, dst_dir: str) -> bool:
        """Copy Chrome profile with error handling"""
        try:
            src = os.path.join(src_base, src_profile)
            if not os.path.exists(src):
                logger.error(f"❌ Source Chrome profile {src} does not exist")
                return False
            
            if os.path.exists(dst_dir):
                logger.info(f"🔄 Removing old copied profile at {dst_dir}")
                shutil.rmtree(dst_dir)
            
            logger.info(f"📁 Copying Chrome profile from {src} to {dst_dir}...")
            shutil.copytree(src, dst_dir)
            logger.info("✅ Profile copy complete")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to copy Chrome profile: {e}")
            return False
    
    @staticmethod
    def get_visible_profile_name(user_data_dir: str) -> str:
        """Get visible profile name from Local State"""
        try:
            local_state_path = os.path.join(user_data_dir, 'Local State')
            if not os.path.exists(local_state_path):
                logger.warning(f"⚠️ Local State file not found at {local_state_path}")
                return os.path.basename(user_data_dir)
            
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            profiles = local_state.get('profile', {}).get('info_cache', {})
            
            # Find most recently used profile
            most_recent = None
            most_recent_time = 0
            for profile_dir, info in profiles.items():
                ts = info.get('last_used', 0)
                if ts > most_recent_time:
                    most_recent = info.get('name', profile_dir)
                    most_recent_time = ts
            
            if most_recent:
                return most_recent
            
            # Fallback: return any profile name
            for profile_dir, info in profiles.items():
                return info.get('name', profile_dir)
            
            return os.path.basename(user_data_dir)
        except Exception as e:
            logger.error(f"❌ Error getting profile name: {e}")
            return os.path.basename(user_data_dir)

# Enhanced Chrome management
class ChromeManager:
    """Enhanced Chrome process management"""
    
    def __init__(self):
        self.process = None
        self.port = None
        self.user_data_dir = None
    
    def launch_chrome_debug(self, user_data_dir: str, port: int) -> bool:
        """Launch Chrome with remote debugging"""
        try:
            chrome_exe = PlatformUtils.get_chrome_path()
            if not chrome_exe:
                logger.error("❌ Chrome executable not found")
                return False
            
            chrome_cmd = [
                chrome_exe,
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
            
            logger.info(f"🚀 Launching Chrome: {' '.join(chrome_cmd)}")
            self.process = subprocess.Popen(chrome_cmd)
            self.port = port
            self.user_data_dir = user_data_dir
            
            # Wait for Chrome to start listening
            if self.wait_for_chrome_startup():
                self.write_port_to_file()
                return True
            else:
                logger.error("❌ Chrome failed to start properly")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to launch Chrome: {e}")
            return False
    
    def wait_for_chrome_startup(self) -> bool:
        """Wait for Chrome to start listening on the debug port"""
        timeout = config.config["chrome"]["connection_timeout"]
        logger.info(f"⏳ Waiting for Chrome to start (timeout: {timeout}s)...")
        
        for _ in range(timeout):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(("127.0.0.1", self.port))
                    if result == 0:
                        logger.info(f"✅ Chrome is listening on port {self.port}")
                        return True
            except Exception:
                pass
            time.sleep(1)
        
        logger.error(f"❌ Chrome did not start listening on port {self.port} within {timeout} seconds")
        return False
    
    def write_port_to_file(self):
        """Write debug port to file"""
        try:
            with open(".chrome_debug_port", "w") as f:
                f.write(str(self.port))
            logger.info(f"📝 Wrote debug port {self.port} to .chrome_debug_port")
        except Exception as e:
            logger.error(f"❌ Failed to write port to file: {e}")
    
    def cleanup(self):
        """Cleanup Chrome process"""
        if self.process:
            try:
                self.process.terminate()
                logger.info("✅ Chrome process terminated")
            except Exception as e:
                logger.warning(f"⚠️ Failed to terminate Chrome process: {e}")

# Enhanced screenshot and notification utilities
class NotificationUtils:
    """Enhanced notification utilities with fallbacks"""
    
    @staticmethod
    def try_screenshot(driver, element, path: str) -> bool:
        """Take screenshot with multiple fallback methods"""
        if not config.config["screenshots"]["enabled"]:
            return False
        
        try:
            # Method 1: Selenium screenshot
            if element:
                element.screenshot(path)
                logger.info(f"📸 Screenshot taken with Selenium: {path}")
                return True
        except Exception as e:
            logger.debug(f"Selenium screenshot failed: {e}")
        
        try:
            # Method 2: Full page screenshot
            driver.save_screenshot(path)
            logger.info(f"📸 Screenshot taken (full page): {path}")
            return True
        except Exception as e:
            logger.debug(f"Full page screenshot failed: {e}")
        
        # Method 3: System screenshot (fallback)
        if config.config["fallbacks"]["enable_screenshot_fallback"]:
            try:
                import mss
                with mss.mss() as sct:
                    monitor = sct.monitors[1]  # Primary monitor
                    screenshot = sct.grab(monitor)
                    mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)
                logger.info(f"📸 Screenshot taken with mss: {path}")
                return True
            except Exception as e:
                logger.debug(f"mss screenshot failed: {e}")
        
        logger.error(f"❌ All screenshot methods failed for {path}")
        return False
    
    @staticmethod
    def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
        """Send Telegram message with retry logic"""
        if not config.config["telegram"]["enabled"]:
            return False
        
        for attempt in range(config.config["telegram"]["max_retries"]):
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {"chat_id": chat_id, "text": message}
                response = requests.post(url, data=data, timeout=config.config["telegram"]["timeout"])
                
                if response.status_code == 200:
                    logger.info("✅ Telegram message sent")
                    return True
                else:
                    logger.warning(f"⚠️ Telegram API error: {response.text}")
            except Exception as e:
                logger.warning(f"⚠️ Telegram message attempt {attempt + 1} failed: {e}")
            
            if attempt < config.config["telegram"]["max_retries"] - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error("❌ Failed to send Telegram message after all retries")
        return False
    
    @staticmethod
    def send_telegram_photo(bot_token: str, chat_id: str, image_path: str, caption: str = None) -> bool:
        """Send Telegram photo with retry logic"""
        if not config.config["telegram"]["enabled"]:
            return False
        
        if not os.path.exists(image_path):
            logger.error(f"❌ Image file not found: {image_path}")
            return False
        
        for attempt in range(config.config["telegram"]["max_retries"]):
            try:
                url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
                with open(image_path, 'rb') as photo:
                    data = {'chat_id': chat_id}
                    if caption:
                        data['caption'] = caption
                    files = {'photo': photo}
                    response = requests.post(url, data=data, files=files, 
                                          timeout=config.config["telegram"]["timeout"])
                
                if response.status_code == 200:
                    logger.info('✅ Screenshot sent to Telegram')
                    return True
                else:
                    logger.warning(f"⚠️ Telegram API error: {response.text}")
            except Exception as e:
                logger.warning(f"⚠️ Telegram photo attempt {attempt + 1} failed: {e}")
            
            if attempt < config.config["telegram"]["max_retries"] - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error("❌ Failed to send Telegram photo after all retries")
        return False

# Enhanced Deposit Automation
class DepositAutomation:
    """Enhanced deposit automation with robust error handling"""
    
    def __init__(self):
        self.driver = None
        self.chrome_manager = ChromeManager()
        self.health_checker = HealthChecker()
        self.profile_name = None
        
        # Register health checks
        self.health_checker.register_health_check(self.health_checker.check_internet_connection)
        
        # Setup cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ WebDriver closed")
            except Exception as e:
                logger.warning(f"⚠️ Failed to close WebDriver: {e}")
        
        self.chrome_manager.cleanup()
    
    def connect_to_chrome(self) -> bool:
        """Connect to Chrome with enhanced error handling"""
        try:
            # Try to find existing Chrome debug session
            port, user_data_dir = Utils.find_existing_debug_chrome()
            
            if not port:
                logger.info("🔍 No existing Chrome debug session found, launching new one...")
                
                # Kill existing Chrome processes
                PlatformUtils.kill_chrome_processes()
                
                # Find free port
                port = Utils.find_free_port()
                if not port:
                    logger.error("❌ Could not find a free port")
                    return False
                
                # Use automation profile (fresh on first run, persisted on subsequent runs)
                automation_profile_dir = "automation_profile"
                if os.path.exists(automation_profile_dir):
                    logger.info(f"✅ Using existing automation profile: {automation_profile_dir}")
                    user_data_dir = automation_profile_dir
                    self.profile_name = Utils.get_visible_profile_name(automation_profile_dir)
                else:
                    logger.info("🆕 First run detected - creating fresh automation profile")
                    os.makedirs(automation_profile_dir, exist_ok=True)
                    user_data_dir = automation_profile_dir
                    self.profile_name = "Automation Profile"
                    logger.info(f"📁 Created fresh automation profile: {automation_profile_dir}")
                
                # Launch Chrome
                if not self.chrome_manager.launch_chrome_debug(user_data_dir, port):
                    logger.error("❌ Failed to launch Chrome")
                    return False
            else:
                logger.info(f"✅ Found existing Chrome debug session on port {port}")
                if user_data_dir:
                    self.profile_name = Utils.get_visible_profile_name(user_data_dir)
            
            # Connect WebDriver
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(config.config["chrome"]["implicit_wait"])
            self.driver.set_page_load_timeout(config.config["chrome"]["page_load_timeout"])
            
            logger.info("✅ Connected to Chrome successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Chrome: {e}")
            return False
    
    def navigate_to_target_site(self) -> bool:
        """Navigate to target site with retry logic"""
        target_url = "https://example.com"  # Replace with actual URL
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"🌐 Navigating to {target_url} (attempt {attempt + 1})")
                self.driver.get(target_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, config.config["chrome"]["page_load_timeout"]).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                logger.info("✅ Successfully navigated to target site")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Navigation attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error("❌ Failed to navigate to target site after all retries")
        return False
    
    def click_profile_icon(self) -> bool:
        """Click profile icon with retry logic"""
        selector = ".profile-icon"  # Replace with actual selector
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"🖱️ Clicking profile icon (attempt {attempt + 1})")
                
                wait = WebDriverWait(self.driver, config.config["chrome"]["implicit_wait"])
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                element.click()
                
                logger.info("✅ Profile icon clicked successfully")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Profile icon click attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error("❌ Failed to click profile icon after all retries")
        return False
    
    def click_deposit_now(self) -> bool:
        """Click deposit now button with retry logic"""
        selector = ".deposit-now-btn"  # Replace with actual selector
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"🖱️ Clicking deposit now button (attempt {attempt + 1})")
                
                wait = WebDriverWait(self.driver, config.config["chrome"]["implicit_wait"])
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                element.click()
                
                logger.info("✅ Deposit now button clicked successfully")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Deposit now click attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error("❌ Failed to click deposit now button after all retries")
        return False
    
    def select_network(self, network_type: str = "bnb") -> bool:
        """Select network with retry logic"""
        network_selector = f".network-{network_type}"  # Replace with actual selector
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"🌐 Selecting network {network_type} (attempt {attempt + 1})")
                
                wait = WebDriverWait(self.driver, config.config["chrome"]["implicit_wait"])
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, network_selector)))
                element.click()
                
                logger.info(f"✅ Network {network_type} selected successfully")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Network selection attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error(f"❌ Failed to select network {network_type} after all retries")
        return False
    
    def enter_deposit_amount(self, amount: str = "50") -> bool:
        """Enter deposit amount with retry logic"""
        amount_selector = ".amount-input"  # Replace with actual selector
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"💰 Entering deposit amount {amount} (attempt {attempt + 1})")
                
                wait = WebDriverWait(self.driver, config.config["chrome"]["implicit_wait"])
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, amount_selector)))
                
                # Clear and enter amount
                element.clear()
                element.send_keys(amount)
                
                # Wait for input delay
                time.sleep(config.config["deposit"]["amount_input_delay"])
                
                logger.info(f"✅ Deposit amount {amount} entered successfully")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Amount entry attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error(f"❌ Failed to enter deposit amount {amount} after all retries")
        return False
    
    def confirm_deposit(self) -> bool:
        """Confirm deposit with retry logic"""
        confirm_selector = ".confirm-deposit-btn"  # Replace with actual selector
        
        for attempt in range(config.config["chrome"]["max_retries"]):
            try:
                logger.info(f"✅ Confirming deposit (attempt {attempt + 1})")
                
                wait = WebDriverWait(self.driver, config.config["chrome"]["implicit_wait"])
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_selector)))
                element.click()
                
                # Wait for confirmation delay
                time.sleep(config.config["deposit"]["confirmation_delay"])
                
                logger.info("✅ Deposit confirmed successfully")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Deposit confirmation attempt {attempt + 1} failed: {e}")
                if attempt < config.config["chrome"]["max_retries"] - 1:
                    time.sleep(config.config["chrome"]["retry_delay"])
        
        logger.error("❌ Failed to confirm deposit after all retries")
        return False
    
    def run_deposit_workflow(self, network_type: str = "bnb", amount: str = "50") -> bool:
        """Run complete deposit workflow with error handling"""
        logger.info(f"🚀 Starting deposit workflow: {amount} {network_type}")
        
        try:
            # Run health checks
            if not self.health_checker.run_health_checks():
                logger.warning("⚠️ Some health checks failed, but continuing...")
            
            # Connect to Chrome
            if not self.connect_to_chrome():
                logger.error("❌ Failed to connect to Chrome")
                return False
            
            # Navigate to target site
            if not self.navigate_to_target_site():
                logger.error("❌ Failed to navigate to target site")
                return False
            
            # Click profile icon
            if not self.click_profile_icon():
                logger.error("❌ Failed to click profile icon")
                return False
            
            # Click deposit now
            if not self.click_deposit_now():
                logger.error("❌ Failed to click deposit now")
                return False
            
            # Select network
            if not self.select_network(network_type):
                logger.error(f"❌ Failed to select network {network_type}")
                return False
            
            # Enter amount
            if not self.enter_deposit_amount(amount):
                logger.error(f"❌ Failed to enter amount {amount}")
                return False
            
            # Confirm deposit
            if not self.confirm_deposit():
                logger.error("❌ Failed to confirm deposit")
                return False
            
            logger.info("🎉 Deposit workflow completed successfully!")
            
            # Play alarm and send notifications
            PlatformUtils.play_alarm()
            
            # Send Telegram notification
            if config.config["telegram"]["enabled"]:
                message = f"✅ Deposit automation completed!\nAmount: {amount} {network_type}\nProfile: {self.profile_name}"
                NotificationUtils.send_telegram_message("YOUR_BOT_TOKEN", "YOUR_CHAT_ID", message)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Deposit workflow failed: {e}")
            
            # Send error notification
            if config.config["telegram"]["enabled"]:
                error_message = f"❌ Deposit automation failed!\nError: {str(e)}\nProfile: {self.profile_name}"
                NotificationUtils.send_telegram_message("YOUR_BOT_TOKEN", "YOUR_CHAT_ID", error_message)
            
            return False

def main():
    """Main entry point"""
    try:
        automation = DepositAutomation()
        
        # Get parameters from command line or use defaults
        network_type = sys.argv[1] if len(sys.argv) > 1 else config.config["deposit"]["default_network"]
        amount = sys.argv[2] if len(sys.argv) > 2 else config.config["deposit"]["default_amount"]
        
        success = automation.run_deposit_workflow(network_type, amount)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
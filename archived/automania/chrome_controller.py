#!/usr/bin/env python3
"""
Chrome Controller - Connect to existing Chrome windows with real profiles
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import os
import sys
import subprocess
import pyautogui
import requests

if os.environ.get('VIRTUAL_ENV') is None:
    print("❌ Not running inside a virtual environment! Please activate your venv with:")
    print("   source .venv/bin/activate")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_deposit_address(text):
    lines = text.strip().split('\n')
    for i, line in enumerate(lines):
        if 'and the deposit address is' in line:
            if i+1 < len(lines):
                return lines[i+1].strip()
    return None

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Telegram message sent.")
        else:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def send_telegram_photo(bot_token, chat_id, image_path, caption=None):
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    with open(image_path, 'rb') as photo:
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        files = {'photo': photo}
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            print('Screenshot sent to Telegram.')
        else:
            print(f'Failed to send screenshot: {response.text}')

def get_debug_port():
    try:
        with open(".chrome_debug_port", "r") as f:
            port = int(f.read().strip())
            print(f"[INFO] Using Chrome debug port: {port}")
            return port
    except Exception:
        print("[INFO] Using default Chrome debug port: 9222")
        return 9222

class ChromeController:
    """Controller for existing Chrome windows with real profiles"""
    
    def __init__(self):
        self.driver = None
        self.windows = []
        self.debug_port = get_debug_port()
        
    def connect_to_existing_windows(self):
        """Connect to existing Chrome windows with real profile"""
        try:
            logger.info("🔍 Connecting to existing Chrome windows...")
            
            # Create Chrome options to connect to existing session
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            
            # Connect to existing Chrome
            try:
                self.driver = webdriver.Chrome(options=options)
                logger.info("✅ Connected to existing Chrome session")
                
                # Get all windows
                self.windows = self.driver.window_handles
                logger.info(f"📋 Found {len(self.windows)} windows")
                
                for i, window in enumerate(self.windows):
                    logger.info(f"  Window {i+1}: {window}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to existing Chrome: {e}")
                logger.info("💡 Make sure Chrome is running with remote debugging enabled")
                logger.info("   Start Chrome with: google-chrome --remote-debugging-port=9222 --user-data-dir=/home/jbee/.config/google-chrome")
                self.driver = None
                self.windows = []
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to windows: {e}")
            self.driver = None
            self.windows = []
            return False
    
    def switch_to_window(self, window_index: int):
        """Switch to a specific window"""
        if self.driver is None:
            logger.error("❌ Driver not initialized.")
            return False
        if 0 <= window_index < len(self.windows):
            self.driver.switch_to.window(self.windows[window_index])
            logger.info(f"🔄 Switched to Window {window_index + 1}")
            return True
        else:
            logger.error(f"❌ Invalid window index: {window_index}")
            return False
    
    def click_element(self, selector: str, window_index: int = 0, selector_type: str = "css"):
        """Click an element in a specific window"""
        if self.driver is None:
            logger.error("❌ Driver not initialized.")
            return False
        try:
            if not self.switch_to_window(window_index):
                return False
            
            wait = WebDriverWait(self.driver, 10)
            
            if selector_type.lower() == "xpath":
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            else:
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            
            element.click()
            logger.info(f"✅ Clicked element: {selector}")
            return True
            
        except TimeoutException:
            logger.error(f"❌ Element not found: {selector}")
            return False
        except Exception as e:
            logger.error(f"❌ Error clicking element: {e}")
            return False
    
    def monitor_for_popup(self, timeout: int = 30):
        """Monitor for popup windows and extract text in all windows"""
        if self.driver is None:
            logger.error("❌ Driver not initialized.")
            return
        try:
            logger.info(f"🔍 Monitoring all windows for popups...")
            initial_windows = len(self.driver.window_handles)
            start_time = time.time()
            found = False
            while time.time() - start_time < timeout:
                for window_index in range(len(self.windows)):
                    try:
                        self.switch_to_window(window_index)
                        # Extract text from popup if present
                        popup_text = None
                        try:
                            popup_text = self.driver.find_element(By.TAG_NAME, "body").text
                        except Exception:
                            continue
                        if popup_text:
                            logger.info(f"📄 Popup text in window {window_index+1}: {popup_text}")
                            found = True
                    except Exception as e:
                        logger.error(f"❌ Error monitoring for popup in window {window_index+1}: {e}")
                if found:
                    break
                time.sleep(1)
            if not found:
                logger.info("⏰ No popup detected within timeout in any window")
        except Exception as e:
            logger.error(f"❌ Error monitoring for popup: {e}")
    
    def list_windows(self):
        """List all available windows"""
        if self.driver is None:
            logger.error("❌ Driver not initialized.")
            return
        logger.info("📋 Available Windows:")
        for i, window in enumerate(self.windows):
            try:
                self.driver.switch_to.window(window)
                title = self.driver.title
                url = self.driver.current_url
                logger.info(f"  Window {i+1}: {title}")
                logger.info(f"    URL: {url}")
            except:
                logger.info(f"  Window {i+1}: [Error getting info]")
    
    def navigate_to_url(self, url: str, window_index: int = 0):
        """Navigate to a URL in a specific window"""
        if self.driver is None:
            logger.error("❌ Driver not initialized.")
            return False
        try:
            if not self.switch_to_window(window_index):
                return False
            
            self.driver.get(url)
            logger.info(f"✅ Navigated to: {url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error navigating to URL: {e}")
            return False
    
    def close_all(self):
        """Close all connections"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        logger.info("🔒 Closed all connections")

    def play_alarm(self):
        """Play a sound alarm using mpg123 and a custom sound file."""
        try:
            subprocess.Popen(["mpg123", "alarm_sounds/carrousel.mpeg"])
        except Exception as e:
            print(f"Alarm failed: {e}")

    def find_whatsapp_tab(self):
        """Return the index of the WhatsApp Web tab, or None if not found."""
        if self.driver is None:
            return None
        for i, window in enumerate(self.windows):
            self.driver.switch_to.window(window)
            title = self.driver.title
            url = self.driver.current_url
            if ("WhatsApp" in title) or ("web.whatsapp" in url):
                return i
        return None

    def send_message_to_whatsapp(self, message):
        """Send a message to WhatsApp Web (assumes chat is open and input is focused)."""
        if self.driver is None:
            print("Driver not initialized. Cannot send WhatsApp message.")
            return False
        whatsapp_index = self.find_whatsapp_tab()
        if whatsapp_index is None:
            print("WhatsApp Web tab not found. Message not sent.")
            return False
        self.switch_to_window(whatsapp_index)
        try:
            # WhatsApp input box is usually a div with contenteditable="true"
            input_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
            input_box.click()
            input_box.send_keys(message)
            input_box.send_keys("\n")  # Press Enter
            print("Message sent to WhatsApp Web.")
            return True
        except Exception as e:
            print(f"Failed to send message to WhatsApp: {e}")
            return False

    def monitor_for_popups_and_alerts(self, max_minutes=60):
        bot_token = "8077567214:AAFaNw-KlMK4fJ36rny_TCjdtEj6P0ffSlE"
        chat_id = 814781807
        print("Monitoring for popups and transaction alerts (checks every 1 minute, up to 1 hour)...")
        start_time = time.time()
        found = False
        skip_until = {}  # window_index: timestamp until which to skip
        while time.time() - start_time < max_minutes * 60:
            for window in range(min(10, len(self.windows))):
                now = time.time()
                # If this window is being skipped, check if skip time is over
                if window in skip_until and now < skip_until[window]:
                    continue
                try:
                    if self.driver is None:
                        continue
                    self.switch_to_window(window)
                    # === MESSAGE BOX ===
                    message_elem = None
                    try:
                        message_elem = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.flexcc.commonModal-wrap > div > div.normal > div.message"
                        )
                    except NoSuchElementException:
                        try:
                            message_elem = self.driver.find_element(By.XPATH,
                                '//*[@id="app"]/div[2]/div/div[2]/div[2]'
                            )
                        except NoSuchElementException:
                            pass
                    if message_elem:
                        message_text = message_elem.text
                        print(f"\n=== MESSAGE BOX FOUND in window {window+1} ===")
                        print("Text:", message_text)
                        address = extract_deposit_address(message_text)
                        if address:
                            print("Extracted code:", address)
                            found = True
                            # === ALARM, TELEGRAM, SCREENSHOT, AND SKIP LOGIC ===
                            self.play_alarm()
                            send_telegram_message(bot_token, chat_id, address)
                            screenshot_path = '/tmp/screen.png'
                            pyautogui.screenshot(screenshot_path)
                            send_telegram_photo(bot_token, chat_id, screenshot_path, caption='Popup detected!')
                            skip_until[window] = now + 300  # skip for 5 minutes (300 seconds)
                            continue  # Don't check further in this window this loop
                    # === TRY AGAIN BUTTON ===
                    try_again_btn = None
                    try:
                        try_again_btn = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.flexcc.commonModal-wrap > div > div.normal > div.flexcc.buttonBox > div"
                        )
                    except NoSuchElementException:
                        try:
                            try_again_btn = self.driver.find_element(By.XPATH,
                                '//*[@id="app"]/div[2]/div/div[2]/div[3]/div'
                            )
                        except NoSuchElementException:
                            pass
                    if try_again_btn and ("Try Again" in try_again_btn.text or "Try Again Later" in try_again_btn.text):
                        print("Clicking 'Try Again Later' button...")
                        try_again_btn.click()
                        found = True
                    # === COMPLETE TRANSACTION BUTTON ===
                    complete_btn = None
                    try:
                        complete_btn = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.USDT-wrap > div.routerViewBox > div > div.buttonBox.status1 > div.button.rightB"
                        )
                    except NoSuchElementException:
                        pass
                    if complete_btn and "Completed Transaction" in complete_btn.text:
                        print("Clicking 'Completed Transaction' button...")
                        complete_btn.click()
                        found = True
                    # === TRANSACTION ALERT ===
                    alert_elem = None
                    try:
                        alert_elem = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.USDT-wrap > div.routerViewBox > div > div.flexcb.bsbb.orderTipsBox.orderStatus1 > div.leftTips > div:nth-child(2)"
                        )
                    except NoSuchElementException:
                        try:
                            alert_elem = self.driver.find_element(By.XPATH,
                                '//*[@id="app"]/div[1]/div[1]/div/div[3]/div[1]/div[2]'
                            )
                        except NoSuchElementException:
                            pass
                    if alert_elem:
                        print(f"\n=== TRANSACTION ALERT in window {window+1} ===")
                        print("Text:", alert_elem.text)
                        found = True
                    # === CONFIRMATION BOX ===
                    confirm_title = None
                    try:
                        confirm_title = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.flexcc.commonModal-wrap > div > div.normal > div.title"
                        )
                    except NoSuchElementException:
                        pass
                    if confirm_title:
                        print(f"\n=== CONFIRMATION BOX TITLE in window {window+1} ===")
                        print("Text:", confirm_title.text)
                        found = True
                    confirm_box = None
                    try:
                        confirm_box = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.flexcc.commonModal-wrap > div > div.normal"
                        )
                    except NoSuchElementException:
                        pass
                    if confirm_box:
                        print(f"\n=== CONFIRMATION BOX in window {window+1} ===")
                        print("Text:", confirm_box.text)
                        found = True
                    # === OK BUTTON ===
                    ok_btn = None
                    try:
                        ok_btn = self.driver.find_element(By.CSS_SELECTOR,
                            "#app > div.flexcc.commonModal-wrap > div > div.normal > div.flexcc.buttonBox > div"
                        )
                    except NoSuchElementException:
                        try:
                            ok_btn = self.driver.find_element(By.XPATH,
                                '//*[@id="app"]/div[2]/div/div[2]/div[3]/div'
                            )
                        except NoSuchElementException:
                            pass
                    if ok_btn and "OK" in ok_btn.text:
                        print("Clicking 'OK' button...")
                        ok_btn.click()
                        found = True
                except Exception as e:
                    print(f"Error in window {window+1}: {e}")
            print("No new popup found or all popups skipped. Waiting 1 minute before next check...")
            time.sleep(60)
        print("No popup or alert found within the monitoring period or monitoring ended.")

def main():
    """Main function for testing"""
    controller = ChromeController()
    
    try:
        # Connect to existing windows
        if not controller.connect_to_existing_windows():
            return
        
        # List available windows
        controller.list_windows()
        
        # Interactive menu
        while True:
            print("\n🎮 Chrome Controller")
            print("=" * 30)
            print("1. List windows")
            print("2. Navigate to URL")
            print("3. Click element")
            print("4. Monitor for popup in all windows")
            print("5. Monitor for popups and alerts")
            print("6. Exit")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                controller.list_windows()
                
            elif choice == "2":
                url = input("Enter URL: ").strip()
                window = int(input("Enter window number (1-based): ").strip()) - 1
                controller.navigate_to_url(url, window)
                
            elif choice == "3":
                selector = input("Enter selector (CSS or XPath): ").strip()
                for window in range(len(controller.windows)):
                    try:
                        # Try as CSS selector first
                        try:
                            controller.click_element(selector, window, selector_type="css")
                            print(f"Clicked selector in window {window+1} (CSS)")
                            continue
                        except Exception:
                            pass
                        # Try as XPath if CSS fails
                        try:
                            controller.click_element(selector, window, selector_type="xpath")
                            print(f"Clicked selector in window {window+1} (XPath)")
                        except Exception:
                            print(f"Selector not found in window {window+1}, skipping.")
                    except Exception as e:
                        print(f"Error in window {window+1}: {e}")
                
            elif choice == "4":
                controller.monitor_for_popup()
                
            elif choice == "5":
                controller.monitor_for_popups_and_alerts()
                
            elif choice == "6":
                break
                
            else:
                print("❌ Invalid option")
    
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        controller.close_all()

if __name__ == "__main__":
    main() 
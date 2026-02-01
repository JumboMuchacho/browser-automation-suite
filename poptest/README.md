# ⚙️ Poptest: Secure Browser Automation & Monitoring

An enterprise-ready automation utility built for real-time monitoring of dynamic web elements. This suite features a robust **Challenge-Response Authentication** system, hardware-bound licensing, and persistent browser state management.

---

## 🌟 Key Features

- **Multi-Tab Intelligent Scanning:** Unlike standard bots, Poptest iterates through all active window handles, switching context dynamically to detect popups/modals across different sessions.
- **Persistent User Personas:** Profiles are stored in `~/.popup_detector_profile`. This ensures that even if the `.exe` is moved or renamed, user cookies and login sessions (e.g., GameMania) remain intact.
- **Bypass Detection:** Implements `AutomationControlled` flags and custom options to mimic human browser behavior and reduce bot-detection triggers.
- **Smart Resource Management:** Uses `psutil` to identify and terminate "zombie" Chromium processes, ensuring zero resource leakage between application restarts.
- **Resource Bundling:** Dynamically resolves paths for Chromium binaries and audio assets using `sys._MEIPASS`, allowing for a truly portable, single-file distribution.

---

## 🏗 System Architecture

The application is split into two primary domains:

### 1. The Automation Core (main.py)
- **Driver Management:** Automatically locates and initializes bundled Chromium/ChromeDriver binaries.
- **Detection Loop:** Uses a polling mechanism with configurable CSS/XPath selectors to identify target elements.
- **Notification System:** Thread-safe execution of audible alarms via `winsound`.

### 2. The Security Layer (license.py)
- **HMAC Signing:** Uses a shared secret to verify that server responses have not been tampered with.
- **Hardware ID (HID) Binding:** Generates a unique machine fingerprint based on system UUIDs.
- **Secure Storage:** Locally stored licenses are Base64 encoded and validated against the system's hardware signature on every launch.

---

## 📂 Project Structure

```text
.
├── main.py              # Application entry point & Automation Logic
├── license.py           # Cryptographic validation & Hardware Fingerprinting
├── main.bat             # Production environment launcher
├── chrome/              # Portable Chromium binary distribution
├── chromedriver/        # Selenium WebDriver binaries
├── alarm_sounds/        # Resource directory for audible alerts
├── requirements.txt     # Dependency manifest
└── README.md            # System documentation
```

---

## 🛠 Installation & Deployment
---
### Development Environment
```bash

# Initialize Virtual Environment
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows

# Install Dependencies
pip install -r requirements.txt

# Run Application
python main.py
```

## 🛠 Usage & Workflow

### User Instructions

1.  **Authentication:** Upon launch, the application automatically validates your unique Hardware ID (HID). If the device is unauthorized, you will be prompted to enter a valid license key to proceed.
2.  **Navigation:** Once authenticated, the system initializes a dedicated, portable Chromium instance. You should navigate to the target website, log in to your account, and open as many browser tabs as required for your workflow.
3.  **Monitoring:** The automation engine runs in the background, automatically cycling through all active browser tabs every **60 seconds** to scan for specific targets.
4.  **Alerts:** When a designated UI element is detected, the system triggers the `carrousel.wav` alarm to notify you immediately.


---

### Production Build (PyInstaller)
The suite is designed to be distributed as a standalone .exe. Run the following command to bundle all resources:
```bash
pyinstaller --onefile --noconsole main.py ^
  --add-data "alarm_sounds;alarm_sounds" ^
  --add-data "chrome;chrome" ^
  --add-data "chromedriver;chromedriver"
  ```

  ---
 ## 🔒 Security Compliance
 ---
 - Zero-Knowledge Keys: The **LICENSE_SECRET** is never stored in plaintext on the client side.
 - Tamper Resistance: Any manual modification to the **license.cache** file results in an immediate signature mismatch and triggers an authentication challenge.
 - Network Security: All server-side communication is performed over HTTPS with strict timeout handling.
 ---
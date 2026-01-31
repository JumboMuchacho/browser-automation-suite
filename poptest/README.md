# Popup Detector – Licensed Browser Automation Tool

A production-ready, license-protected browser automation utility built with **Python**, **Selenium**, and a secure **FastAPI-based license server**.

This application is distributed as a **standalone Windows executable** and enforces **device-bound licensing** with offline support.

---

## 🔐 Licensing Overview

- One-time license activation per device
- Hardware-bound (Device ID)
- Offline operation supported via signed tokens
- Server-side revocation enforced
- No `.env` files or plaintext keys shipped

---

## 🚀 How Licensing Works

### First Run
1. Launch the application
2. Enter your license key when prompted
3. License is verified with the server
4. A signed token is stored securely on the device

### Subsequent Runs
- No prompt
- No internet required (until token expiry)
- Automatic revalidation when needed

---

## 🗂 Local Storage (Automatic)

| File | Purpose |
|---|---|
| `~/.popup_detector/device.id` | Unique device identifier |
| `~/.popup_detector/license.cache` | Signed license token |

These files should **not be modified manually**.

---

## 🧠 Features

- Popup detection across browser windows
- Audible alerts on detection
- Chrome profile isolation
- License enforcement with device limits
- PyInstaller-compatible

---

## 📦 Project Structure

.
├── main.py                 # Application entry point
├── license.py              # License validation logic
├── chrome/                 # Browser profile data
├── chromedriver/           # Selenium webdriver binaries
├── alarm_sounds/           # Audio alert files (wav/mp3)
├── requirements.txt        # Python dependencies
└── README.md               # Documentation

---

## 🛠 Development Setup (Optional)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py

```

## 🏗 Build Executable

pyinstaller --onefile --noconsole main.py ^
  --add-data "alarm_sounds;alarm_sounds" ^
  --add-data "chrome;chrome" ^
  --add-data "chromedriver;chromedriver"
Output will be in dist/.

## 🔒 Security Notes
- License verification uses HMAC signatures
- Secrets never leave the server
- Tokens are device-bound and time-limited
- Copying the .exe does not bypass licensing

## ❓ Support
If your license is revoked or expires, the application will prompt for a new key.
Contact the distributor for license issues.
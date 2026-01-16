# Popup Detector (Production Edition)

## Overview

Popup Detector is a standalone Chrome monitoring utility designed to **watch for the appearance of a deposit address popup** in real time and **immediately alert the operator with an audible alarm**.

Its sole purpose is to ensure that **the moment a deposit address becomes available**, the user is notified instantly so they can **copy the address and manually complete the required USDT deposit actions (e.g., via Binance)** without delay.

This tool does **not** execute transactions, handle funds, or interact with exchanges. It functions strictly as a **monitoring and alerting assistant** for time-sensitive browser events.

---

## Primary Function

- Monitors the browser DOM for the **deposit address popup**
- Triggers a **loud alarm immediately when the address appears**
- Allows the operator to:
  - Copy the address
  - Perform manual deposit steps externally
  - Complete platform-required actions to qualify for bonuses or credits

No automation beyond detection and alerting is performed.

---

## Key Characteristics

- Real-time DOM-based popup detection
- Selenium-driven Chrome automation
- Audible alarm notification (operator-driven response)
- Headless or visible browser support
- License-controlled execution
- Compiled Windows executable for production use

---

## Intended Use Case

Popup Detector is built for **browser-based operational workflows** where:

- A deposit address appears unpredictably
- Timing is critical
- Missing the popup can result in lost opportunity
- Human confirmation and manual action are required

Typical use includes monitoring **USD-denominated digital credit or gift platforms** that require a user to deposit USDT after an address is generated.

---

## What This Tool Does NOT Do

- Does NOT move funds
- Does NOT place trades
- Does NOT interact with Binance APIs
- Does NOT perform financial transactions
- Does NOT automate deposits

All financial actions are performed **manually by the user**.

---

## Project Structure

```text
popup-detector/
├── alarm_sounds/          # Alarm audio files
├── client.py              # License client logic
├── license.py             # License creation & verification
├── license.json           # Local license configuration
├── main.py                # Core popup monitoring logic
├── main.bat               # Windows launcher
├── popup_detector.spec    # PyInstaller build configuration
├── requirements.txt       # Python dependencies
├── version.txt            # Application versioning
├── README.md
└── .gitignore

```
## Running from Source (Development)

### Requirements
- **Python 3.x**  
- **Google Chrome or Chromium**  
- **Matching ChromeDriver**  

### Setup
Install dependencies and run:

```bash
pip install -r requirements.txt
python main.py

```
## Ensure:

- Chrome.exe exists under chromedriver/chrome-win64/

- Chromedriver.exe exists under chromedriver/chromedriver-win64/

- Alarm audio files are present in alarm_sounds/

## Executable Releases

Precompiled Windows executables are available under GitHub Releases.

No Python installation required

No dependency setup

License-controlled execution

Intended for production operators

Download the latest .exe and run it directly.

## Licensing & Access Control

Popup Detector uses a custom license system for controlled deployment.

Each installation requires a valid license

Execution is blocked without authorization

Access can be enabled or revoked centrally

This ensures safe distribution without exposing unrestricted access or source code.

## Notes

This repository represents the production edition

Earlier experimental prototypes are superseded by this version

Disclaimer
USD denomination references digital platform credits only.
This software does not provide financial, trading, or payment services.

📄 README.md
Secure Browser Automation & Multi-Tab Monitoring Suite
A professional-grade, enterprise-ready automation utility built for real-time monitoring of dynamic web elements. This suite features a robust Challenge-Response Authentication system, hardware-bound licensing, and persistent browser state management.

🌟 Key Features
Intelligent Multi-Tab Scanning: Concurrently monitors all open browser handles to detect specific UI changes (popups, modals, alerts) across different session contexts.

Cryptographic Hardware Binding: Uses machine-specific UUIDs to generate a unique Hardware ID (HID), preventing unauthorized license sharing.

Offline-First Licensing: Implements a local caching mechanism with signed HMAC-SHA256 tokens, allowing verified users to operate without an internet connection until token expiration.

Session Persistence: Configured with custom Chrome Data Directories, ensuring user login states and cookies remain intact between application restarts.

Process Guard: Integrated psutil logic to manage system resources and prevent "zombie" Chromium instances from impacting performance.

🏗 System Architecture
The application is split into two primary domains:

1. The Automation Core (main.py)
Driver Management: Automatically locates and initializes bundled Chromium/ChromeDriver binaries.

Detection Loop: Uses a polling mechanism with configurable CSS/XPath selectors to identify target elements.

Notification System: Thread-safe execution of audible alarms via winsound.

2. The Security Layer (license.py)
HMAC Signing: Uses a shared secret to verify that server responses have not been tampered with.

Secure Storage: Locally stored licenses are Base64 encoded and validated against the system's hardware signature on every launch.

📂 Project Structure
Plaintext
.
├── main.py              # Application entry point & Automation Logic
├── license.py           # Cryptographic validation & Hardware Fingerprinting
├── main.bat             # Production-ready environment launcher
├── chrome/              # Portable Chromium binary distribution
├── chromedriver/        # Selenium WebDriver binaries
├── alarm_sounds/        # Resource directory for audible alerts
├── requirements.txt     # Dependency manifest
└── README.md            # System documentation
🛠 Installation & Deployment
Development Environment
Bash
# Initialize Virtual Environment
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows

# Install Dependencies
pip install -r requirements.txt

# Run Application
python main.py
Production Build (PyInstaller)
The suite is designed to be distributed as a standalone .exe:

Bash
pyinstaller --onefile --noconsole main.py ^
  --add-data "alarm_sounds;alarm_sounds" ^
  --add-data "chrome;chrome" ^
  --add-data "chromedriver;chromedriver"
🔒 Security Compliance
Zero-Knowledge Keys: The LICENSE_SECRET is never stored in plaintext on the client side.

Tamper Resistance: Any manual modification to the license.cache file results in an immediate signature mismatch and triggers an authentication challenge.

Network Security: All server-side communication is performed over HTTPS with strict timeout handling.

📞 Support & Maintenance
For license renewals, hardware migrations, or technical support:

Admin: Jbee

Tel: 0725766022

Status: Active Maintenance
# poptest.py Standalone (Plug & Play)

## What is this?
A robust Chrome popup detection and notification script. Sends Telegram alerts with screenshots and the Chrome profile name.

## Files Needed
- `main.py` (this script)
- `requirements.txt` (Python dependencies)
- `alarm_sounds/carrousel.wav` (alarm sound)
- `config.json` (for your Telegram bot token/chat ID)

## How to Run

### 1. Install Python 3.8+

### 2. Set up a virtual environment (recommended)
```sh
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install dependencies
```sh
pip install -r requirements.txt
```

### 4. Download Chromium and ChromeDriver
- Download Chromium from [Chromium snapshots](https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Win/)
- Download the matching ChromeDriver from [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) 

- Create a folder 'Chromendriver' in the poptest dir
- Place `chrome.exe` in `chromendriver/chrome-win64/`
- Place `chromedriver.exe` in `chromendriver/chromedriver-win64/`

### 5. Configure
- Edit `config.json` and set your Telegram bot token and chat ID:
```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "chat_id": "YOUR_CHAT_ID_HERE",
  ...
}
```

### 6. Run the script
```sh
python main.py
```

## Notes
- Chrome will be launched with a fresh profile in `automation_profile/`.
- The script will play an alarm and send a screenshot with the profile name as caption when a popup is detected.
- If you want to use a different alarm sound, use a `.wav` file for best compatibility on Windows.

## Windows PowerShell Users: Script Activation Issue
If you see an error like:

    cannot be loaded because running scripts is disabled on this system

run this command in PowerShell (once per user):

    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Then activate your virtual environment as usual:

    .\venv\Scripts\Activate

This allows local scripts (like venv activation) to run safely.

## Contributing
Pull requests are welcome!

## License
See LICENSE file. 
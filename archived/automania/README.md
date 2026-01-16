# Chrome Automation Suite - "Chip In" Project

A comprehensive Chrome automation system with popup detection, deposit automation, and robust error handling.

## 🎯 What It Does

- **Popup Detection**: Monitors Chrome windows for specific popups and sends notifications
- **Deposit Automation**: Automates deposit workflows with retry logic and error handling
- **Fresh Profile Management**: Starts with clean profiles and persists new data for reuse
- **Cross-Platform**: Works on Linux, Windows, and macOS
- **Robust Error Handling**: Multiple fallbacks, health checks, and graceful degradation
- **Telegram Integration**: Sends notifications with screenshots and audio alerts

## 🆕 New Profile Management (v2.0)

**Fresh Start Approach**: The automation now uses a clean, dedicated profile that:
- **First Run**: Creates a fresh automation profile (no copying from existing profiles)
- **Subsequent Runs**: Reuses the automation profile with any new data you've added
- **Safe**: Never touches your real Chrome profiles
- **Persistent**: Saves your automation-specific data for future runs

### Benefits:
- ✅ **Clean slate**: No conflicts with existing profiles
- ✅ **Safe**: Your real profiles remain untouched
- ✅ **Persistent**: Automation data is saved for reuse
- ✅ **Isolated**: Dedicated profile for automation tasks

## 📋 Requirements

```bash
pip install -r requirements.txt
```

## 🚀 Best Practice Setup (Cross-Platform)

### 1. Create and Activate Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bat
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Clean Up Old Profiles (Optional)
If you have old profile directories from previous versions:
```bash
python cleanup_profiles.py
```

### 4. Run the Main Menu Launcher
```bash
python run.py
```

## 🎮 Available Scripts

### Main Automation Scripts

1. **Popup Detection** (`poptest.py`)
   - Monitors Chrome windows for specific popups
   - Sends Telegram notifications with screenshots
   - Throttles notifications to avoid spam
   - Cross-platform audio alerts

2. **Deposit Automation** (`deposit_automation.py`)
   - Automates deposit workflows
   - Retry logic with exponential backoff
   - Error recovery and health checks
   - Telegram notifications for success/failure

3. **Chrome Launcher** (`launch_chrome_debug.py`)
   - Launches Chrome with remote debugging
   - Automatic port detection and ChromeDriver compatibility
   - Fresh profile management
   - Health checks and error recovery

4. **Chrome Controller** (`chrome_controller.py`)
   - Connects to existing Chrome windows
   - Element clicking and navigation
   - Popup monitoring and text extraction

### Utility Scripts

- `run.py` - Main menu launcher
- `cleanup_profiles.py` - Clean up old profile directories
- `refresh.py` - Refresh Chrome session

## 🔧 Configuration

### Automatic Configuration
Scripts automatically create configuration files on first run:
- `chrome_launcher_config.json` - Chrome launcher settings
- `deposit_config.json` - Deposit automation settings
- `poptest_config.json` - Popup detection settings

### Manual Configuration
Edit the generated config files to customize:
- Timeouts and retry settings
- Telegram bot settings
- Audio and screenshot preferences
- Health check parameters

## 🛡️ Robustness Features

### Health Checks
- Chrome installation verification
- ChromeDriver compatibility checks
- Internet connectivity monitoring
- Disk space and memory usage checks
- Telegram API connectivity

### Error Recovery
- Multiple fallback methods for screenshots
- Cross-platform audio playback
- Automatic ChromeDriver updates
- Port scanning and detection
- Graceful degradation modes

### Configuration Management
- Centralized configuration with fallbacks
- User-configurable settings
- Automatic config file creation
- Deep merge of user and default settings

### Logging and Monitoring
- Comprehensive logging to files and console
- Error tracking and reporting
- Performance monitoring
- Debug information for troubleshooting

## 💡 Example Usage

### Popup Detection
```bash
# Run popup detection for 20 minutes
python poptest.py

# Monitor will:
# - Launch Chrome with fresh profile
# - Monitor for popups every 5 seconds
# - Send Telegram notifications with screenshots
# - Play audio alerts
# - Throttle notifications to avoid spam
```

### Deposit Automation
```bash
# Run deposit automation
python deposit_automation.py bnb 50

# Automation will:
# - Connect to Chrome with fresh profile
# - Navigate to target site
# - Execute deposit workflow
# - Send success/failure notifications
# - Handle errors with retry logic
```

### Chrome Launcher
```bash
# Launch Chrome with debugging
python launch_chrome_debug.py

# Launcher will:
# - Check Chrome and ChromeDriver compatibility
# - Find free debug port
# - Create fresh automation profile
# - Launch Chrome with optimal settings
```

## 🔍 Troubleshooting

### Common Issues

1. **Chrome not found**
   - Install Google Chrome
   - Check PATH environment variable

2. **ChromeDriver compatibility**
   - Scripts automatically update ChromeDriver
   - Manual update: `pip install --upgrade chromedriver-autoinstaller`

3. **Port conflicts**
   - Scripts automatically find free ports
   - Kill existing Chrome processes: `pkill -f chrome`

4. **Telegram notifications not working**
   - Check bot token and chat ID in config
   - Verify internet connectivity
   - Check Telegram API status

### Debug Mode
Enable debug logging by editing config files:
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## 📁 Project Structure

```
chip_in/
├── automation_profile/          # Fresh automation profile (created on first run)
├── logs/                        # Log files
├── alarm_sounds/               # Audio alert files
├── poptest.py                  # Popup detection script
├── deposit_automation.py       # Deposit automation script
├── launch_chrome_debug.py      # Chrome launcher
├── chrome_controller.py        # Chrome controller
├── run.py                      # Main menu launcher
├── cleanup_profiles.py         # Profile cleanup utility
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🎯 Key Advantages

- **Fresh Profiles**: Clean start with persistent automation data
- **Robust Error Handling**: Multiple fallbacks and recovery mechanisms
- **Cross-Platform**: Works on Linux, Windows, and macOS
- **Comprehensive Logging**: Detailed logs for troubleshooting
- **Configuration Management**: User-friendly settings
- **Health Monitoring**: System health checks and alerts
- **Graceful Degradation**: Continues operation even with partial failures

## 🔄 Migration from v1.0

If you're upgrading from the previous version:

1. **Backup your data** (if needed)
2. **Run cleanup**: `python cleanup_profiles.py`
3. **Start fresh**: Scripts will create new automation profiles
4. **Configure**: Edit generated config files as needed

The new approach is safer and more reliable than copying existing profiles. 
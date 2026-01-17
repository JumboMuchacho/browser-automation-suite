@echo off
REM Batch file to activate venv and run poptest.py

REM Activate the virtual environment
call "venv\Scripts\activate.bat"

REM Run the script
python poptest.py

REM Pause so the window stays open after script ends
pause 
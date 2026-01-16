@echo off
REM Batch file to run main.py

REM Activate virtual environment if it exists
IF EXIST "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

REM Run the script
python main.py 
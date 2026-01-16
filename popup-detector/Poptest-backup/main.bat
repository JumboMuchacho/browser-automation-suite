@echo off
cd /d "%~dp0"

set VENV_PATH=.env

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found at %VENV_PATH%
    pause
    exit /b
)

call "%VENV_PATH%\Scripts\activate.bat"

python main.py

pause

@echo off
cd /d "%~dp0"

:: CHANGE THIS LINE FROM .env TO venv
set VENV_PATH=venv

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found at %VENV_PATH%   
    pause
    exit /b
)

call "%VENV_PATH%\Scripts\activate.bat"

python main.py

pause
@echo off
echo ========================================
echo NovaTrip AI - Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.13.9 from python.org
    pause
    exit /b 1
)

echo Step 1: Creating virtual environment...
python -m venv venv_nt
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv_nt\Scripts\activate.bat

echo Step 3: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. (Optional) Set your Groq API key:
echo    $env:GROQ_API_KEY="your-api-key-here"
echo.
echo 2. Run the application:
echo    python app_main.py
echo.
echo 3. Open browser at: http://127.0.0.1:5000
echo.
echo Or simply run: run.bat
echo ========================================
pause

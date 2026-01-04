@echo off
echo ========================================
echo NovaTrip AI - Starting Application
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv_nt\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv_nt\Scripts\activate.bat

REM Check if database exists, if not create it
if not exist "instance\novatrip.db" (
    echo Creating database...
    python -c "from app_main import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
)

echo Starting NovaTrip AI server...
echo.
echo Open your browser at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python app_main.py

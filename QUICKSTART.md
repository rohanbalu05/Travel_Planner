# 🚀 Quick Start Guide - Windows

## Prerequisites
- Python 3.13.9 installed on Windows
- Internet connection

---

## Option 1: Automated Setup (Easiest!)

### Step 1: Run Setup
Double-click `setup.bat` or run in terminal:
```cmd
setup.bat
```

This will automatically:
- Create virtual environment
- Install all dependencies
- Set up the application

### Step 2: Run Application
Double-click `run.bat` or run in terminal:
```cmd
run.bat
```

### Step 3: Open Browser
Navigate to: **http://127.0.0.1:5000**

Done! 🎉

---

## Option 2: Manual Setup

### Step 1: Create Virtual Environment
```cmd
python -m venv venv_nt
```

### Step 2: Activate Virtual Environment
```cmd
venv_nt\Scripts\activate
```

### Step 3: Install Dependencies
```cmd
pip install -r requirements.txt
```

### Step 4: Set Groq API Key (Optional)
**PowerShell:**
```powershell
$env:GROQ_API_KEY="your-api-key-here"
```

**CMD:**
```cmd
set GROQ_API_KEY=your-api-key-here
```

> **Note:** The app works without API key using mock data

### Step 5: Run Application
```cmd
python app_main.py
```

### Step 6: Open Browser
Navigate to: **http://127.0.0.1:5000**

---

## Troubleshooting

### "Python is not recognized"
- Make sure Python 3.13.9 is installed
- Add Python to PATH during installation
- Or use full path: `C:\Python313\python.exe`

### "pip is not recognized"
```cmd
python -m pip install -r requirements.txt
```

### "Virtual environment not activating"
Try using full path:
```cmd
venv_nt\Scripts\activate.bat
```

### Port 5000 already in use
The app will show an error. Either:
- Stop the application using port 5000
- Or change the port in `app_main.py` (line 1069)

### Database errors
Delete the database and restart:
```cmd
rmdir /s /q instance
python app_main.py
```

---

## What Gets Installed

The application will install these packages:
- **Flask**: Web framework
- **groq**: AI model API client
- **requests**: HTTP library
- **Flask-SQLAlchemy**: Database ORM
- **Werkzeug**: Security utilities
- **reportlab**: PDF generation

Total size: ~50MB

---

## First Time Usage

1. **Register**: Create an account with username, email, and password
2. **Login**: Sign in with your credentials
3. **Create Trip**: Fill in destination, days, budget, and trip type
4. **Generate**: AI creates your personalized itinerary
5. **Enjoy**: View, edit, download, and share your travel plans!

---

## Stopping the Application

Press `Ctrl+C` in the terminal where the app is running

---

## Next Steps

- Read the full [README.md](README.md) for all features
- Check [CHANGES.md](CHANGES.md) for version history
- See example trips in the application

---

**Having issues? Check that:**
- ✅ Python 3.13.9 is installed
- ✅ Virtual environment is activated
- ✅ All dependencies installed successfully
- ✅ No other application is using port 5000
- ✅ You're in the correct project directory

---

*Happy traveling with NovaTrip AI! ✈️*

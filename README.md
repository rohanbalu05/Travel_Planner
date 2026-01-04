# NovaTrip AI - Travel Itinerary Planner

AI-powered travel itinerary planner with beautiful UI and interactive features.

---

## Setup & Installation

### Prerequisites
- Python 3.13.9
- Windows Operating System

---

### Step-by-Step Setup

#### Step 1: Create Virtual Environment
```cmd
python -m venv venv_nt
```

#### Step 2: Activate Virtual Environment
```cmd
venv_nt\Scripts\activate
```

You should see `(venv_nt)` at the beginning of your command prompt.

#### Step 3: Install Dependencies
```cmd
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Groq (AI model)
- Requests (HTTP library)
- Flask-SQLAlchemy (database)
- Werkzeug (security)
- ReportLab (PDF generation)

#### Step 4: Set Groq API Key (Optional)
The application works without an API key using mock data.

If you have a Groq API key:

**PowerShell:**
```powershell
$env:GROQ_API_KEY="your-api-key-here"
```

**Command Prompt:**
```cmd
set GROQ_API_KEY=your-api-key-here
```

#### Step 5: Run the Application
```cmd
python app_main.py
```

You should see output like:
```
* Running on http://127.0.0.1:5000
* Press CTRL+C to quit
```

#### Step 6: Open in Browser
Open your web browser and go to:
```
http://127.0.0.1:5000
```

---

## First Time Usage

1. **Register**: Click "Register" and create an account
   - Enter username
   - Enter email
   - Enter password

2. **Login**: Sign in with your credentials

3. **Create Trip**: Fill in the form
   - Destination (e.g., "Paris, France")
   - Number of days (e.g., 5)
   - Budget (e.g., "50000 INR")
   - Trip type (e.g., "cultural")

4. **Generate**: Click "Generate Itinerary"

5. **View & Edit**:
   - View your itinerary on the map
   - Edit using the AI chat assistant
   - Download as PDF or TXT

---

## Features

- AI-powered itinerary generation
- Beautiful travel-themed UI
- Interactive maps with route planning
- Chat-based itinerary modifications
- PDF/TXT export
- Multiple trip management
- Secure authentication

---

## Stopping the Application

Press `CTRL+C` in the terminal where the app is running.

---

## Troubleshooting

### "python is not recognized"
Make sure Python 3.13.9 is installed and added to PATH.

### "pip is not recognized"
Use: `python -m pip install -r requirements.txt`

### Port 5000 already in use
Close any other applications using port 5000.

### Database errors
Delete the instance folder and restart:
```cmd
rmdir /s /q instance
python app_main.py
```

### Virtual environment not activating
Make sure you're in the correct directory and use:
```cmd
venv_nt\Scripts\activate.bat
```

---

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite + SQLAlchemy
- **AI**: Groq LLaMA 3.1
- **Maps**: Leaflet.js + OpenStreetMap
- **Routing**: OSRM
- **PDF**: ReportLab

---

## Author

Rahul Sonar

# 🧭 NovaTrip AI – AI-Powered Travel Itinerary Planner  
### Built with Flask + Groq LLaMA Models

NovaTrip AI is a simple, fast and free AI itinerary generator.  
The user enters destination, budget, number of days, and travel type.  
The system generates a complete day-by-day travel plan using Groq’s LLaMA models.

---

## 🚀 Features

- AI-generated itineraries  
- Groq LLaMA 3.1 model integration  
- Zero billing required  
- Flask backend  
- Clean HTML/CSS UI  
- Mock itinerary when API key is missing  

---

## 🛠️ Tech Stack

- Python  
- Flask  
- Groq LLaMA 3.1  
- HTML/CSS (Jinja templates)

---

## 📦 Folder Structure

NovaTripAI/
│── app_main.py
│── templates_main/
│ └── index_page.html
│── .gitignore
│── requirements.txt
│── README.md

---

## ⚙️ Setup Instructions

### 1) Clone the repo
git clone https://github.com/rahulnew0405-del/NovaTripAI.git

cd NovaTripAI

### 2) Create virtual environment
python -m venv venv_nt
.\venv_nt\Scripts\activate


### 3) Install dependencies


pip install -r requirements.txt


### 4) Set Groq API key


$env:GROQ_API_KEY="grq-YOUR_KEY_HERE"


### 5) Run the project


python app_main.py


Open in browser:  
http://127.0.0.1:5000/

---

## 🧠 How It Works

1. User enters travel details  
2. Flask receives input  
3. Prompt is sent to Groq API  
4. LLaMA model generates itinerary  
5. Webpage displays it neatly  

---

## 🔮 Future Scope

- Live flight/hotel APIs  
- Saved itineraries  
- Mobile UI  

---

## 👤 Author

**Rahul Sonar**  
NovaTrip AI – Mini Project

# 🔥 CalorieBot // Personal Nutrition & Calorie Tracking System

> **Designed specifically for your weight-cut goal:**  
> **Profile:** 21 y/o Male | **Height:** 168 cm | **Current Weight:** 89 kg ➔ **Target Weight:** 70 kg (-19 kg)  
> **Daily Calorie Target:** **1,750 kcal/day** (~500 kcal safe daily deficit from 2,208 kcal maintenance)  
> **Daily Protein Goal:** **120g** (preserves lean muscle while burning fat)

---

## ⚡ What CalorieBot Does

1. **📱 Free & Unlimited Chat Logging (Telegram Bot):**
   - Text whatever you eat anytime throughout the day.
   - Handles natural terms:
     - *"for morning/breakfast/tiffin i ate 2 dosas and sambar"*
     - *"for lunch i ate 1 bowl rice, dal and chicken curry"*
     - *"for snack/snacks i ate samosa and chai"*
     - *"meanwhile i ate an apple and almonds"*
     - *"for dinner i ate 2 rotis with paneer"*
   - Instant calculation: items, quantities, calories, macros (Protein, Carbs, Fats), running total today, remaining deficit, and smart nutrition tips.

2. **📊 End-Of-Day (EOD) Audit & PDF Report:**
   - Type **`EOD`** when finished for the day.
   - The bot analyzes:
     - Did you eat in excess?
     - What specific foods caused the calorie spike?
     - What to control and replace tomorrow (e.g. reduce rice, skip fried snacks).
   - Generates and sends a **formatted summary + downloadable PDF report** directly in chat!

3. **🌐 Real-Time Web Dashboard:**
   - Open `http://localhost:8000/dashboard` in any browser.
   - Real-time KPI cards: Consumed vs Budget, Remaining, Protein tracker, Weight loss progress.
   - Interactive Chart.js charts: Calorie distribution by meal, 7-day intake history with budget target line.
   - Log meals directly from the web interface or delete entries with one click.
   - Download historical PDF reports.

---

## 🚀 2-Minute Quick Setup

### Step 1: Get your Free Telegram Bot Token (30 seconds)
1. Open Telegram and search for **`@BotFather`** (the official verified bot).
2. Send `/newbot`.
3. Choose a name (e.g. `MyCalorieCoach`) and a username (e.g. `my_calorie_cut_bot`).
4. Copy the **HTTP API Token** provided by BotFather.

### Step 2: Get your Free Google Gemini API Key (30 seconds)
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **"Create API Key"** and copy your key. (Gemini 2.5 Flash free tier gives thousands of requests daily).

### Step 3: Configure `.env`
Open the `.env` file in the project folder and paste your keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🏃 Running the Project

### On Windows (One-Click):
Double-click:
```bat
start.bat
```
Or run in PowerShell:
```powershell
.\start.ps1
```

### Manual CLI:
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Start server & bot
python run.py
```

- **Telegram Bot:** Open Telegram, find your bot, and send `/start`
- **Web Dashboard:** Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

---

## 💬 Bot Commands & Usage

| Message / Command | Action |
|-------------------|--------|
| `/start` | Welcome message with your 89kg ➔ 70kg profile & instructions |
| `for breakfast 2 idlis & sambar` | Automatically parses and logs breakfast |
| `for lunch rice, dal, chicken` | Automatically parses and logs lunch |
| `for snack biscuits and chai` | Automatically parses and logs evening snack |
| `meanwhile 1 banana` | Logs in-between snacking / munching |
| `/status` or `status` | Shows today's running intake, calories left, and logged meals |
| `/undo` | Deletes your last logged meal in case of typos |
| `EOD` or `/eod` | Triggers the daily nutrition audit & sends your **PDF Daily Report** |
| `/dashboard` | Provides your web dashboard URL |

---

## ☁️ Free 24/7 Cloud Deployment

The repository includes ready-to-deploy configurations for free cloud hosts:

### Option A: Render.com (Recommended - 100% Free)
1. Push this project to a free GitHub repository.
2. Go to [Render.com](https://render.com) and create a free account.
3. Click **New +** ➔ **Web Service** ➔ Connect your GitHub repo.
4. Render will auto-detect the `render.yaml` or set:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run.py`
5. Under **Environment Variables**, add:
   - `TELEGRAM_BOT_TOKEN`: your bot token
   - `GEMINI_API_KEY`: your gemini API key
6. Click **Deploy**! Your bot and dashboard will now run 24/7 in the cloud with zero hosting cost.

### Option B: Railway / Fly.io / Docker
A production `Dockerfile` is included in the root directory:
```bash
docker build -t caloriebot .
docker run -p 8000:8000 --env-file .env caloriebot
```

---

## 📁 Project Architecture
```
noble-turing/
├── app/
│   ├── config.py             # User stats (21M, 168cm, 89kg -> 70kg), BMR & budget
│   ├── database.py           # SQLite database engine
│   ├── models.py             # MealLog, DailyReport, WeightLog
│   ├── gemini_parser.py      # Google Gemini 2.5 Flash + offline fallback parser
│   ├── report_generator.py   # Daily audit analysis & ReportLab PDF generator
│   ├── bot.py                # Telegram Bot handler (commands, EOD, food logger)
│   ├── web_app.py            # FastAPI dashboard & REST APIs
│   ├── templates/
│   │   └── dashboard.html    # Modern dark theme dashboard with Chart.js
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js   # Dynamic charts & AJAX meal logging
├── data/
│   ├── caloriebot.db         # Persistent SQLite database
│   └── reports/              # Generated daily PDF reports
├── run.py                    # Master unified runner (Web + Bot)
├── start.bat                 # 1-click Windows launcher
├── start.ps1                 # PowerShell launcher
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container deployment
├── render.yaml               # Render free cloud deployment config
└── .env                      # API tokens and configuration
```

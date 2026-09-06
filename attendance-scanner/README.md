# AttendScan — Student Attendance Scanner App

A premium web app for teachers to scan student ID cards and take attendance automatically.

## Stack
- **Frontend:** React 18 + Vite + Tailwind CSS + Framer Motion
- **Backend:** Python 3.11+ + FastAPI + pytesseract OCR
- **Database:** Supabase (Postgres) — only database, no fallback

---

## SETUP (Step by Step)

### Step 1: Supabase Database
1. Go to https://supabase.com → create a new project
2. Open **SQL Editor** → New Query
3. Copy and paste everything from `supabase_schema.sql` → click **Run**
4. Go to **Project Settings** → **API** → copy:
   - `Project URL` (SUPABASE_URL)
   - `service_role` key (SUPABASE_SERVICE_ROLE_KEY) — keep this secret!

### Step 2: Backend Configuration
1. Copy `backend\.env.example` → `backend\.env`
2. Fill in your values:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJ...
   JWT_SECRET=any-random-string-at-least-32-chars
   ```

### Step 3: Install Tesseract OCR (for ID card scanning)
- **Windows:** Download from https://github.com/UB-Mannheim/tesseract/wiki
  - Install to `C:\Program Files\Tesseract-OCR\`
  - Add to PATH: System Properties → Environment Variables → Path → Add `C:\Program Files\Tesseract-OCR`
- **Mac:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

### Step 4: Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 5: Install Node.js dependencies
```bash
cd frontend
npm install
```

---

## RUNNING THE APP

### Easy way (double-click):
Run `start.bat` in the project root — it starts both backend and frontend.

### Manual way:
**Terminal 1 (Backend):**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

Open: **http://localhost:5173**

---

## ACCESSING ON PHONE (for camera scanning)

Since camera requires HTTPS or localhost, use one of these methods:

### Option A: Same WiFi Network
1. Find your computer's IP: run `ipconfig` → look for IPv4 (e.g. 192.168.1.5)
2. Open on phone: `http://192.168.1.5:5173`
3. ⚠️ Camera may not work on HTTP on Android Chrome — use Option B for best results

### Option B: ngrok tunnel (HTTPS)
1. Download ngrok from https://ngrok.com
2. Run: `ngrok http 5173`
3. Use the `https://xxx.ngrok.io` URL on your phone — camera works perfectly!

### Option C: Build & serve with HTTPS
```bash
cd frontend && npm run build
cd ../backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Then visit: `http://localhost:8000` (backend serves the built frontend)

---

## HOW THE SCANNER WORKS

1. Teacher taps **"Scan Attendance"** on Home screen
2. Camera opens automatically on **back camera** (phone camera)
3. Hold student ID card in front of camera — **any orientation** works
4. App captures frames for 1–6 seconds, picks the sharpest one
5. Python OCR (pytesseract) reads all text on the card
6. Extracted Roll No / ID No / Name matched against student roster
7. **Any ONE match** = student marked Present ✅
8. Green flash + chime on success, Red flash + buzz on failure
9. Tap **Stop** → Home shows full present/absent summary

---

## PROJECT STRUCTURE

```
attendance-scanner/
├── start.bat                 ← Run this to start everything
├── supabase_schema.sql       ← Run this in Supabase SQL editor once
├── backend/
│   ├── .env                  ← Your Supabase credentials (create this!)
│   ├── .env.example          ← Template
│   ├── main.py               ← FastAPI app
│   ├── config.py             ← Env var loading
│   ├── requirements.txt      ← Python dependencies
│   ├── auth/                 ← Login / Register routes
│   ├── students/             ← Student CRUD routes
│   ├── timetable/            ← Schedule CRUD routes
│   ├── sessions/             ← Attendance session routes
│   ├── scan/                 ← OCR scan endpoint
│   └── ocr/pipeline.py       ← Frame picking + OCR + matching
└── frontend/
    ├── src/screens/          ← All app screens
    │   ├── SplashScreen.tsx  ← 3.5s animated intro
    │   ├── LoginScreen.tsx
    │   ├── RegisterScreen.tsx
    │   ├── HomeScreen.tsx    ← Today lectures + scan button
    │   ├── ScannerScreen.tsx ← Camera + OCR feedback
    │   ├── SettingsScreen.tsx← Students + Timetable management
    │   └── HistoryScreen.tsx ← Session history + detail
    ├── src/api/client.ts     ← Axios API client
    └── src/sounds/audio.ts   ← Web Audio API chimes
```

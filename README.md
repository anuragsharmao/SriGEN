# SriGEN

Secure Generative AI Platform for multi-format content transformation, verification, disclosure control, and provenance tracking.

This repository contains the full SriGEN project:

- Backend: FastAPI service with ingestion, fact graph extraction, sensitivity detection, generation adapters, verification, approval flow, and provenance ledger
- Frontend: React + Vite dashboard for generating and reviewing drafts
- Database: SQLite for local development

## What this project actually uses

The codebase is configured for:

- Python 3.11.11
- Backend virtual environment in `backend/.venv`
- Gemini as the primary LLM backend
- Groq as the fallback backend
- SQLite database in the backend folder
- Frontend served by Vite on the local dev server

Important: do not use Python 3.13 or a system-wide Python unless you specifically know the repo is compatible. The project is pinned to Python 3.11 in [backend/runtime.txt](backend/runtime.txt).

## Prerequisites

- Python 3.11 installed
- Node.js 18+ and npm installed
- API keys for Gemini and/or Groq
- Git Bash, PowerShell, or a terminal with access to the project folder

## 1) Create the backend virtual environment

From the project root:

```powershell
py -3.11 --version
py -3.11 -m venv backend/.venv
```

Activate it in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\backend\.venv\Scripts\Activate.ps1
```

If you are using cmd instead of PowerShell:

```cmd
backend\.venv\Scripts\activate.bat
```

## 2) Install backend dependencies

```powershell
cd backend
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If you want the optional spaCy English model used by some extraction/grounding checks:

```powershell
python -m spacy download en_core_web_sm
```

## 3) Configure environment variables

Create a local backend environment file from the example:

```powershell
copy .env.example .env
```

Then edit `backend/.env` and set the required values. The repo expects keys like:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
LLM_BACKEND=gemini
LLM_FALLBACK_BACKEND=groq
DATABASE_URL=sqlite:///./srigen.db
CORS_ORIGINS_RAW=http://localhost:3000,http://127.0.0.1:3000
OPERATOR_BOOTSTRAP_USERNAME=your_admin_username
OPERATOR_BOOTSTRAP_PASSWORD=your_admin_password
```

You can also leave `OPERATOR_BOOTSTRAP_USERNAME` and `OPERATOR_BOOTSTRAP_PASSWORD` blank if you want to create accounts manually later.

The current project default is Gemini-first with Groq fallback. This is intentional and matches the configuration in [backend/app/core/config.py](backend/app/core/config.py).

## 4) Run the backend

From the project root while the virtual environment is active:

```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend API docs are available at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

Health check:

- http://localhost:8000/health

## 5) Run the frontend

Open a new terminal and do:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs by default on:

- http://localhost:5173

## 6) First-time login / bootstrap

If you set `OPERATOR_BOOTSTRAP_USERNAME` and `OPERATOR_BOOTSTRAP_PASSWORD`, the app creates a default approver account on first startup automatically.

Otherwise, use the auth endpoints to register or log in through the backend API.

## 7) Common project commands

Backend:

```powershell
cd backend
python -m pytest -q
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

## 8) Notes on the actual runtime behavior

- Gemini is primary by default, but quota exhaustion or provider errors trigger automatic fallback to Groq.
- The backend does not use fake or placeholder values for generation, approvals, or ledger data. The project was cleaned up to remove dummy frontend data and unconnected mock responses.
- The backend maintains local databases and runs the app using SQLite for local development.
- If you start from the wrong Python interpreter or skip the virtual environment, installs and imports will fail or behave inconsistently.

## 9) Project structure

```text
SriGEN/
├── README.md
├── backend/
│   ├── .env.example
│   ├── .venv/
│   ├── app/
│   ├── requirements.txt
│   ├── runtime.txt
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   └── vite.config.js
└── docs/
```

## 10) Quick start summary

```powershell
# from project root
py -3.11 -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
cd backend
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
copy .env.example .env
# edit .env with your keys
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

If you want, I can also tighten the root README further into a cleaner “setup + troubleshooting” format for sharing with teammates.

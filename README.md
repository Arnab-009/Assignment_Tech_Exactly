# 📄 Document Summarizer

> **AI-powered Google Drive document summarizer** — Connect your Google Drive, select a folder, and get concise AI-generated summaries for every PDF, DOCX, TXT, and Google Docs file inside it.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Google Drive OAuth2** | Secure sign-in with Google. Read-only access to your Drive. |
| **Multi-format Parsing** | Extracts text from PDF (PyMuPDF), DOCX (python-docx), TXT, and Google Docs (auto-exported). |
| **AI Summarization** | Each document gets a 5–10 sentence summary powered by Gemini 2.5 Flash. |
| **Batch Processing** | Processes up to 20 files concurrently with per-file fault isolation. |
| **Export Reports** | Download results as a CSV spreadsheet or a styled PDF report. |
| **Modern React UI** | Clean, responsive interface with real-time loading states, expandable summaries, and file-type badges. |
| **Docker Ready** | One-command deployment with `docker compose up`. |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLIENT BROWSER                   │
│           React SPA (Vite + Tailwind CSS)           │
└────────────────────┬────────────────────────────────┘
                     │ HTTP (:8080)
┌────────────────────▼────────────────────────────────┐
│                 NGINX REVERSE PROXY                 │
│     /api/* → backend:8000    /* → static files      │
└────────┬──────────────────────────┬─────────────────┘
         │                          │
┌────────▼───────────┐    ┌────────▼─────────────────┐
│   FASTAPI BACKEND  │    │  REACT STATIC FILES      │
│                    │    │  (built by Vite)          │
│  ┌──────────────┐  │    └──────────────────────────┘
│  │ Auth Router  │  │
│  │ Drive Router │  │
│  │ Summarize    │  │
│  │ Export       │  │
│  └──────────────┘  │
│  ┌──────────────┐  │
│  │ Services:    │  │
│  │ Drive        │──┼──→ Google Drive API
│  │ Parser       │  │
│  │ LLM          │──┼──→ Gemini 2.5 Flash
│  │ Export       │  │
│  └──────────────┘  │
└────────────────────┘
```

---

## 📋 Prerequisites

1. **Python 3.12+** (for local development without Docker)
2. **Node.js 20+** (for local frontend development)
3. **Docker & Docker Compose** (for containerized deployment)
4. **Google Cloud Project** with:
   - Google Drive API enabled
   - OAuth 2.0 Web Client credentials
5. **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/apikey)

---

## 🔐 Google Cloud Setup (One-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Drive API**
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs:
     - Docker: `http://localhost:8080/api/auth/callback`
     - Local dev: `http://localhost:5173/api/auth/callback`
6. Copy the **Client ID** and **Client Secret**

---

## 🚀 Quick Start (Docker)

The fastest way to run the full stack:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Assignment_Tech_Exactly.git
cd Assignment_Tech_Exactly

# 2. Create your environment file
cp .env.example .env
# Edit .env with your real credentials:
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GEMINI_API_KEY, SECRET_KEY

# 3. Build and start all services
docker compose up --build

# 4. Open in browser
open http://localhost:8080
```

### What Docker starts:

| Service | Container | Port |
|---|---|---|
| FastAPI backend | `docsum-backend` | 8000 (internal) |
| React frontend | `docsum-frontend` | — (provides static files) |
| Nginx proxy | `docsum-nginx` | **8080** (public) |

---

## 🛠️ Local Development (Without Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env from the root template
cp ../.env.example .env
# Edit .env: set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GEMINI_API_KEY, SECRET_KEY
# IMPORTANT: For local dev, set:
#   GOOGLE_REDIRECT_URI=http://localhost:5173/api/auth/callback
#   POST_LOGIN_REDIRECT=http://localhost:5173

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api → localhost:8000)
npm run dev
# → Opens at http://localhost:5173
```

---

## 🧪 Running Tests

```bash
cd backend

# Install dev dependencies
pip install -r requirements-dev.txt

# Run the test suite
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_parser.py -v
```

### Test Coverage

| Test File | What It Tests |
|---|---|
| `test_parser.py` | PDF, DOCX, TXT extraction; truncation; error handling; edge cases |
| `test_llm.py` | Gemini API mocking; batch processing; fault isolation; empty/error skipping |
| `test_export.py` | CSV structure/encoding; PDF generation; empty input handling |

---

## 📁 Project Structure

```
Assignment_Tech_Exactly/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py              # Package + version
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── config.py                # pydantic-settings config
│   │   ├── dependencies.py          # DI: auth, services, session
│   │   ├── exceptions.py            # Domain exceptions
│   │   ├── cache.py                 # In-memory TTL result store
│   │   ├── logging_config.py        # Structured logging setup
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic models
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py              # OAuth2 login/callback/logout
│   │   │   ├── drive.py             # Drive folder listing + preview
│   │   │   ├── summarize.py         # Full pipeline endpoint
│   │   │   └── export.py            # CSV & PDF download
│   │   │
│   │   └── services/
│   │       ├── drive_service.py     # Google Drive API wrapper
│   │       ├── parser_service.py    # PDF/DOCX/TXT text extraction
│   │       ├── llm_service.py       # Gemini summarization
│   │       └── export_service.py    # Report generation
│   │
│   ├── tests/
│   │   ├── conftest.py              # Shared fixtures
│   │   ├── test_parser.py
│   │   ├── test_llm.py
│   │   └── test_export.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pytest.ini
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Root component + state management
│   │   ├── main.jsx                 # React entry point
│   │   ├── index.css                # Tailwind + custom animations
│   │   │
│   │   ├── api/
│   │   │   └── client.js            # Fetch wrapper for backend API
│   │   │
│   │   └── components/
│   │       ├── Header.jsx           # App header + auth status
│   │       ├── ConnectCard.jsx      # Google sign-in CTA
│   │       ├── HomeView.jsx         # Folder ID input + submit
│   │       ├── ResultsView.jsx      # Summary table + stats + export
│   │       ├── Alert.jsx            # Error/info/success alerts
│   │       └── Spinner.jsx          # Loading indicator
│   │
│   ├── Dockerfile
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── nginx/
│   └── nginx.conf                   # Reverse proxy configuration
│
├── docker-compose.yml               # Full-stack orchestration
├── docker-compose.test.yml          # Test runner orchestration
├── .env.example                     # Environment template (single source of truth)
├── .gitignore
└── README.md
```

---

## 🔧 Configuration

All configuration is via environment variables (loaded from `.env`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | ✅ | — | OAuth2 web client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | — | OAuth2 web client secret |
| `GOOGLE_REDIRECT_URI` | — | `http://localhost:8080/api/auth/callback` | Must match Google Console |
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key |
| `GEMINI_MODEL` | — | `gemini-2.5-flash` | Gemini model identifier |
| `SECRET_KEY` | ✅ | — | Session cookie signing key |
| `DEFAULT_FOLDER_ID` | — | *(empty)* | Pre-fill folder ID in UI |
| `MAX_FILES_PER_RUN` | — | `20` | Max documents per run |
| `MAX_FILE_SIZE_MB` | — | `10` | Skip files larger than this |
| `LLM_CONCURRENCY` | — | `5` | Parallel Gemini API calls |
| `SUMMARIZE_COOLDOWN_SECONDS` | — | `30` | Rate limit between runs |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/auth/login` | Start OAuth2 flow |
| `GET` | `/api/auth/callback` | OAuth2 redirect handler |
| `GET` | `/api/auth/status` | Check auth status + email |
| `POST` | `/api/auth/logout` | Clear session |
| `GET` | `/api/drive/files?folder_id=...` | List files in a Drive folder |
| `POST` | `/api/summarize` | Run full summarization pipeline |
| `GET` | `/api/results` | Retrieve cached results |
| `GET` | `/api/export/csv` | Download CSV report |
| `GET` | `/api/export/pdf` | Download PDF report |

---

## 🛡️ Security

- OAuth tokens stored in **signed, HttpOnly session cookies**
- Drive API scope limited to **read-only** (`drive.readonly`)
- File downloads happen **server-side** (credentials never exposed to browser)
- `client_secret.json` is **gitignored**
- Per-session **rate limiting** on the summarization endpoint
- Security headers via Nginx: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`

---

## 📝 License

This project is licensed under the [Apache License 2.0](LICENSE).
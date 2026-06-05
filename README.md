# 📄 Document Summarizer

> **AI-powered Google Drive document summarizer** — Connect your Google Drive, select a folder, and get concise AI-generated summaries for every PDF, DOCX, TXT, and Google Docs file inside it.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## ✨ Features

- **Google Drive Integration**: Secure sign-in with Google OAuth2 to access your Drive (Read-Only).
- **Multi-format Parsing**: Extracts text from PDFs, DOCX files, TXTs, and Google Docs automatically.
- **AI Summarization**: Generates a neat 5-10 sentence summary for each document using Gemini 2.5 Flash, along with key topics, important numbers, and extracted entities.
- **Downloadable Reports**: Export your results as a clean CSV spreadsheet or a beautifully styled PDF report.
- **Modern UI**: A responsive, fast React interface with real-time feedback.
- **Docker Ready**: Deploy everything with a single command.

---

## 🚀 Step-by-Step Setup Guide to start this system

Follow these steps to get the project running on your local machine.

### Prerequisites
Make sure you have installed on your computer:
1. [Git](https://git-scm.com/downloads)
2. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Must be installed and running!)

---

### Step 1: Clone the Repository
First, download the code to your local machine using your terminal (or command prompt):
```bash
git clone https://github.com/Arnab-009/Assignment_Tech_Exactly.git
cd Assignment_Tech_Exactly
```

### Step 2: Get your Gemini API Key
This app uses Google's Gemini AI to read and summarize documents.
1. Go to [Google AI Studio](https://aistudio.google.com/apikey).
2. Sign in with your Google account.
3. Click **"Create API Key"** and copy the generated string. Keep this safe for Step 4.

### Step 3: Get Google OAuth Credentials
To let the app access your Google Drive, you need to create an OAuth Client ID.
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., name it "DocSummarizer").
3. In the search bar at the top, type **"Google Drive API"** and click **Enable**.
4. Go to **APIs & Services > OAuth consent screen**. 
   - Choose **External** and fill in the required App Name and User Support Email fields. Save and continue.
   - Click Add or Remove Scopes, search for Google Drive API and select `.../auth/drive.readonly`. Save and continue.
   - Under "Test users", click **Add Users** and add your own email address. Save and continue.
5. Go to **APIs & Services > Credentials** on the left sidebar.
6. Click **+ Create Credentials > OAuth client ID**.
   - Application type: **Web application**
   - Name: `DocSummarizer local`
   - Authorized redirect URIs: Click **+ ADD URI** and paste exactly: `http://localhost:8080/api/auth/callback`
7. Click **Create**. A popup will appear with your **Client ID** and **Client Secret**. Keep these handy!

### Step 4: Configure Environment Variables
The application needs your secret keys to run.
1. In the root of the project folder, make a copy of the `.env.example` file and name it `.env`.
   ```bash
   cp .env.example .env
   ```
2. Open the new `.env` file in any text editor (like VS Code, Notepad, or TextEdit).
3. Fill in the keys you collected in Steps 2 and 3 so it looks like this:
   ```env
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GEMINI_API_KEY=your_gemini_api_key_here
   SECRET_KEY=put_any_random_long_string_here_like_abcdef123456
   ```

### Step 5: Start the Application!
With Docker Desktop running in the background, type the following command in your terminal:
```bash
docker compose up --build
```
*Note: The first time you run this, it will take a few minutes to download the necessary files and install dependencies.*

Once the terminal stops scrolling and shows the containers are running, open your web browser and go to:
👉 **[http://localhost:8080](http://localhost:8080)**

**You're done!** Click "Connect Google Drive", authorize your account, select a Google Drive folder from the dropdown, choose a document from the list to summarize, and click the summarize button!

---

## 🛠️ Local Development (Without Docker)

If you want to edit the code and run the app manually without Docker:

**1. Backend (FastAPI)**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy the environment file from the root directory
cp ../.env .env

# Edit backend/.env to use the local React dev server ports:
# GOOGLE_REDIRECT_URI=http://localhost:5173/api/auth/callback
# POST_LOGIN_REDIRECT=http://localhost:5173

uvicorn app.main:app --reload --port 8000
```
*⚠️ **Important**: Because you changed `GOOGLE_REDIRECT_URI` to use port `5173`, you MUST go back to the Google Cloud Console (Step 3) and add `http://localhost:5173/api/auth/callback` to your Authorized Redirect URIs!*

**2. Frontend (React)**
```bash
cd frontend
npm install
npm run dev
# The app will open at http://localhost:5173
```

---

## 🧪 Running Tests
You can run the automated backend test suite using Docker (recommended) or locally.

**Option 1: Using Docker (Easiest)**
```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

**Option 2: Local Environment**
```bash
cd backend
# Make sure your virtual environment is activated
pip install -r requirements-dev.txt
pytest -v
```

---

## 📝 License
This project is licensed under the [Apache License 2.0](LICENSE).
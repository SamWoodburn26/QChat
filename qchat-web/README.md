# QChat Webpage

QChat is a local development setup for the Quinnipiac chatbot experience.

This project includes:
- A React + Vite frontend (`qchat-web`) for the chat UI.
- A Python Azure Functions backend (`qchat-web/src/backend`) that handles `/api/*` requests.
- Ollama for local LLM responses.
- Azurite for local Azure storage emulation (required by current backend settings).

## What Runs in Each Terminal

To run the full app locally, you normally use **3 terminals**:
- `Terminal 1` - Frontend (`npm run dev`)
- `Terminal 2` - Backend Azure Functions (`func start`)
- `Terminal 3` - Local services (Ollama + Azurite)

If all services start correctly:
- Frontend opens at `https://localhost` when certs exist, otherwise `http://localhost:8000`
- Backend runs at `http://localhost:7071`
- Frontend `/api/...` calls are proxied to the backend

---

## Prerequisites (Both OS)

Install these before running:
- Node.js 20+
- npm
- Python 3.12
- Azure Functions Core Tools v4 (`func`)
- Ollama

From the project root:

```bash
cd qchat-web
npm install
```

Backend Python dependencies:

```bash
cd qchat-web/src/backend
pip install -r requirements.txt
```

> Note: `src/backend/local.settings.json` is used by the backend during local development. Do not commit personal or secret credentials.

---

## Mac Setup and Run

### Terminal 1 - Frontend

```bash
cd qchat-web
npm install
npm run dev
```

### Terminal 2 - Backend server (Mac)

```bash
cd qchat-web/src/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
func start
```

### Terminal 3 - Local services (Mac)

Start Ollama (if not already running):

```bash
ollama serve
```

In another tab/window (or after confirming Ollama is already running), start Azurite from project root:

```bash
cd qchat-web
npx azurite --silent --location "./__blobstorage__" --debug "./__blobstorage__/debug.log"
```

Optional model pull (first time only):

```bash
ollama pull mistral:latest
```

---

## Windows Setup and Run (Server Instructions Included)

### Terminal 1 - Frontend

```powershell
cd qchat-web
npm install
```

Optional HTTPS certificate generation (recommended for local HTTPS):

```powershell
npm run cert:generate
```

Start frontend:

```powershell
npm run dev
```

### Terminal 2 - Backend server (Windows)

```powershell
cd qchat-web\src\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
func start
```

### Terminal 3 - Local services (Windows)

Start Ollama:

```powershell
ollama serve
```

Start Azurite from project root:

```powershell
cd qchat-web
npx azurite --silent --location ".\__blobstorage__" --debug ".\__blobstorage__\debug.log"
```

Optional model pull (first time only):

```powershell
ollama pull mistral:latest
```

---

## Quick Health Check

After all terminals are running:
- Open frontend in browser (`https://localhost` or `http://localhost:8000`)
- Confirm backend responds at `http://localhost:7071`
- Send a chat message and verify no backend or Ollama connection errors appear

## Common Issues

- If frontend cannot reach backend, make sure `func start` is running in the backend terminal.
- If responses fail due to model access, make sure Ollama is running and the expected model is pulled.
- If backend logs storage warnings, confirm Azurite is running.

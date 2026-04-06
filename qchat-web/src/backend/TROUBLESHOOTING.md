# QChat backend troubleshooting

cd qchat-web
npm install
npm run cert:generate
npm run dev

cd qchat-web/src/backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
func start

npx azurite --silent --location "C:\Users\tarua1\Documents\QChat\qchat-web\__blobstorage__" --debug "C:\Users\tarua1\Documents\QChat\qchat-web\__blobstorage__\debug.log"


## Virtualenv creation fails on Windows

If you see an error like:

`Unable to copy ... venvlauncher.exe ... to ... .venv\Scripts\python.exe`

use these checks:

- Do not recreate `.venv` while it is active. Run `deactivate` first (or open a new terminal).
- Remove the old env before recreating:
  ```powershell
  Remove-Item -Recurse -Force .venv
  ```
- Create the env with Python 3.12 explicitly:
  ```powershell
  py -3.12 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -V
  ```
- If `py -3.12` is missing, install it:
  ```powershell
  choco install python312 -y
  ```



## "LLM isn't running" / "Could not access LLM"

The chat needs **two** things to be running:

## Frontend over HTTPS

The Vite dev server runs on standard web ports:

- `https://localhost` (port 443) when local cert files exist
- `http://localhost` (port 80) when cert files are missing

using a local OpenSSL certificate setup.

**One-time setup on this machine:**

- Install OpenSSL:
  ```powershell
  choco install openssl.light -y
  ```
- Generate and trust the local dev certificate:
  ```powershell
  cd qchat-web
  npm run cert:generate
  ```

This creates `.cert/localhost-cert.pem` and `.cert/localhost-key.pem`, and trusts the certificate in the current user's Windows certificate store.

**How HTTPS works in dev:**

- The frontend is served from `https://localhost`.
- Browser calls to `/api/...` stay on the same HTTPS origin.
- Vite proxies those `/api` requests to the Azure Functions backend at `http://localhost:7071`.

This avoids browser mixed-content errors while keeping the local Functions host on HTTP.

### 1. Backend (Azure Functions)

The frontend calls `/api/chat` in development and Vite proxies that to `http://localhost:7071` (or `SERVER_URL` from `local.settings.json`). If the backend isn’t running, you’ll see a connection error and the message about the LLM.

**Fix:**

- From the **backend** folder (where `host.json` and `local.settings.json` live), run:
  ```bash
  func start
  ```
- Confirm the terminal shows the function app running and that `api/chat` is listed.
- If you use a different port, set `SERVER_URL` in the frontend (e.g. in `local.settings.json` or env) to match (e.g. `http://localhost:7071`).

### 2. Ollama (the actual LLM)

The backend uses **Ollama** for the LLM. It connects to the URL in `OLLAMA_URL` (in `local.settings.json` or env).

**If you use the default/local Ollama:**

- Install [Ollama](https://ollama.com) and start it (it usually runs as a service).
- Pull the model your app expects, e.g.:
  ```bash
  ollama pull mistral:latest
  ```
  (or `mistral-small3.2:latest` if that’s what’s in `OLLAMA_MODEL`).
- In `local.settings.json`, either omit `OLLAMA_URL` (so it defaults to `http://127.0.0.1:11434`) or set:
  ```json
  "OLLAMA_URL": "http://127.0.0.1:11434"
  ```

**If you use a remote Ollama via ngrok** (e.g. `OLLAMA_URL": "https://....ngrok-free.dev"`):

- On the machine where Ollama is running, start Ollama and then start ngrok pointing at port 11434, e.g.:
  ```bash
  ngrok http 11434
  ```
- Update `OLLAMA_URL` in `local.settings.json` to the current ngrok URL (it changes each time unless you have a fixed domain).
- Ensure the model in `OLLAMA_MODEL` is pulled on that Ollama instance.

### Quick checks

- **Backend reachable:** Open `http://localhost:7071` (or your `SERVER_URL`) in a browser; you should get some response, not “connection refused”.
- **Ollama reachable:** If using local Ollama, open `http://127.0.0.1:11434` in a browser; you should see Ollama’s API (e.g. “Ollama is running”).

If the backend runs but Ollama is down or unreachable, the backend may still return 200 with a generic “I don’t know” reply. Check the backend terminal for Python errors mentioning connection refused or timeouts to Ollama.


## "Unable to access AzureWebJobsStorage"

If the backend starts but repeatedly logs:

`Unable to access AzureWebJobsStorage`

your `local.settings.json` is pointing at local development storage:

```json
"AzureWebJobsStorage": "UseDevelopmentStorage=true"
```

That means **Azurite** must be running locally.

### Windows command

From the project root, run this in a separate terminal:

```powershell
Import-Module $env:ChocolateyInstall\helpers\chocolateyProfile.psm1
refreshenv
npx azurite --silent --location "C:\Users\tarua1\Documents\QChat\qchat-web\__blobstorage__" --debug "C:\Users\tarua1\Documents\QChat\qchat-web\__blobstorage__\debug.log"
```

If `npx` is not available in that terminal yet, close and reopen PowerShell, or run the `Import-Module` and `refreshenv` lines first.

### What to expect

- Azurite should listen on the default local storage ports (`10000`, `10001`, `10002`).
- Once it is running, the Azure storage health warnings should stop.
- Your HTTP functions may still work without Azurite, but the Functions host will continue reporting the app as unhealthy.

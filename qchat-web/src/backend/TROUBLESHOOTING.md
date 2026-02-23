# QChat backend troubleshooting

## "LLM isn't running" / "Could not access LLM"

The chat needs **two** things to be running:

### 1. Backend (Azure Functions)

The frontend calls `http://localhost:7071/api/chat` (or `SERVER_URL` from `local.settings.json`). If the backend isn’t running, you’ll see a connection error and the message about the LLM.

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

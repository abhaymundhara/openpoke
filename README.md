# OpenPoke 🌴

OpenPoke is a simplified, open-source take on [Interaction Company’s](https://interaction.co/about) [Poke](https://poke.com/) assistant—built to show how a multi-agent orchestration stack can feel genuinely useful. It keeps the handful of things Poke is great at (email triage, reminders, and persistent agents) while staying easy to spin up locally.

- Multi-agent FastAPI backend that mirrors Poke's interaction/execution split, powered by a local [Ollama](https://ollama.com/) runtime.
- Gmail tooling via [Composio](https://composio.dev/) for drafting/replying/forwarding without leaving chat.
- Trigger scheduler and background watchers for reminders and "important email" alerts.
- Next.js web UI that proxies everything through the shared `.env`, so plugging in API keys is the only setup.

## About this fork

This project extends [shlokkhemani/OpenPoke](https://github.com/shlokkhemani/OpenPoke) with a locally hosted stack: all agents now call Ollama’s `gemma2:2b` model by default and a macOS iMessage bridge lets conversations flow through native Messages threads. The upstream FastAPI/Next.js foundation remains intact, so the new features slot into the existing architecture without changing the original workflows.

## Requirements
- Python 3.10+
- Node.js 18+
- npm 9+
- [Ollama](https://ollama.com/) with the `gemma2:2b` model available
- macOS (only required for the optional iMessage bridge)

## Quickstart
1. **Clone and enter the repo.**
   ```bash
   git clone https://github.com/<your-org>/openpoke.git
   cd openpoke
   ```
2. **Create a shared env file.** Copy the template and open it in your editor:
   ```bash
   cp .env.example .env
   ```
3. **Fill in `.env` with your Composio credentials (required for Gmail tooling).**
   - Sign in at [composio.dev](https://composio.dev/) and create an API key
   - Set up Gmail integration to obtain the auth config ID
   - Replace the placeholder values for `COMPOSIO_API_KEY` and `COMPOSIO_GMAIL_AUTH_CONFIG_ID`
4. **Install and start Ollama with the default model.**
   ```bash
   # Install Ollama if you do not already have it (macOS example)
   brew install ollama
   ```
   Start the Ollama service in a separate terminal:
   ```bash
   ollama serve
   ```
   Then pull the model used by OpenPoke:
   ```bash
   ollama pull gemma2:2b
   ```
   If Ollama is hosted elsewhere, set `OLLAMA_HOST` in `.env` to the reachable base URL.
5. **(Required) Create and activate a Python 3.10+ virtualenv:**
   ```bash
   # Ensure you're using Python 3.10+
   python3.10 -m venv .venv
   source .venv/bin/activate
   
   # Verify Python version (should show 3.10+)
   python --version
   ```
   On Windows (PowerShell):
   ```powershell
   # Use Python 3.10+ (adjust path as needed)
   python3.10 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   
   # Verify Python version
   python --version
   ```

6. **Install backend dependencies:**
   ```bash
   pip install -r server/requirements.txt
   ```
7. **Install frontend dependencies:**
   ```bash
   npm install --prefix web
   ```
8. **Start the FastAPI server:**
   ```bash
   python -m server.server --reload
   ```
9. **Start the Next.js app (new terminal):**
   ```bash
   npm run dev --prefix web
   ```
10. **(Optional) Run the macOS iMessage bridge.** In another terminal on macOS, point the bridge at the backend:
    ```bash
    python bridges/imessage_proxy.py --server http://localhost:8001/api/v1/bridge/imessage
    ```
    You can set `OPENPOKE_BRIDGE_ENDPOINT`, `OPENPOKE_BRIDGE_POLL`, or `OPENPOKE_BRIDGE_TOKEN` environment variables to adjust the bridge connection.
11. **Connect Gmail for email workflows.** With both services running, open [http://localhost:3000](http://localhost:3000), head to *Settings → Gmail*, and complete the Composio OAuth flow. This step is required for email drafting, replies, and the important-email monitor.

The web app proxies API calls to the Python server using the values in `.env`, so keeping both processes running is required for end-to-end flows.

## Project Layout
- `server/` – FastAPI application and agents
- `web/` – Next.js app
- `server/data/` – runtime data (ignored by git)

## License
MIT — see [LICENSE](LICENSE).

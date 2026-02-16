# Card Game

Backend (Nakama + generation service) and client layout for a unit + equipment card game.

## Repo layout

- **`backend/`** — Server and services
  - **`nakama-module/`** — Go plugin (game contract, RPCs). Build output: `backend/modules/game.so`
  - **`generation-service/`** — Python service (card art + stat generation, drop types, asset serving)
  - **`data/`** — Card templates, drop types (JSON)
  - **`assets/`** — Borders, generated art
  - **`modules/`** — Built `game.so` (loadable by Nakama)
- **`client/`** — Frontend (placeholder)
  - **`app/`** — Shared web app (future: Vite + React/Vue; Capacitor adds `ios/` and `android/` here)
  - **`desktop/`** — Electron wrapper (future)
- **`docker-compose.yml`** — Postgres, Nakama, generation-service (run from repo root)

## Run backend and frontend

From repo root. Ensure `backend/modules/game.so` exists (see [backend/README.md](backend/README.md)).

**Option 1 — One command (recommended for dev):**
```bash
npm install   # once, installs concurrently
npm run dev   # starts Docker (backend) + Vite (frontend) in one terminal; Ctrl+C stops both
```

**Option 2 — Two terminals:**
```bash
# Terminal 1: backend
docker compose up

# Terminal 2: frontend
cd client/app && npm run dev
```

**Option 3 — Backend in background:**
```bash
npm run dev:backend:detach   # Docker in background
cd client/app && npm run dev # frontend in foreground
npm run down                 # when done, stop Docker
```

- **Nakama API:** `http://127.0.0.1:7350` · **Console:** `http://127.0.0.1:8080` · **Generation:** `http://127.0.0.1:8000`
- **App:** URL printed by Vite (e.g. `http://localhost:5173`)

Details: [backend/README.md](backend/README.md), [backend/generation-service/README.md](backend/generation-service/README.md).

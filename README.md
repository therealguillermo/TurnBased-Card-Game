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

## Run backend

From repo root:

1. Build the Go plugin (see [backend/README.md](backend/README.md)) so `backend/modules/game.so` exists.
2. `docker-compose up -d`
3. Nakama API: `http://127.0.0.1:7350` · Console: `http://127.0.0.1:8080` · Generation: `http://127.0.0.1:8000`

Details: [backend/README.md](backend/README.md), [backend/generation-service/README.md](backend/generation-service/README.md).

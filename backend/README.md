# Backend

Nakama (Go plugin) + generation service (Python). All backend code and docs live here.

## Layout

- **`nakama-module/`** — Go plugin (game contract, RPCs). Build output goes to **`modules/game.so`**.
- **`generation-service/`** — Python service: card art + stat generation, drop types, asset serving (port 8000).
- **`data/`** — Card templates, drop types (JSON).
- **`assets/`** — Borders, generated art (mounted into generation-service).
- **`modules/`** — Built `game.so` (Nakama loads this).
- **`docs/`** — Backend documentation:
  - [README_NAKAMA_BACKEND.md](docs/README_NAKAMA_BACKEND.md) — Build plugin, run Nakama, example RPCs.
  - [GAME_CONTRACT_SCHEMAS.md](docs/GAME_CONTRACT_SCHEMAS.md) — JSON shapes for storage and RPCs.
  - [IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md) — What’s implemented, contract constraints.
  - [NAKAMA_CAPABILITIES.md](docs/NAKAMA_CAPABILITIES.md) — What Nakama does vs generation service.
  - [future_rules.txt](docs/future_rules.txt) — Future game rules / design notes.

## Run (from repo root)

1. Build the Go plugin so `backend/modules/game.so` exists (see [docs/README_NAKAMA_BACKEND.md](docs/README_NAKAMA_BACKEND.md)).
2. `docker-compose up -d` (from repo root).
3. Nakama: `http://127.0.0.1:7350` · Console: `http://127.0.0.1:8080` · Generation: `http://127.0.0.1:8000`.

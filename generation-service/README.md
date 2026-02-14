# Card Generation Service

Python container that generates card **art** and **stats** for units and items, and serves assets (art and borders) to the game and Nakama.

## Run with Docker Compose

From the project root:

```bash
docker-compose up -d
```

The generation service listens on **port 8000**. Nakama can call it at `http://generation-service:8000` from inside the same Docker network.

## Responsibilities

- **Art generation:** Pixel art for units and items (placeholder or AI), saved under `assets/art/`.
- **Stats generation (planned):** Generate stats for new units and items (e.g. from AI or templates).
- **Serving:** Expose generated art and border images via HTTP so clients and Nakama can use them.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/assets/art/{templateId}.png` | Serve generated art (404 if not generated) |
| GET | `/assets/borders/{rarity}.png` | Serve border (rarity: Common, Uncommon, Rare, Epic, Legendary, Mythic) |
| POST | `/generate/{templateId}` | Generate art for a template (optional `?force=true` to regenerate) |
| GET | `/templates` | List template IDs from the catalog |
| POST | `/generate/unit` | Generate unit stats (body: `rarity`, optional `templateId`, `displayName`, `archetype`) |
| POST | `/generate/item` | Generate item stats (body: `rarity`, `slot`, optional `templateId`, `displayName`) |

Stat generation uses prompts that adhere strictly to `stat_generation_rules.txt`. With `OPENAI_API_KEY` set, the service uses the AI; otherwise it returns valid placeholder stats within the same budget and rules.

## Generating art

- **Placeholder mode (default):** No API key needed. `POST /generate/warrior_01` creates a simple colored PNG (1024×1024) and saves it under `assets/art/`.
- **AI mode:** Set `OPENAI_API_KEY` in the environment (e.g. in `docker-compose.yml` under `generation-service.environment`) to use AI generation when implemented. Until then, the service still uses placeholders.

## Data and assets

- **Catalog:** `data/card-templates.json` in the repo root. Add entries with `templateId`, `type` (unit/item), `displayName`, `promptDescription`, and for items `slot`.
- **Borders:** `assets/borders/{Rarity}Border.png` (e.g. `CommonBorder.png`). Mounted into the container.
- **Generated art:** Written to `assets/art/{templateId}.png` via the mounted volume.

## Example

```bash
# Generate art for a template
curl -X POST "http://localhost:8000/generate/warrior_01"

# Fetch the image
curl -o warrior_01.png "http://localhost:8000/assets/art/warrior_01.png"

# Serve a border
curl -o CommonBorder.png "http://localhost:8000/assets/borders/Common.png"

# Generate unit stats (placeholder if no API key)
curl -X POST "http://localhost:8000/generate/unit" \
  -H "Content-Type: application/json" \
  -d '{"rarity": "Common", "templateId": "warrior_01"}'

# Generate item stats
curl -X POST "http://localhost:8000/generate/item" \
  -H "Content-Type: application/json" \
  -d '{"rarity": "Uncommon", "slot": "Weapon", "templateId": "sword_01"}'
```

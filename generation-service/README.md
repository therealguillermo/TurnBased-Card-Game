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
| POST | `/generate/{templateId}` | Generate art (optional body: `displayName`, `promptDescription` for non-catalog templates; `?force=true` to regenerate) |
| GET | `/templates` | List template IDs from the catalog |
| POST | `/generate/unit` | Generate **any** unit (body: `rarity`, optional `templateId`, `displayName`, `archetype`, `allowedArchetypes`) |
| POST | `/generate/item` | Generate **any** item (body: `rarity`, `slot` or `allowedSlots`, optional `templateId`, `displayName`) |
| GET | `/drop-types` | List drop type definitions (rarity/unit/item/slot controls) |
| POST | `/generate/drop` | Generate from a drop type (body: `dropTypeId`, optional `rarityOverride`) |

Stat generation uses prompts that adhere strictly to `stat_generation_rules.txt`. The AI can generate any unit or item type (no catalog required). Responses include `suggestedTemplateId` for art and Nakama. With `OPENAI_API_KEY` set the service uses the AI; otherwise it returns valid placeholder stats.

## Generating art

- **Placeholder mode (default):** No API key needed. `POST /generate/warrior_01` creates a simple colored PNG (1024×1024) and saves it under `assets/art/`.
- **AI mode:** Set `OPENAI_API_KEY` in the environment (e.g. in `docker-compose.yml` under `generation-service.environment`) to use AI generation when implemented. Until then, the service still uses placeholders.

## Type controls and drop types

- **Unit controls:** `allowedArchetypes` restricts generation to Melee Specialist, Ranger, Mage, Monster Brute, or Hybrid.
- **Item controls:** `slot` (Weapon/Armor/Relic) or `allowedSlots` (pick one at random).
- **Drop types:** `data/drop-types.json` defines drop kinds (e.g. rare_unit_drop, legendary_item_drop, weapon_drop, ranged_unit_drop). Each has `type` (unit | item | any), `rarities`, `archetypes` (units), and `slots` (items). User opens "rare unit drop" → `POST /generate/drop` with `dropTypeId: "rare_unit_drop"` → get a generated unit/item with `suggestedTemplateId` for art and Nakama.

## Data and assets

- **Catalog:** `data/card-templates.json` — optional; AI can generate any unit/item without a catalog entry.
- **Drop types:** `data/drop-types.json` — controls which rarities, unit archetypes, and item slots can be generated per drop kind.
- **Borders:** `assets/borders/{Rarity}Border.png`. Mounted into the container.
- **Generated art:** Written to `assets/art/{templateId}.png`. For AI-generated templates not in the catalog, call `POST /generate/{templateId}` with body `{ "displayName": "...", "promptDescription": "..." }`.

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

# Generate item stats (or use allowedSlots to pick slot at random)
curl -X POST "http://localhost:8000/generate/item" \
  -H "Content-Type: application/json" \
  -d '{"rarity": "Uncommon", "slot": "Weapon", "templateId": "sword_01"}'

# Generate from a drop type (e.g. rare unit drop, legendary item drop)
curl -X POST "http://localhost:8000/generate/drop" \
  -H "Content-Type: application/json" \
  -d '{"dropTypeId": "rare_unit_drop"}'

# List drop types
curl "http://localhost:8000/drop-types"
```

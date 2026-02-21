# Nakama Backend — Game Contract

Backend enforces the locked game contract: 7 unit stats, 3 equipment slots (weapon, armor, relic), 6 rarities, items with bonuses only, no combat/cards/drops. All state changes go through RPCs; client cannot write to storage directly.

---

## How to run locally

### 1. Build the Go plugin

The plugin must be built so it matches Nakama’s runtime: **same Go version** (go1.23.3) and **same libc**. The Nakama 3.25 image is Debian/glibc; building on Alpine/musl produces a `.so` that needs `libc.musl-x86_64.so.1` and will fail to load. The Dockerfile uses **golang:1.23.3-bookworm** so the plugin links against glibc.

From the **project root**:

```bash
mkdir -p backend/modules
docker build -f backend/nakama-module/Dockerfile -t game-plugin ./backend/nakama-module
docker run --rm -v "$(pwd)/backend/modules:/out" game-plugin
```

Then start Nakama. Ensure `backend/modules/game.so` exists before `docker compose up`.

### 2. Start Nakama with Docker Compose

```bash
docker-compose up -d
```

- **Nakama API**: `http://127.0.0.1:7350`
- **Console**: `http://127.0.0.1:8080` (admin / password)
- Runtime path is set to `/local/backend/modules` (project root is mounted at `/local`).

### 3. (Optional) Admin secret for `rpc_grant_item`

To use the admin-only `rpc_grant_item` RPC, set an env in `docker-compose.yml`:

```yaml
ADMIN_SECRET: "your-secret"
```

Then pass `"adminSecret": "your-secret"` in the RPC payload.

---

## Example client calls

All RPCs (except `rpc_grant_item` when using `targetUserId`) require an authenticated session. Use the same token for the `Authorization: Bearer <token>` header in HTTP or the session when using the Nakama client.

### Authenticate (get session token)

```bash
# Device auth (returns token)
curl -s -X POST "http://127.0.0.1:7350/v2/account/authenticate/device?create=true" \
  -H "Authorization: Bearer defaultkey" \
  -H "Content-Type: application/json" \
  -d '{"id": "my-device-id"}'
```

Save the `token` from the response for the next calls.

### 1. Get state

```bash
TOKEN="<paste-token-here>"
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_get_state" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Returns: `profile`, `wallet`, `inventorySummary` (itemsCount, unitsCount), `units` (full list).

### 2. Create unit

```bash
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_create_unit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "templateId": "warrior_01",
    "rarity": "Rare",
    "stats": {
      "hp_max": 100, "stamina_max": 50, "mana_max": 20,
      "melee": 10, "ranged": 2, "magic": 0, "maneuver": 5
    }
  }'
```

### 3. Grant item (admin only)

Requires `adminSecret` in payload (and `ADMIN_SECRET` set in server env). Optional `targetUserId` to grant to another user.

```bash
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_grant_item" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "adminSecret": "your-secret",
    "templateId": "sword_01",
    "rarity": "Uncommon",
    "slot": "Weapon",
    "bonuses": { "melee": 3 },
    "passive": "Life steal"
  }'
```

### 4. Equip / unequip item

```bash
# Equip
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_equip_item" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unitInstanceId": "<unit-instance-id>",
    "slotName": "weapon",
    "itemInstanceId": "<item-instance-id>"
  }'

# Unequip (pass null for itemInstanceId)
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_equip_item" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unitInstanceId": "<unit-instance-id>",
    "slotName": "weapon",
    "itemInstanceId": null
  }'
```

### 5. Compute final stats

```bash
curl -s -X POST "http://127.0.0.1:7350/v2/rpc/rpc_compute_final_stats" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"unitInstanceId": "<unit-instance-id>"}'
```

Returns: `baseStats`, `finalStats` (base + sum of equipped item bonuses).

---

## Error codes / messages

- **3 (InvalidArgument)**: Missing/invalid payload, invalid stat key, invalid rarity/slot, item_slot_mismatch, etc.
- **5 (NotFound)**: unit_not_found, item_not_found.
- **7 (PermissionDenied)**: user_id_required, admin_only.

Server returns these as gRPC/HTTP error code and message string.

---

## JSON schemas

See [GAME_CONTRACT_SCHEMAS.md](./GAME_CONTRACT_SCHEMAS.md).

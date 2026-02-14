# Implementation Summary — Card Game Backend

**Purpose:** Handoff document for another AI to discuss new implementations. Describes what exists and the locked game contract.

---

## 1. Project overview

- **What it is:** A Nakama-backed game server for a **unit + equipment** system (no combat, cards, or drops yet). Players have a profile, wallet (gold), and an inventory of **items** (equippable) and **units** (characters with 3 equipment slots).
- **Stack:** Nakama 3.25 (Go runtime), PostgreSQL, Docker Compose. Backend is a **Go plugin** (`backend/nakama-module/`) built to `backend/modules/game.so` and loaded by Nakama.
- **Client:** No game client in this repo. All interaction is via Nakama HTTP/gRPC (authenticate → call RPCs). Optional Python backend for AI/image generation is described in docs but not implemented.

---

## 2. Locked game contract (design constraints)

The backend enforces a fixed schema. New features must respect these:

| Concept | Allowed values |
|--------|-----------------|
| **Stats (exactly 7)** | `hp_max`, `stamina_max`, `mana_max`, `melee`, `ranged`, `magic`, `maneuver` |
| **Rarity (6)** | `Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`, `Mythic` |
| **Item slot (3)** | `Weapon`, `Armor`, `Relic` |
| **Equipment slot names (3)** | `weapon`, `armor`, `relic` (lowercase in payloads/equipment map) |

- **Units:** Have `stats` (all 7 keys required) and `equipment` (weapon, armor, relic → item instance ID or `""`).
- **Items:** Have `bonuses` (any subset of the 7 stat keys), `slot` (Weapon/Armor/Relic), optional `passive` string. No other fields in bonuses.
- **Storage:** Server-write only (permissions 0,0). Client cannot read/write storage directly; all mutations go through RPCs.

---

## 3. Storage model (per user)

- **Collections/keys:**  
  - `player/profile` → key `"profile"`  
  - `player/wallet` → key `"wallet"`  
  - `player/inventory` → key `"inventory"`

- **Profile:** `username`, `createdAt` (RFC3339). Created on first use; username defaulted from user ID if missing.
- **Wallet:** `gold` (number). Initialized to 0.
- **Inventory:** Single JSON object: `items` (map instanceId → ItemInstance), `units` (map instanceId → UnitInstance). Instance IDs are server-generated (hex + timestamp).

---

## 4. RPCs implemented

| RPC | Auth | Purpose |
|-----|------|--------|
| `rpc_get_state` | Required | Returns profile, wallet, inventorySummary (counts), and full list of units. Ensures profile/wallet/inventory exist. |
| `rpc_create_unit` | Required | Create a unit with given templateId, rarity, and full 7-key stats. Returns the new UnitInstance. |
| `rpc_grant_item` | Admin only | Grant an item (templateId, rarity, slot, bonuses, optional passive). Requires `adminSecret` in payload matching env `ADMIN_SECRET`. Optional `targetUserId`. |
| `rpc_equip_item` | Required | Equip or unequip: unitInstanceId, slotName (weapon/armor/relic), itemInstanceId (string or null). Validates item exists and item.Slot matches slotName. |
| `rpc_compute_final_stats` | Required | For a unit: returns baseStats and finalStats (base + sum of equipped item bonuses). |

All RPCs (except `rpc_grant_item` when using `targetUserId` without session) require an authenticated user. Errors use Nakama codes: **3** InvalidArgument, **5** NotFound, **7** PermissionDenied.

---

## 5. Code layout

- **`backend/nakama-module/contract.go`** — Constants and validators: collection/key names, `AllowedStats`, `AllowedRarities`, `AllowedSlots`, `EquipmentSlotKeys`, and `isAllowed*` helpers.
- **`backend/nakama-module/main.go`** — Structs (Profile, Wallet, ItemInstance, UnitInstance, Inventory), storage helpers (read/write with 0,0 permissions), `ensureProfileAndWallet` (load or create profile/wallet/inventory), validation (`validateUnitStats`, `validateBonuses`), and the five RPC handlers. `InitModule` registers all RPCs.
- **`backend/modules/`** — Target for built plugin: `game.so`. Nakama loads this from `NAKAMA_RUNTIME_PATH` (Docker: `/local/backend/modules`).
- **`docker-compose.yml`** — Postgres 15 + Nakama 3.25 + generation-service; project root mounted at `/local`; ports 7349, 7350, 8080 (console), 8000 (generation).

---

## 6. Notable implementation details

- **Idempotent first load:** `ensureProfileAndWallet` is used by every RPC that touches user state; it creates profile/wallet/inventory if missing, then returns in-memory structs. All writes go through the same storage write path.
- **Instance IDs:** Generated with `generateInstanceId()` (8 random bytes hex + `-` + Unix nano). Used for both items and units.
- **Equip validation:** Item’s `slot` (Weapon/Armor/Relic) must match the request’s `slotName` (weapon/armor/relic); case differs by design.
- **Wallet:** Stored and returned; no RPC currently modifies `gold` (ready for future economy).
- **rpc_get_state:** Does not return full item list; only `inventorySummary` (itemsCount, unitsCount) and full `units` array. Items are fetched implicitly via unit equipment or would require a new RPC for “list my items.”

---

## 7. What is not implemented

- **Combat / battles** — No match type, no damage, no turns.
- **Cards** — NAKAMA_CAPABILITIES.md describes a card-game vision; current contract is units + equipment items only.
- **Drops / loot / rewards** — No flow that grants items or gold outside `rpc_grant_item` (admin).
- **Client** — No Unity, web, or other client in repo; only backend + docs.
- **Python/AI backend** — Documented as future for AI card generation and external APIs; not present.
- **Listing items** — No RPC that returns full `items` map; only counts and units.
- **Gold spend/source** — Wallet exists but no RPCs change gold.

---

## 8. How to run and extend

- **Build plugin:** From repo root, use Heroic Labs plugin builder (see README_NAKAMA_BACKEND.md) or build Go plugin with same Go version as Nakama (e.g. Go 1.21 for 3.25), output `backend/modules/game.so`.
- **Run:** `docker-compose up -d`. API: `http://127.0.0.1:7350`. Console: `http://127.0.0.1:8080` (admin/password).
- **New implementations:** Keep storage and RPC shapes within GAME_CONTRACT_SCHEMAS.md; add new RPCs in `main.go` and register in `InitModule`; add new validation in `contract.go` if new enums or keys are introduced. For new features (e.g. combat), prefer new RPCs and/or Nakama match handlers rather than changing existing storage shapes.

---

## 9. Reference files

- **GAME_CONTRACT_SCHEMAS.md** — Full JSON shapes for storage and every RPC payload/response.
- **README_NAKAMA_BACKEND.md** — Run instructions, example `curl` for auth and each RPC, error codes.
- **NAKAMA_CAPABILITIES.md** — High-level split: Nakama for storage/auth/realtime, Python for AI/external APIs.

Use this summary plus GAME_CONTRACT_SCHEMAS.md when discussing new implementations (e.g. combat, items list RPC, economy, or a client) so the other AI stays within the existing contract and knows what’s already there.

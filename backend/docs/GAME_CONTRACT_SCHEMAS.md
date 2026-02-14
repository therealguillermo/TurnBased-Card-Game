# JSON schemas (game contract)

All storage and RPC payloads/response shapes used by the Nakama backend.

---

## Storage collections (per user)

- **player/profile** — key: `"profile"`
- **player/wallet** — key: `"wallet"`
- **player/inventory** — key: `"inventory"`

Storage is server-write only (permissions 0,0). Client cannot read/write these directly.

---

## Profile

```json
{
  "username": "string",
  "createdAt": "string (RFC3339)"
}
```

---

## Wallet

```json
{
  "gold": 0
}
```

---

## ItemInstance

```json
{
  "instanceId": "string (server-generated)",
  "templateId": "string",
  "rarity": "Common | Uncommon | Rare | Epic | Legendary | Mythic",
  "slot": "Weapon | Armor | Relic",
  "bonuses": {
    "hp_max": 0,
    "stamina_max": 0,
    "mana_max": 0,
    "melee": 0,
    "ranged": 0,
    "magic": 0,
    "maneuver": 0
  },
  "passive": "string (optional)",
  "createdAt": "string (RFC3339)"
}
```

Only the 7 stat keys may appear in `bonuses`; any subset is allowed.

---

## UnitInstance

```json
{
  "instanceId": "string (server-generated)",
  "templateId": "string",
  "rarity": "Common | Uncommon | Rare | Epic | Legendary | Mythic",
  "stats": {
    "hp_max": 0,
    "stamina_max": 0,
    "mana_max": 0,
    "melee": 0,
    "ranged": 0,
    "magic": 0,
    "maneuver": 0
  },
  "equipment": {
    "weapon": "itemInstanceId or \"\"",
    "armor": "itemInstanceId or \"\"",
    "relic": "itemInstanceId or \"\""
  }
}
```

`stats` must contain exactly these 7 keys. `equipment` has exactly these 3 keys.

---

## Inventory (single storage object)

```json
{
  "items": {
    "<instanceId>": { "<ItemInstance>" }
  },
  "units": {
    "<instanceId>": { "<UnitInstance>" }
  }
}
```

---

## RPC payloads and responses

### rpc_get_state

- **Payload:** `{}`
- **Response:**
```json
{
  "profile": { "<Profile>" },
  "wallet": { "<Wallet>" },
  "inventorySummary": {
    "itemsCount": 0,
    "unitsCount": 0
  },
  "units": [ { "<UnitInstance>" }, ... ]
}
```

### rpc_create_unit

- **Payload:**
```json
{
  "templateId": "string",
  "rarity": "Common | Uncommon | Rare | Epic | Legendary | Mythic",
  "stats": {
    "hp_max": 0, "stamina_max": 0, "mana_max": 0,
    "melee": 0, "ranged": 0, "magic": 0, "maneuver": 0
  }
}
```
- **Response:** `{ "unit": { "<UnitInstance>" } }`

### rpc_grant_item (admin only)

- **Payload:**
```json
{
  "adminSecret": "string",
  "templateId": "string",
  "rarity": "Common | Uncommon | Rare | Epic | Legendary | Mythic",
  "slot": "Weapon | Armor | Relic",
  "bonuses": { "<subset of 7 stat keys>": 0 },
  "passive": "string (optional)",
  "targetUserId": "string (optional, default: current user)"
}
```
- **Response:** `{ "item": { "<ItemInstance>" } }`

### rpc_equip_item

- **Payload:**
```json
{
  "unitInstanceId": "string",
  "slotName": "weapon | armor | relic",
  "itemInstanceId": "string or null"
}
```
`itemInstanceId: null` = unequip that slot.
- **Response:** `{ "unit": { "<UnitInstance>" } }`

### rpc_compute_final_stats

- **Payload:** `{ "unitInstanceId": "string" }`
- **Response:**
```json
{
  "unitInstanceId": "string",
  "baseStats": { "<stats object>" },
  "finalStats": { "<stats object (base + sum of equipped item bonuses)>" }
}
```

---

## Allowed enums

- **Stats (exactly 7):** `hp_max`, `stamina_max`, `mana_max`, `melee`, `ranged`, `magic`, `maneuver`
- **Rarity (6):** `Common`, `Uncommon`, `Rare`, `Epic`, `Legendary`, `Mythic`
- **Item slot (3):** `Weapon`, `Armor`, `Relic`
- **Equipment slot name (3):** `weapon`, `armor`, `relic`

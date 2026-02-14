"""
Stat generation for units and items. Prompts adhere strictly to stat_generation_rules.txt.
Supports any unit/item type (no catalog required); type controls via allowedArchetypes / allowedSlots.
"""
import json
import os
import re
import secrets
from pathlib import Path

# Game contract constants (must match nakama-module/contract.go)
RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")
SLOTS = ("Weapon", "Armor", "Relic")
STAT_KEYS = ("hp_max", "stamina_max", "mana_max", "melee", "ranged", "magic", "maneuver")

# From rules: unit archetypes (for type controls)
UNIT_ARCHETYPES = ("Melee Specialist", "Ranger", "Mage", "Monster Brute", "Hybrid")

# From rules: unit rarity budget range (min, max inclusive)
UNIT_BUDGET_RANGES = {
    "Common": (12, 14),
    "Uncommon": (15, 18),
    "Rare": (19, 23),
    "Epic": (24, 29),
    "Legendary": (30, 36),
    "Mythic": (37, 45),
}

# From rules: item rarity budget range
ITEM_BUDGET_RANGES = {
    "Common": (2, 2),
    "Uncommon": (3, 4),
    "Rare": (5, 6),
    "Epic": (7, 9),
    "Legendary": (10, 13),
    "Mythic": (14, 18),
}

# Approved modifiers (rules section 9)
LEGENDARY_MODIFIERS = (
    "MOD_FREE_FIRST_ATTACK",
    "MOD_REFUND_RESOURCE_ON_ACTION",
    "MOD_GAIN_RESOURCE_ON_KILL",
    "MOD_BONUS_DAMAGE_FIRST_ACTION",
    "MOD_EXECUTE_LOW_HP",
    "MOD_ARMOR_PIERCE",
    "MOD_APPLY_STATUS_ON_HIT",
    "MOD_HEAL_ON_HIT",
    "MOD_SHIELD_COMBAT_START",
    "MOD_DAMAGE_REDUCTION_LOW_HP",
)
MYTHIC_MODIFIERS = (
    "MOD_SECOND_ACTION_EACH_TURN",
    "MOD_HP_INSTEAD_OF_RESOURCE",
    "MOD_CONVERT_RESOURCE_TO_STAT",
    "MOD_HIGHEST_STAT_APPLIES",
    "MOD_CHEAT_DEATH_ONCE",
    "MOD_GAIN_STAT_ON_ACTION",
)


def suggest_template_id(name: str) -> str:
    """Produce a stable templateId from a name (for AI-generated units/items not in catalog)."""
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "gen").lower()).strip("_") or "gen"
    return f"{slug}_{secrets.token_hex(3)}"


def load_rules(rules_path: str) -> str:
    """Load the full stat generation rules text."""
    path = Path(rules_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    return path.read_text(encoding="utf-8").strip()


def build_unit_prompt(
    rarity: str,
    *,
    template_id: str | None = None,
    display_name: str | None = None,
    archetype: str | None = None,
    allowed_archetypes: list[str] | None = None,
) -> str:
    """Build the user prompt for unit generation. Rules text is the system prompt."""
    if rarity not in RARITIES:
        raise ValueError(f"Invalid rarity: {rarity}")
    parts = [
        f"Generate exactly one UNIT. Rarity: {rarity}.",
    ]
    if template_id or display_name:
        parts.append(f"Use for name/flavor: templateId={template_id or 'any'}, displayName={display_name or 'any'}.")
    if archetype:
        parts.append(f"Archetype (MUST use this one): {archetype}.")
    elif allowed_archetypes:
        valid = [a for a in allowed_archetypes if a in UNIT_ARCHETYPES]
        if valid:
            parts.append(f"Archetype MUST be exactly one of: {', '.join(valid)}.")
        else:
            parts.append("Choose exactly ONE archetype from: Melee Specialist, Ranger, Mage, Monster Brute, Hybrid.")
    else:
        parts.append("Choose exactly ONE archetype from: Melee Specialist, Ranger, Mage, Monster Brute, Hybrid.")
    parts.append(
        "Respond with ONLY a single JSON object matching the Unit output format in section 10 (Output Format). "
        "No markdown code fences, no explanation, no other text."
    )
    return " ".join(parts)


def build_item_prompt(
    rarity: str,
    slot: str,
    *,
    template_id: str | None = None,
    display_name: str | None = None,
) -> str:
    """Build the user prompt for item generation. Rules text is the system prompt."""
    if rarity not in RARITIES:
        raise ValueError(f"Invalid rarity: {rarity}")
    if slot not in SLOTS:
        raise ValueError(f"Invalid slot: {slot}")
    parts = [
        f"Generate exactly one ITEM. Rarity: {rarity}. Slot: {slot}.",
    ]
    if template_id or display_name:
        parts.append(f"Use for name/flavor: templateId={template_id or 'any'}, displayName={display_name or 'any'}.")
    parts.append(
        "Respond with ONLY a single JSON object matching the Item output format in section 10 (Output Format). "
        "Use modifier: null if rarity is Common, Uncommon, Rare, or Epic. "
        "No markdown code fences, no explanation, no other text."
    )
    return " ".join(parts)


def _compute_unit_budget(stats: dict) -> float:
    """Compute total budget from stats (rules formula)."""
    melee = stats.get("melee", 0)
    ranged = stats.get("ranged", 0)
    magic = stats.get("magic", 0)
    maneuver = stats.get("maneuver", 0)
    stamina = stats.get("stamina_max", 0)
    mana = stats.get("mana_max", 0)
    hp = stats.get("hp_max", 0)
    return (melee + ranged + magic + maneuver) + stamina + mana + (hp / 3.0)


def _compute_item_budget(bonuses: dict) -> float:
    """Same weighting for item bonuses."""
    total = 0.0
    for k, v in bonuses.items():
        if k == "hp_max":
            total += v / 3.0
        else:
            total += v
    return total


def validate_unit_payload(rarity: str, data: dict) -> None:
    """Raise ValueError if unit payload violates rules or contract."""
    if not isinstance(data.get("stats"), dict):
        raise ValueError("Unit must have 'stats' object")
    stats = data["stats"]
    for key in STAT_KEYS:
        if key not in stats:
            raise ValueError(f"Unit stats missing required key: {key}")
    for k, v in stats.items():
        if k not in STAT_KEYS:
            raise ValueError(f"Unknown stat key: {k}")
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Stat {k} must be a non-negative number")
    budget = _compute_unit_budget(stats)
    lo, hi = UNIT_BUDGET_RANGES.get(rarity, (0, 0))
    if not (lo <= budget <= hi):
        raise ValueError(f"Unit budget {budget} outside range [{lo}, {hi}] for {rarity}")
    # Stat caps from rules (Common 6, Rare 8, Legendary 12, Mythic 16)
    cap = {"Common": 6, "Uncommon": 6, "Rare": 8, "Epic": 8, "Legendary": 12, "Mythic": 16}.get(rarity, 6)
    for k, v in stats.items():
        if int(v) > cap:
            raise ValueError(f"Stat {k}={v} exceeds cap {cap} for {rarity}")


def validate_item_payload(rarity: str, slot: str, data: dict) -> None:
    """Raise ValueError if item payload violates rules or contract."""
    if data.get("slot") != slot:
        raise ValueError(f"Item slot must be {slot}")
    bonuses = data.get("bonuses") or {}
    if not isinstance(bonuses, dict):
        raise ValueError("Item must have 'bonuses' object")
    for k in bonuses:
        if k not in STAT_KEYS:
            raise ValueError(f"Unknown bonus key: {k}")
    for k, v in bonuses.items():
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Bonus {k} must be a non-negative number")
    budget = _compute_item_budget(bonuses)
    lo, hi = ITEM_BUDGET_RANGES.get(rarity, (0, 0))
    if not (lo <= budget <= hi):
        raise ValueError(f"Item budget {budget} outside range [{lo}, {hi}] for {rarity}")
    modifier = data.get("modifier")
    has_mod = False
    if isinstance(modifier, dict):
        has_mod = bool(modifier.get("id"))
    elif modifier:
        has_mod = True
    if rarity in ("Common", "Uncommon", "Rare", "Epic"):
        if has_mod:
            raise ValueError("Only Legendary and Mythic items may have a modifier")
    else:
        if has_mod and isinstance(modifier, dict):
            mid = modifier.get("id", "")
            allowed = LEGENDARY_MODIFIERS + MYTHIC_MODIFIERS
            if mid not in allowed:
                raise ValueError(f"Modifier {mid} not in approved pool")


def _parse_json_from_response(text: str) -> dict:
    """Extract a single JSON object from model output (strip markdown if present)."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def generate_unit(
    rarity: str,
    rules_path: str,
    *,
    template_id: str | None = None,
    display_name: str | None = None,
    archetype: str | None = None,
    allowed_archetypes: list[str] | None = None,
    api_key: str | None = None,
) -> dict:
    """
    Generate unit stats. Uses OpenAI when api_key is set, else returns a valid placeholder.
    Works without templateId (AI invents name). Returns name, rarity, archetype, stats, total_budget, suggestedTemplateId.
    """
    if rarity not in RARITIES:
        raise ValueError(f"Invalid rarity: {rarity}")
    if allowed_archetypes and archetype and archetype not in allowed_archetypes:
        raise ValueError(f"archetype {archetype} not in allowed_archetypes")

    if api_key:
        rules = load_rules(rules_path)
        user_prompt = build_unit_prompt(
            rarity,
            template_id=template_id,
            display_name=display_name,
            archetype=archetype,
            allowed_archetypes=allowed_archetypes,
        )
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": rules},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            text = resp.choices[0].message.content or "{}"
            data = _parse_json_from_response(text)
            data.setdefault("rarity", rarity)
            data.setdefault("stats", {})
            for key in STAT_KEYS:
                data["stats"].setdefault(key, 0)
            data["stats"] = {k: int(data["stats"][k]) for k in STAT_KEYS}
            validate_unit_payload(rarity, data)
            data["total_budget"] = round(_compute_unit_budget(data["stats"]), 2)
            name = (data.get("name") or "").strip() or f"Unit_{rarity}"
            data["suggestedTemplateId"] = suggest_template_id(name)
            return data
        except Exception as e:
            raise RuntimeError(f"AI unit generation failed: {e}") from e

    # Placeholder: valid unit within rarity budget and stat caps
    lo, hi = UNIT_BUDGET_RANGES[rarity]
    cap = {"Common": 6, "Uncommon": 6, "Rare": 8, "Epic": 8, "Legendary": 12, "Mythic": 16}[rarity]
    target = (lo + hi) // 2
    # Melee Specialist: high melee, medium stamina, low magic
    hp = max(6, min(cap, target // 2))
    stamina = min(cap, 2)
    melee = min(cap, max(1, target - int(hp / 3) - stamina - 1))
    placeholder_stats = {
        "hp_max": hp,
        "stamina_max": stamina,
        "mana_max": 0,
        "melee": melee,
        "ranged": 0,
        "magic": 0,
        "maneuver": min(cap, 1),
    }
    budget = _compute_unit_budget(placeholder_stats)
    if budget < lo:
        placeholder_stats["melee"] = min(cap, placeholder_stats["melee"] + int(lo - budget))
    elif budget > hi:
        placeholder_stats["melee"] = max(0, placeholder_stats["melee"] - int(budget - hi))
    name = display_name or template_id or f"Unit_{rarity}"
    arch = archetype or (allowed_archetypes[0] if allowed_archetypes else "Melee Specialist")
    return {
        "name": name,
        "rarity": rarity,
        "archetype": arch,
        "stats": {k: int(placeholder_stats[k]) for k in STAT_KEYS},
        "total_budget": round(_compute_unit_budget(placeholder_stats), 2),
        "suggestedTemplateId": suggest_template_id(name),
    }


def generate_item(
    rarity: str,
    slot: str,
    rules_path: str,
    *,
    template_id: str | None = None,
    display_name: str | None = None,
    api_key: str | None = None,
) -> dict:
    """
    Generate item stats and optional modifier. Uses OpenAI when api_key is set, else placeholder.
    Works without templateId (AI invents name). Returns name, rarity, slot, bonuses, modifier, total_budget_used, suggestedTemplateId.
    """
    if rarity not in RARITIES:
        raise ValueError(f"Invalid rarity: {rarity}")
    if slot not in SLOTS:
        raise ValueError(f"Invalid slot: {slot}")

    if api_key:
        rules = load_rules(rules_path)
        user_prompt = build_item_prompt(
            rarity, slot, template_id=template_id, display_name=display_name
        )
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": rules},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            text = resp.choices[0].message.content or "{}"
            data = _parse_json_from_response(text)
            data.setdefault("rarity", rarity)
            data.setdefault("slot", slot)
            data.setdefault("bonuses", {})
            data["bonuses"] = {k: int(v) for k, v in (data.get("bonuses") or {}).items() if k in STAT_KEYS}
            if rarity in ("Common", "Uncommon", "Rare", "Epic"):
                data["modifier"] = None
            validate_item_payload(rarity, slot, data)
            data["total_budget_used"] = round(_compute_item_budget(data["bonuses"]), 2)
            name = (data.get("name") or "").strip() or f"{slot}_{rarity}"
            data["suggestedTemplateId"] = suggest_template_id(name)
            return data
        except Exception as e:
            raise RuntimeError(f"AI item generation failed: {e}") from e

    # Placeholder: valid item
    lo, hi = ITEM_BUDGET_RANGES[rarity]
    if slot == "Weapon":
        bonuses = {"melee": min(2, hi)}
    elif slot == "Armor":
        bonuses = {"hp_max": min(6, hi * 3)}
    else:
        bonuses = {"maneuver": min(2, hi)}
    budget = _compute_item_budget(bonuses)
    if budget < lo and slot == "Weapon":
        bonuses["melee"] = min(6, bonuses.get("melee", 0) + 1)
    name = display_name or template_id or f"{slot}_{rarity}"
    return {
        "name": name,
        "rarity": rarity,
        "slot": slot,
        "bonuses": {k: int(v) for k, v in bonuses.items()},
        "modifier": None,
        "total_budget_used": round(_compute_item_budget(bonuses), 2),
        "suggestedTemplateId": suggest_template_id(name),
    }

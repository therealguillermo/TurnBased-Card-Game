"""
Generation service: generate and serve card art and borders; generate stats for units and items.
Supports any unit/item type, type controls (archetypes, slots, rarities), and drop-type-based generation.
"""
import json
import os
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.generator import generate_and_save, load_catalog, get_template, RARITIES
from app.stat_generator import generate_unit, generate_item, SLOTS, UNIT_ARCHETYPES

# Paths (override with env in Docker)
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "/app/assets"))
CATALOG_PATH = os.environ.get("CATALOG_PATH", "/app/data/card-templates.json")
RULES_PATH = os.environ.get("RULES_PATH", "/app/stat_generation_rules.txt")
DROP_TYPES_PATH = os.environ.get("DROP_TYPES_PATH", "/app/data/drop-types.json")

BORDERS_DIR = ASSETS_DIR / "borders"
ART_DIR = ASSETS_DIR / "art"


def load_drop_types() -> list[dict]:
    """Load drop type definitions (id, label, type, rarities, archetypes, slots)."""
    path = Path(DROP_TYPES_PATH)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def get_drop_type(drop_type_id: str) -> dict | None:
    for dt in load_drop_types():
        if dt.get("id") == drop_type_id:
            return dt
    return None


app = FastAPI(title="Card Generation Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check for Docker / orchestration."""
    return {"status": "ok"}


@app.get("/assets/art/{template_id}.png")
def serve_art(template_id: str):
    """Serve generated art for a template. Returns 404 if not yet generated."""
    path = ART_DIR / f"{template_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Art not found: {template_id}")
    return FileResponse(path, media_type="image/png")


@app.get("/assets/borders/{rarity}.png")
def serve_border(rarity: str):
    """Serve border image for a rarity (Common, Uncommon, Rare, Epic, Legendary, Mythic)."""
    if rarity not in RARITIES:
        raise HTTPException(status_code=404, detail=f"Unknown rarity: {rarity}")
    # Filename convention: Common -> CommonBorder.png
    filename = f"{rarity}Border.png"
    path = BORDERS_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Border not found: {rarity}")
    return FileResponse(path, media_type="image/png")


class GenerateArtRequest(BaseModel):
    """Optional body for POST /generate/{template_id} when template is not in catalog."""
    displayName: str | None = None
    promptDescription: str | None = None


@app.post("/generate/{template_id}")
def generate(template_id: str, force: bool = False, body: GenerateArtRequest | None = None):
    """
    Generate pixel art for the given templateId.
    Saves to assets/art/{template_id}.png.
    For AI-generated templates not in the catalog, pass body with displayName and/or promptDescription.
    Use force=true to regenerate if file already exists.
    """
    path = ART_DIR / f"{template_id}.png"
    if path.is_file() and not force:
        return {
            "templateId": template_id,
            "url": f"/assets/art/{template_id}.png",
            "cached": True,
        }
    try:
        generate_and_save(
            template_id=template_id,
            art_dir=ART_DIR,
            catalog_path=CATALOG_PATH,
            use_ai=bool(os.environ.get("OPENAI_API_KEY")),
            api_key=os.environ.get("OPENAI_API_KEY"),
            display_name=body.displayName if body else None,
            prompt_description=body.promptDescription if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "templateId": template_id,
        "url": f"/assets/art/{template_id}.png",
        "cached": False,
    }


@app.get("/templates")
def list_templates():
    """List all template IDs from the catalog (for UI or Nakama)."""
    catalog = load_catalog(CATALOG_PATH)
    return {"templates": [t.get("templateId") for t in catalog if t.get("templateId")]}


# --- Stat generation (units and items); prompts adhere to stat_generation_rules.txt ---


class GenerateUnitRequest(BaseModel):
    """Request body for POST /generate/unit. Any unit type; optional type controls."""
    rarity: str
    templateId: str | None = None
    displayName: str | None = None
    archetype: str | None = None
    allowedArchetypes: list[str] | None = None


class GenerateItemRequest(BaseModel):
    """Request body for POST /generate/item. Any item type; slot or allowedSlots required."""
    rarity: str
    slot: str | None = None
    templateId: str | None = None
    displayName: str | None = None
    allowedSlots: list[str] | None = None


@app.post("/generate/unit")
def generate_unit_stats(body: GenerateUnitRequest):
    """
    Generate unit stats (any unit type). Optional type control: allowedArchetypes restricts to those archetypes.
    Returns name, rarity, archetype, stats, total_budget, suggestedTemplateId (for art and Nakama).
    """
    if body.rarity not in RARITIES:
        raise HTTPException(status_code=400, detail=f"Invalid rarity: {body.rarity}. Must be one of: {list(RARITIES)}")
    if body.allowedArchetypes is not None:
        invalid = [a for a in body.allowedArchetypes if a not in UNIT_ARCHETYPES]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid archetypes: {invalid}. Allowed: {list(UNIT_ARCHETYPES)}")
    display_name = body.displayName
    if body.templateId and not display_name:
        template = get_template(CATALOG_PATH, body.templateId)
        if template:
            display_name = template.get("displayName")
    try:
        result = generate_unit(
            body.rarity,
            RULES_PATH,
            template_id=body.templateId,
            display_name=display_name,
            archetype=body.archetype,
            allowed_archetypes=body.allowedArchetypes,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result


@app.post("/generate/item")
def generate_item_stats(body: GenerateItemRequest):
    """
    Generate item stats (any item type). Provide slot, or allowedSlots to pick one at random.
    Returns name, rarity, slot, bonuses, modifier, total_budget_used, suggestedTemplateId.
    """
    if body.rarity not in RARITIES:
        raise HTTPException(status_code=400, detail=f"Invalid rarity: {body.rarity}. Must be one of: {list(RARITIES)}")
    slot = body.slot
    if slot is None:
        if not body.allowedSlots:
            raise HTTPException(status_code=400, detail="Provide slot or allowedSlots")
        valid = [s for s in body.allowedSlots if s in SLOTS]
        if not valid:
            raise HTTPException(status_code=400, detail=f"allowedSlots must contain at least one of: {list(SLOTS)}")
        slot = random.choice(valid)
    elif slot not in SLOTS:
        raise HTTPException(status_code=400, detail=f"Invalid slot: {slot}. Must be one of: {list(SLOTS)}")
    display_name = body.displayName
    if body.templateId and not display_name:
        template = get_template(CATALOG_PATH, body.templateId)
        if template:
            display_name = template.get("displayName")
    try:
        result = generate_item(
            body.rarity,
            slot,
            RULES_PATH,
            template_id=body.templateId,
            display_name=display_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result


# --- Drop-type-based generation (for "open a rare unit drop", etc.) ---


class GenerateDropRequest(BaseModel):
    """Request body for POST /generate/drop."""
    dropTypeId: str
    rarityOverride: str | None = None


@app.get("/drop-types")
def list_drop_types():
    """List all drop type definitions (for UI / drop opening)."""
    return {"dropTypes": load_drop_types()}


@app.post("/generate/drop")
def generate_from_drop(body: GenerateDropRequest):
    """
    Generate a unit or item according to a drop type (e.g. rare_unit_drop, legendary_item_drop).
    Uses drop type's rarities, archetypes (units), and slots (items). Optional rarityOverride to force a rarity.
    Returns the same shape as /generate/unit or /generate/item, plus dropTypeId and kind (unit|item).
    """
    drop = get_drop_type(body.dropTypeId)
    if not drop:
        raise HTTPException(status_code=404, detail=f"Unknown dropTypeId: {body.dropTypeId}")
    rarities = drop.get("rarities") or []
    if not rarities:
        raise HTTPException(status_code=400, detail=f"Drop type {body.dropTypeId} has no rarities")
    rarity = body.rarityOverride if body.rarityOverride in RARITIES else random.choice(rarities)
    if rarity not in RARITIES:
        rarity = random.choice(list(RARITIES))

    kind = drop.get("type") or "any"
    if kind == "any":
        kind = random.choice(("unit", "item"))

    api_key = os.environ.get("OPENAI_API_KEY")
    try:
        if kind == "unit":
            archetypes = drop.get("archetypes")
            archetype = random.choice(archetypes) if archetypes else None
            result = generate_unit(
                rarity,
                RULES_PATH,
                display_name=None,
                archetype=archetype,
                allowed_archetypes=archetypes,
                api_key=api_key,
            )
            result["kind"] = "unit"
        else:
            slots = drop.get("slots")
            slot = random.choice(slots) if slots else random.choice(list(SLOTS))
            result = generate_item(rarity, slot, RULES_PATH, api_key=api_key)
            result["kind"] = "item"
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result["dropTypeId"] = body.dropTypeId
    return result

"""
Generation service: generate and serve card art and borders; generate stats for units and items.
Nakama or clients call GET /assets/... for images, POST /generate for art, POST /generate/unit and POST /generate/item for stats.
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.generator import generate_and_save, load_catalog, get_template, RARITIES
from app.stat_generator import generate_unit, generate_item, SLOTS

# Paths (override with env in Docker)
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "/app/assets"))
CATALOG_PATH = os.environ.get("CATALOG_PATH", "/app/data/card-templates.json")
RULES_PATH = os.environ.get("RULES_PATH", "/app/stat_generation_rules.txt")

BORDERS_DIR = ASSETS_DIR / "borders"
ART_DIR = ASSETS_DIR / "art"

app = FastAPI(title="Card Generation Service", version="1.0.0")


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


@app.post("/generate/{template_id}")
def generate(template_id: str, force: bool = False):
    """
    Generate pixel art for the given templateId.
    Saves to assets/art/{template_id}.png.
    Use force=true to regenerate if file already exists.
    Returns the URL path to the image (client can append to service base URL).
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
    """Request body for POST /generate/unit."""
    rarity: str
    templateId: str | None = None
    displayName: str | None = None
    archetype: str | None = None


class GenerateItemRequest(BaseModel):
    """Request body for POST /generate/item."""
    rarity: str
    slot: str
    templateId: str | None = None
    displayName: str | None = None


@app.post("/generate/unit")
def generate_unit_stats(body: GenerateUnitRequest):
    """
    Generate unit stats following stat_generation_rules.txt.
    Returns name, rarity, archetype, stats (all 7 keys), total_budget.
    Use the returned stats in rpc_create_unit payload.
    """
    if body.rarity not in RARITIES:
        raise HTTPException(status_code=400, detail=f"Invalid rarity: {body.rarity}. Must be one of: {list(RARITIES)}")
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
    Generate item stats (and optional modifier for Legendary/Mythic) following stat_generation_rules.txt.
    Returns name, rarity, slot, bonuses, modifier (or null), total_budget_used.
    Use bonuses (and optional passive from modifier.id) in rpc_grant_item payload.
    """
    if body.rarity not in RARITIES:
        raise HTTPException(status_code=400, detail=f"Invalid rarity: {body.rarity}. Must be one of: {list(RARITIES)}")
    if body.slot not in SLOTS:
        raise HTTPException(status_code=400, detail=f"Invalid slot: {body.slot}. Must be one of: {list(SLOTS)}")
    display_name = body.displayName
    if body.templateId and not display_name:
        template = get_template(CATALOG_PATH, body.templateId)
        if template:
            display_name = template.get("displayName")
    try:
        result = generate_item(
            body.rarity,
            body.slot,
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

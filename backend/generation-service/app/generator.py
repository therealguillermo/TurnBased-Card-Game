"""Generate pixel art for card templates (placeholder or AI)."""
import json
import os
from pathlib import Path

from PIL import Image


# Rarities that match the game contract (for border filenames)
RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")

# Output size for generated art (can be 32 or 1024; viewer downscales 1024 -> 32)
DEFAULT_ART_SIZE = 1024


def load_catalog(catalog_path: str) -> list[dict]:
    """Load card template catalog from JSON."""
    path = Path(catalog_path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def get_template(catalog_path: str, template_id: str) -> dict | None:
    """Return the template with the given templateId, or None."""
    for t in load_catalog(catalog_path):
        if t.get("templateId") == template_id:
            return t
    return None


def generate_placeholder(
    template_id: str,
    size: int = DEFAULT_ART_SIZE,
    *,
    display_name: str | None = None,
) -> Image.Image:
    """Create a simple placeholder image (no API)."""
    label = (display_name or template_id).strip() or template_id
    # Distinct hue per template for variety (hash template_id to get a stable color)
    h = hash(template_id) % 360
    # Use a muted saturation/value so it's not harsh
    from colorsys import hsv_to_rgb
    r, g, b = hsv_to_rgb(h / 360.0, 0.5, 0.8)
    color = (int(r * 255), int(g * 255), int(b * 255), 255)
    img = Image.new("RGBA", (size, size), color)
    # Optional: draw a simple border or text (for 1024 we'd need a font; for 32 we could skip text)
    if size >= 128:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 8)
        except OSError:
            font = ImageFont.load_default()
        text = (label or template_id)[:12]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        xy = ((size - tw) // 2, (size - th) // 2)
        draw.text(xy, text, fill=(255, 255, 255, 255), font=font)
    return img


def generate_and_save(
    template_id: str,
    art_dir: Path,
    catalog_path: str,
    size: int = DEFAULT_ART_SIZE,
    use_ai: bool = False,
    api_key: str | None = None,
    *,
    display_name: str | None = None,
    prompt_description: str | None = None,
) -> Path:
    """
    Generate art for the given templateId and save to art_dir.
    If templateId is not in the catalog, display_name or prompt_description must be provided.
    Returns the path to the saved file.
    """
    template = get_template(catalog_path, template_id)
    if not template:
        if not (display_name or prompt_description):
            raise ValueError(
                f"Unknown templateId: {template_id}. Provide displayName or promptDescription for AI-generated templates."
            )
        display_name = (display_name or prompt_description or template_id).strip()

    art_dir = Path(art_dir)
    art_dir.mkdir(parents=True, exist_ok=True)
    out_path = art_dir / f"{template_id}.png"
    label = display_name or (template.get("displayName") if template else None) or template_id

    if use_ai and api_key:
        # Optional: call OpenAI or Replicate here using (template or prompt_description)
        # For now, fall back to placeholder
        img = generate_placeholder(template_id, size, display_name=label)
    else:
        img = generate_placeholder(template_id, size, display_name=label)

    img.save(out_path, "PNG")
    return out_path

"""Generate pixel art for card templates (placeholder or AI)."""
import base64
import io
import json
import os
from pathlib import Path

from PIL import Image


# Rarities that match the game contract (for border filenames)
RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")

# Output size for generated art (can be 32 or 1024; viewer may downscale)
DEFAULT_ART_SIZE = 1024

# AI-generated art: 32x32 pixel art sprite (top-down RPG item/unit icon style)
PIXEL_ART_SIZE = 32

# Base style rules for pixel art (mandatory for all rarities)
PIXEL_ART_STYLE_RULES = """
Create a TRUE 32x32 pixel art sprite for a top-down medieval RPG item.

STYLE RULES (MANDATORY):
- Exactly 32x32 pixels
- Transparent background
- No anti-aliasing
- No gradients
- Hard pixel edges only
- 8–16 color palette maximum
- Strong, clean silhouette
- High contrast
- No painterly shading
- No soft lighting
- No blur
- No realistic rendering

VISUAL STYLE:
- Minimalist pixel art
- Classic RPG loot icon style
- Top-down readable at small scale
- Designed for dark UI background
- Clear center focus

FRAMING (MANDATORY):
- The artwork must FILL the entire 32x32 canvas.
- The subject must extend to or near the edges; use the full frame with minimal or no transparent margins.
- No large empty borders; edge-to-edge or nearly edge-to-edge composition.

IMPORTANT:
- Do NOT add borders
- Do NOT add glow
- Do NOT add UI framing
- The sprite itself must communicate rarity through material quality and detail level
""".strip()

# Rarity-specific design rules (appended to the prompt)
RARITY_DESIGN_RULES = {
    "Common": """
RARITY: Common
Design rules:
- Simple shape
- Basic material (iron, wood, cloth)
- Minimal decorative detail
- Muted colors
- Limited shading clusters
- Functional but plain
""".strip(),
    "Uncommon": """
RARITY: Uncommon
Design rules:
- Slightly improved craftsmanship
- Small accent details
- Slightly richer color
- Clean but still modest
- One minor decorative element
""".strip(),
    "Rare": """
RARITY: Rare
Design rules:
- High-quality material (polished steel, dyed leather)
- Stronger color saturation
- 2–3 decorative details
- Cleaner geometry
- More refined shading clusters
""".strip(),
    "Epic": """
RARITY: Epic
Design rules:
- Intricate craftsmanship
- Unique shape or silhouette twist
- Vibrant color accents
- Engraving, runes, gem inlay
- Noticeable visual complexity
- Luxurious materials
""".strip(),
    "Legendary": """
RARITY: Legendary
Design rules:
- Masterwork craftsmanship
- Complex silhouette
- Rare materials (gold filigree, enchanted crystal, glowing core implied via color contrast)
- High saturation highlights
- Rich ornamental detailing
- Visually powerful but still clean at 32x32
""".strip(),
    "Mythic": """
RARITY: Mythic
Design rules:
- Extremely intricate
- Unique silhouette not seen in lower tiers
- Exotic materials (crimson crystal, void metal, divine gold)
- Dramatic contrast
- Symbolic or arcane elements
- Maximum detail while preserving readability
""".strip(),
}


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


def build_image_prompt(
    display_name: str,
    *,
    prompt_description: str | None = None,
    template_type: str | None = None,
    rarity: str | None = None,
) -> str:
    """Build the prompt sent to the image model: style rules + rarity rules + subject."""
    rarity = (rarity or "Common").strip()
    if rarity not in RARITIES:
        rarity = "Common"
    subject = (prompt_description or display_name or "").strip() or "fantasy item or character"
    type_hint = f" ({template_type})" if template_type else ""
    subject_line = f"SUBJECT TO DRAW: {subject}{type_hint}."
    rarity_block = RARITY_DESIGN_RULES.get(rarity, RARITY_DESIGN_RULES["Common"])
    return f"{PIXEL_ART_STYLE_RULES}\n\n{rarity_block}\n\n{subject_line}"


def generate_image_ai(prompt: str, api_key: str) -> Image.Image:
    """Generate a 32x32 pixel-art sprite via OpenAI (gpt-image-1.5). Returns a PIL Image (RGBA, 32x32)."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    # 1024x1024 then downscale to 32x32 with nearest-neighbor for crisp pixel-art
    # GPT Image returns base64 by default; response_format is not supported for gpt-image-1.5
    resp = client.images.generate(
        model="gpt-image-1.5",
        prompt=prompt,
        size="1024x1024",
        n=1,
    )
    b64 = resp.data[0].b64_json
    raw = base64.b64decode(b64)
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    img = img.resize((PIXEL_ART_SIZE, PIXEL_ART_SIZE), Image.Resampling.NEAREST)
    return img


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
    rarity: str | None = None,
) -> Path:
    """
    Generate art for the given templateId and save to art_dir.
    If templateId is not in the catalog, display_name or prompt_description must be provided.
    rarity is used for AI prompts (default Common); can come from template or request.
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
    effective_rarity = rarity or (template.get("rarity") if template else None) or "Common"

    if use_ai and api_key:
        description = prompt_description or (template.get("promptDescription") if template else None) or label
        prompt = build_image_prompt(
            label,
            prompt_description=description,
            template_type=template.get("type") if template else None,
            rarity=effective_rarity,
        )
        img = generate_image_ai(prompt, api_key)
        img.save(out_path, "PNG")
        return out_path

    img = generate_placeholder(template_id, size, display_name=label)
    img.save(out_path, "PNG")
    return out_path

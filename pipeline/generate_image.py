#!/usr/bin/env python3
"""
generate_image.py — Generates an illustrative image via Imagen 4 (Google AI Studio).

Usage: python generate_image.py <content_dir>

Used for the ~10-15% of posts that are illustrative rather than data viz.
Reads prompt from metadata.json["image_prompt"], saves to image.png.

metadata.json fields:
  image_prompt: str       — the generation prompt
  image_source: "imagen"  — flag to use this script vs generate_viz.py
"""

import json
import sys
from pathlib import Path
from google import genai
from google.genai import types


CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.json"


def generate(content_dir: str):
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    api_key = config["gemini"]["api_key"]
    model = config["gemini"].get("image_model", "imagen-4.0-generate-001")

    content_path = Path(content_dir)
    meta_path = content_path / "metadata.json"

    if not meta_path.exists():
        print(f"ERROR: No metadata.json in {content_dir}")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    prompt = meta.get("image_prompt")
    if not prompt:
        print("ERROR: No image_prompt in metadata.json")
        sys.exit(1)

    # Append brand style to every prompt
    style_suffix = (
        " Style: dark background (#0F0F0F near-black), warm gold data elements, "
        "cartographic brutalism, clean minimal design, no text overlays, "
        "high contrast, data visualization aesthetic."
    )
    full_prompt = prompt + style_suffix

    output_path = content_path / "image.png"

    print(f"🎨 Generating image with {model}...")
    print(f"   Prompt: {prompt[:80]}...")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_images(
        model=model,
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",       # 1080×1080 equivalent for square posts
    
        )
    )

    if not response.generated_images:
        print("ERROR: No images returned")
        sys.exit(1)

    image = response.generated_images[0].image
    with open(output_path, "wb") as f:
        f.write(image.image_bytes)

    print(f"✅ Image saved to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_image.py <content_dir>")
        sys.exit(1)
    generate(sys.argv[1])

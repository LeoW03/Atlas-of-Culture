#!/usr/bin/env python3
"""
generate_viz.py — Renders a visualization from a content spec.

Usage: python generate_viz.py <content_dir>

Expects content_dir/metadata.json with a 'viz_html' field (full HTML string).
Renders via Playwright headless Chrome to image.png at 1080×1080.

Falls back to viz_code (matplotlib) for legacy content only.
"""

import json
import sys
import os
import asyncio
import subprocess
import tempfile
from pathlib import Path


async def render_html(html_content: str, output_path: str, w=1080, h=1080):
    """Render HTML string to PNG via Playwright."""
    from playwright.async_api import async_playwright

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": w, "height": h})
            await page.goto(f"file://{Path(tmp_path).resolve()}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1.5)  # Buffer for Google Fonts
            await page.screenshot(
                path=output_path,
                full_page=False,
                clip={"x": 0, "y": 0, "width": w, "height": h}
            )
            await browser.close()
    finally:
        os.unlink(tmp_path)


def render_matplotlib_legacy(viz_code: str, output_path: str):
    """Legacy fallback: execute matplotlib viz_code."""
    code = viz_code.replace("__OUTPUT_PATH__", output_path)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"ERROR generating viz (matplotlib):\n{result.stderr}")
            sys.exit(1)
    finally:
        os.unlink(tmp_path)


def generate(content_dir: str):
    content_path = Path(content_dir)
    meta_path = content_path / "metadata.json"

    if not meta_path.exists():
        print(f"ERROR: No metadata.json found in {content_dir}")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    output_path = str(content_path / "image.png")

    # Preferred: HTML + Playwright
    viz_html = meta.get("viz_html")
    if viz_html:
        print("Rendering HTML via Playwright...")
        asyncio.run(render_html(viz_html, output_path))
        print(f"✅ Image saved to {output_path}")
        return

    # Legacy: matplotlib viz_code
    viz_code = meta.get("viz_code")
    if viz_code:
        print("⚠️  Falling back to legacy matplotlib renderer...")
        render_matplotlib_legacy(viz_code, output_path)
        print(f"✅ Image saved to {output_path}")
        return

    print("ERROR: No viz_html or viz_code in metadata.json")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_viz.py <content_dir>")
        sys.exit(1)
    generate(sys.argv[1])

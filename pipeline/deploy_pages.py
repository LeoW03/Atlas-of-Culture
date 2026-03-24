#!/usr/bin/env python3
"""
deploy_pages.py — Deploy interactive HTML files to GitHub Pages.

Pushes all staged/*-interactive.html files to the gh-pages branch.
Each post gets a clean URL: https://leow03.github.io/Atlas-of-Culture/<slug>/

Run automatically after approve_post, or manually:
  python pipeline/deploy_pages.py
  python pipeline/deploy_pages.py staged/<slug>/  (deploy one post)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
GITHUB_REPO = "git@github.com:LeoW03/Atlas-of-Culture.git"
GITHUB_PAGES_URL = "https://leow03.github.io/Atlas-of-Culture"


def run(cmd, cwd=None, check=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"ERROR: {cmd}\n{result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout.strip()


def deploy(post_dir: Path = None):
    """Deploy interactive HTML files to gh-pages branch."""

    # Collect files to deploy
    if post_dir:
        interactives = list(post_dir.glob("*-interactive.html"))
        slugs = [post_dir.name] if interactives else []
    else:
        interactives = list(ROOT.glob("staged/*/*-interactive.html"))
        slugs = [p.parent.name for p in interactives]

    if not interactives:
        print("No interactive HTML files found to deploy.")
        return {}

    print(f"\n🚀 Deploying {len(interactives)} interactive(s) to GitHub Pages...")

    # Work in a temp directory — checkout gh-pages branch
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone just the gh-pages branch (or create it)
        try:
            run(f"git clone --depth 1 --branch gh-pages {GITHUB_REPO} .", cwd=tmpdir)
            print("   Cloned gh-pages branch")
        except RuntimeError:
            # Branch doesn't exist yet — init fresh
            run(f"git init", cwd=tmpdir)
            run(f"git remote add origin {GITHUB_REPO}", cwd=tmpdir)
            # Create minimal index
            Path(tmpdir, "index.html").write_text(
                "<!DOCTYPE html><html><head><meta charset='UTF-8'/>"
                "<title>Atlas of Culture</title></head><body>"
                "<h1>Atlas of Culture</h1><p>Interactive data visualizations.</p>"
                "</body></html>"
            )
            run(f"git checkout --orphan gh-pages", cwd=tmpdir)
            print("   Created new gh-pages branch")

        # Copy each interactive into its slug directory
        urls = {}
        for html_path in interactives:
            slug = html_path.parent.name
            dest_dir = Path(tmpdir) / slug
            dest_dir.mkdir(exist_ok=True)

            # Copy HTML
            shutil.copy(html_path, dest_dir / "index.html")

            # Copy slide images if they exist
            for img in html_path.parent.glob("image_*.png"):
                shutil.copy(img, dest_dir / img.name)
            for img in html_path.parent.glob("slide-*.png"):
                shutil.copy(img, dest_dir / img.name)

            url = f"{GITHUB_PAGES_URL}/{slug}/"
            urls[slug] = url
            print(f"   ✅ {slug} → {url}")

        # Update root index with links to all posts
        index_links = "\n".join([
            f'<li><a href="{GITHUB_PAGES_URL}/{s}/">{s}</a></li>'
            for s in sorted(urls.keys())
        ])
        Path(tmpdir, "index.html").write_text(
            f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/>
<title>Atlas of Culture — Interactive Posts</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 700px; margin: 60px auto; padding: 0 20px; background: #07070c; color: #f0ece0; }}
  h1 {{ font-size: 2rem; margin-bottom: 8px; }}
  p {{ color: rgba(255,255,255,0.5); margin-bottom: 32px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin-bottom: 12px; }}
  a {{ color: #e8c547; text-decoration: none; font-family: monospace; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>Atlas of Culture</h1>
<p>Interactive data visualizations. @atlasofculture on X.</p>
<ul>{index_links}</ul>
</body>
</html>"""
        )

        # Commit and push
        run("git config user.email 'atlas@atlasofculture.com'", cwd=tmpdir)
        run("git config user.name 'Atlas of Culture'", cwd=tmpdir)
        run("git add -A", cwd=tmpdir)

        try:
            run('git commit -m "Deploy interactive posts"', cwd=tmpdir)
        except RuntimeError:
            print("   Nothing new to commit")
            return urls

        run("git push origin gh-pages --force", cwd=tmpdir)
        print(f"\n✅ Deployed to GitHub Pages")
        print(f"   Index: {GITHUB_PAGES_URL}/")
        for slug, url in urls.items():
            print(f"   {slug}: {url}")

    # Update metadata files with real URLs
    for slug, url in urls.items():
        meta_path = ROOT / "staged" / slug / "metadata.json"
        if not meta_path.exists():
            meta_path = ROOT / "queue" / slug / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta["interactive_url"] = url
            # Update tweet 4 in slides if it has [link] placeholder
            if "slides" in meta:
                meta["slides"] = [
                    s.replace("[link]", url).replace("[link to teacher-pay-outcomes-interactive.html]", url)
                    for s in meta["slides"]
                ]
            meta_path.write_text(json.dumps(meta, indent=2))

    return urls


if __name__ == "__main__":
    post_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    deploy(post_dir)

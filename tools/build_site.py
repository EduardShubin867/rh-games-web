#!/usr/bin/env python3
"""Rebuild the two pinned source commits; publish only verified static output."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import re
import subprocess
import sys

from catalog import read_catalog, verify_game

ROOT = Path(__file__).resolve().parents[1]


def apply_site_shell(folder, slug, expected, manifest, revision):
    """Replace only the launch UI after verifying the original game export."""
    exported = (folder / "index.html").read_text(encoding="utf-8")
    match = re.search(r"^const config = (\{.*\});$", exported, re.MULTILINE)
    if not match:
        raise ValueError("Cannot find the exported Godot configuration: " + slug)
    config = json.loads(match[1])
    prefix = manifest["engine_file_prefix"]
    if config.get("executable") != prefix:
        raise ValueError("Godot configuration differs from the verified engine prefix")
    page = (ROOT / "templates/game.html").read_text(encoding="utf-8")
    values = {
        "__TITLE__": html.escape(manifest["title"]),
        "__VERSION__": expected["version"],
        "__ENGINE__": prefix,
        "__ASSET_VERSION__": revision,
        "__CONFIG__": json.dumps(config, ensure_ascii=False).replace("<", "\\u003c"),
    }
    for token, value in values.items():
        page = page.replace(token, value)
    content = page.encode("utf-8")
    for name in ("index.html", prefix + ".html"):
        (folder / name).write_bytes(content)
        manifest["files"][name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    manifest["site_shell_revision"] = revision
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_game(folder, slug, expected)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "sources")
    parser.add_argument("--from-existing", action="store_true")
    parser.add_argument("--refs", action="store_true")
    args = parser.parse_args()
    catalog = read_catalog(ROOT / "games.json")
    if args.refs:
        for slug, entry in catalog["games"].items():
            print(slug.replace("-", "_") + "=" + entry["commit"])
        return
    destination = ROOT / "dist"
    staging = ROOT / "dist.staging"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(ROOT / "site", staging)
    # Refresh common UI assets on every UI change, including on cached mobile browsers.
    assets = sorted((ROOT / "site/assets").glob("*.css")) + sorted((ROOT / "site/assets").glob("*.js"))
    revision = hashlib.sha256(b"".join(path.read_bytes() for path in assets) +
                              (ROOT / "templates/game.html").read_bytes()).hexdigest()[:16]
    engine = os.environ.get("GODOT_BIN")
    if not args.from_existing and not engine:
        binary_root = args.sources / "lovec-suiko/tools/bin"
        candidates = list(binary_root.glob("Godot_v*-stable_linux.x86_64")) + list(binary_root.glob("Godot.app/Contents/MacOS/Godot"))
        if len(candidates) != 1:
            raise ValueError("Install the pinned Godot version before building")
        engine = str(candidates[0].resolve())
    for slug, entry in catalog["games"].items():
        source = (args.sources / slug).resolve()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        if commit != entry["commit"]:
            raise ValueError("Source checkout differs from games.json: " + slug)
        if not args.from_existing:
            subprocess.run([sys.executable, "tools/prepare_web.py"], cwd=source,
                           env={**os.environ, "GODOT_BIN": engine}, check=True)
        folder = source / "dist/web/game"
        manifest = verify_game(folder, slug, entry)
        shutil.copytree(folder, staging / slug)
        apply_site_shell(staging / slug, slug, entry, manifest, revision)
    page = (staging / "index.html").read_text()
    page = page.replace("__ASSET_VERSION__", revision)
    for slug, entry in catalog["games"].items():
        page = page.replace("__" + slug.upper().replace("-", "_") + "_VERSION__", entry["version"])
        page = page.replace(f'href="{slug}/"', f'href="{slug}/?v={entry["commit"]}&amp;ui={revision}"')
        page = page.replace(f'src="{slug}/poster.png"', f'src="{slug}/poster.png?v={entry["commit"]}"')
    if "__VERSION__" in page:
        raise ValueError("Unresolved site version")
    (staging / "index.html").write_text(page, encoding="utf-8")
    (staging / "versions.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    (staging / ".nojekyll").touch()
    if destination.exists():
        shutil.rmtree(destination)
    staging.rename(destination)
    print("Site build PASS: both pinned games and every runtime checksum verified")


if __name__ == "__main__":
    main()

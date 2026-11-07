#!/usr/bin/env python3
"""Promote one verified game release, preserving the other game's version."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from catalog import REPOSITORIES, read_catalog, verify_game, version_tuple


def git(root, *args, check=True):
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=check)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--game", required=True, choices=REPOSITORIES)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if git(args.site, "status", "--porcelain").stdout.strip():
        raise ValueError("Website checkout must be clean before promotion")
    folder = args.source / "dist/web/game"
    release = json.loads((folder / "manifest.json").read_text())
    proposed = {"repository": REPOSITORIES[args.game], "version": release["version"], "commit": release["source_commit"]}
    verify_game(folder, args.game, proposed)
    archive = args.source / "dist/web" / f"{args.game}-{release['version']}-web.zip"
    proposed["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    git(args.site, "config", "user.name", "RH Games releases")
    git(args.site, "config", "user.email", "releases@users.noreply.github.com")
    # A simultaneous release of the other game can win the first push. Re-read
    # its latest manifest on a non-fast-forward rejection; never overwrite it.
    for attempt in range(3):
        git(args.site, "fetch", "origin", "main")
        git(args.site, "checkout", "-B", "main", "origin/main")
        path = args.site / "games.json"
        catalog = read_catalog(path)
        current = catalog["games"][args.game]
        if version_tuple(proposed["version"]) < version_tuple(current["version"]):
            raise ValueError("Refusing to roll back a newer published release")
        if proposed["version"] == current["version"] and proposed["commit"] != current["commit"]:
            raise ValueError("A published version must keep its original source commit; bump VERSION.json")
        if current == proposed:
            print("This exact Web release is already in the site catalog")
            return
        catalog["games"][args.game] = proposed
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
        git(args.site, "add", "games.json")
        git(args.site, "commit", "-m", f"Publish {args.game} {proposed['version']} on the website")
        result = git(args.site, "push", "origin", "HEAD:main", check=False)
        if result.returncode == 0:
            print(f"Website notified: {args.game} {proposed['version']}")
            return
        if not any(marker in result.stderr for marker in ("fetch first", "non-fast-forward", "stale info")):
            raise RuntimeError("Website push failed: " + result.stderr)
    raise RuntimeError("Concurrent site updates prevented promotion; rerun this release job")


if __name__ == "__main__":
    main()

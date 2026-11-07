"""Strict, shared contract between game release publishers and the website."""
import hashlib
import json
from pathlib import Path
import re

REPOSITORIES = {"lovec-suiko": "EduardShubin867/lovec-suiko", "hk-in-a-row": "EduardShubin867/hk-in-a-row"}
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def version_tuple(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError("Expected a stable release version")
    return tuple(map(int, value.split(".")))


def read_catalog(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != 1 or set(data.get("games", {})) != set(REPOSITORIES):
        raise ValueError("The catalog must contain exactly the two supported games")
    for slug, entry in data["games"].items():
        version_tuple(entry["version"])
        if entry["repository"] != REPOSITORIES[slug] or not re.fullmatch(r"[0-9a-f]{40}", entry["commit"]):
            raise ValueError("Unexpected repository or source commit")
        digest = entry.get("archive_sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid release archive checksum")
    return data


def verify_game(folder, slug, expected):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    if (manifest["game"], manifest["version"], manifest["source_commit"], manifest["threads"]) != (slug, expected["version"], expected["commit"], False):
        raise ValueError("The exported game does not match its pinned release")
    if any(path.is_symlink() for path in folder.rglob("*")):
        raise ValueError("Symlinks are not release files")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.relative_to(folder).as_posix() != "manifest.json"}
    if actual != set(manifest["files"]):
        raise ValueError("The exported game has missing or extra files")
    for name, details in manifest["files"].items():
        path = folder / name
        if not path.resolve().is_relative_to(folder.resolve()) or path.is_symlink():
            raise ValueError("Unsafe release file")
        content = path.read_bytes()
        if len(content) != details["bytes"] or hashlib.sha256(content).hexdigest() != details["sha256"]:
            raise ValueError("Release file checksum mismatch: " + name)
    prefix = f"game-{slug}-{expected['version']}-{expected['commit'][:12]}"
    if manifest.get("engine_file_prefix") != prefix:
        raise ValueError("Runtime assets must be versioned by source commit")
    if (folder / (prefix + ".wasm")).read_bytes()[:4] != b"\x00asm" or (folder / (prefix + ".pck")).read_bytes()[:4] != b"GDPC":
        raise ValueError("Invalid WebAssembly or game pack")
    return manifest

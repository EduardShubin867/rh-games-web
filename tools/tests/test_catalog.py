import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import read_catalog, verify_game, version_tuple


class CatalogTests(unittest.TestCase):
    def test_version_order_is_numeric(self):
        self.assertGreater(version_tuple("1.10.0"), version_tuple("1.9.9"))
        for value in ["v1.0.0", "1.0", "1.0.0-rc1", "01.0.0"]:
            with self.assertRaises(ValueError):
                version_tuple(value)

    def test_unknown_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "games.json"
            path.write_text(json.dumps({"schema": 1, "games": {"morok": {}}}))
            with self.assertRaises(ValueError):
                read_catalog(path)

    def game(self, folder):
        expected = {"version": "1.0.0", "commit": "a" * 40}
        files = {"game-lovec-suiko-1.0.0-aaaaaaaaaaaa.wasm": b"\x00asmtest", "game-lovec-suiko-1.0.0-aaaaaaaaaaaa.pck": b"GDPCtest", "index.html": b"page", "game-lovec-suiko-1.0.0-aaaaaaaaaaaa.js": b"engine"}
        for name, content in files.items():
            (folder / name).write_bytes(content)
        manifest = {"schema": 1, "game": "lovec-suiko", "version": expected["version"], "source_commit": expected["commit"], "threads": False, "engine_file_prefix": "game-lovec-suiko-1.0.0-aaaaaaaaaaaa",
                    "files": {name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()} for name, content in files.items()}}
        (folder / "manifest.json").write_text(json.dumps(manifest))
        return expected

    def test_complete_game_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            verify_game(folder, "lovec-suiko", self.game(folder))

    def test_corrupted_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected = self.game(folder)
            (folder / "game-lovec-suiko-1.0.0-aaaaaaaaaaaa.wasm").write_bytes(b"bad")
            with self.assertRaises(ValueError):
                verify_game(folder, "lovec-suiko", expected)

    def test_different_source_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected = self.game(folder)
            expected["commit"] = "b" * 40
            with self.assertRaises(ValueError):
                verify_game(folder, "lovec-suiko", expected)

    def test_extra_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected = self.game(folder)
            (folder / "private.key").write_text("not a release file")
            with self.assertRaises(ValueError):
                verify_game(folder, "lovec-suiko", expected)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected = self.game(folder)
            (folder / "game-lovec-suiko-1.0.0-aaaaaaaaaaaa.js").unlink()
            (folder / "game-lovec-suiko-1.0.0-aaaaaaaaaaaa.js").symlink_to(folder / "index.html")
            with self.assertRaises(ValueError):
                verify_game(folder, "lovec-suiko", expected)


if __name__ == "__main__":
    unittest.main()

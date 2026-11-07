import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_site import apply_site_shell
from catalog import verify_game


class SiteShellTests(unittest.TestCase):
    def fixture(self, folder, config=None):
        expected = {"version": "1.0.0", "commit": "a" * 40}
        prefix = "game-lovec-suiko-1.0.0-aaaaaaaaaaaa"
        config = {"executable": prefix, "args": ["</script><script>bad()</script>"]} if config is None else config
        exported = "<script>\nconst config = " + json.dumps(config) + ";\n</script>"
        files = {"index.html": exported.encode(), prefix + ".html": exported.encode(),
                 prefix + ".wasm": b"\x00asmtest", prefix + ".pck": b"GDPCtest"}
        for name, content in files.items():
            (folder / name).write_bytes(content)
        manifest = {"schema": 1, "game": "lovec-suiko", "title": "Title <&>", "version": "1.0.0",
                    "source_commit": "a" * 40, "threads": False, "engine_file_prefix": prefix,
                    "files": {name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                              for name, content in files.items()}}
        (folder / "manifest.json").write_text(json.dumps(manifest))
        return expected, verify_game(folder, "lovec-suiko", expected)

    def test_shell_preserves_binaries_and_verifiable_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected, manifest = self.fixture(folder)
            original_pack = manifest["files"][manifest["engine_file_prefix"] + ".pck"].copy()
            apply_site_shell(folder, "lovec-suiko", expected, manifest, "revision1")
            published = verify_game(folder, "lovec-suiko", expected)
            self.assertEqual(published["files"][manifest["engine_file_prefix"] + ".pck"], original_pack)
            self.assertEqual((folder / "index.html").read_bytes(),
                             (folder / (manifest["engine_file_prefix"] + ".html")).read_bytes())
            page = (folder / "index.html").read_text()
            self.assertIn("Title &lt;&amp;&gt;", page)
            self.assertNotIn("</script><script>bad()", page)
            config = page.split('<script id="game-config" type="application/json">')[1].split("</script>")[0]
            self.assertEqual(json.loads(config)["args"], ["</script><script>bad()</script>"])

    def test_different_engine_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected, manifest = self.fixture(folder, {"executable": "unexpected"})
            with self.assertRaisesRegex(ValueError, "engine prefix"):
                apply_site_shell(folder, "lovec-suiko", expected, manifest, "revision1")

    def test_changed_export_format_fails_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            expected, manifest = self.fixture(folder)
            (folder / "index.html").write_text("unknown export format")
            with self.assertRaisesRegex(ValueError, "Godot configuration"):
                apply_site_shell(folder, "lovec-suiko", expected, manifest, "revision1")


if __name__ == "__main__":
    unittest.main()

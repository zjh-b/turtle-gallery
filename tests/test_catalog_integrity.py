"""Catch broken catalog entries and published assets without executing artwork."""
import copy
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

from tools import check_catalog
from tools.check_catalog import validate_catalog
from tools.export_gallery import build_gallery


def png_bytes():
    """One valid transparent PNG pixel, using only the standard library."""
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
            + chunk(b"IEND", b""))


def work(number, collection="interactive"):
    label = f"{number:02d}"
    return dict(
        id=number, number=label, title=f"Work {label}", subtitle="A small scene",
        filename=f"scenes/{label}.py", collection=collection, category="Geometry",
        controls="Click to draw", description="An example artwork.",
        featured=False, tags=("drawing",), creation=False, autoplay=False,
        entry_class="ExampleScene" if collection == "interactive" else None,
        console=False, accent="#abcdef", motif="flower",
        preview=f"previews/{label}.png", web_play="play/example.html" if number == 1 else None,
    )


class CatalogIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.works = [work(1), work(2, "original")]
        for item in self.works:
            self.add_assets(item)
        self.publish()

    def write(self, relative, data):
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    def add_assets(self, item):
        self.write(item["filename"], "raise AssertionError('Artwork must not execute')\n")
        self.write(item["preview"], png_bytes())
        section = "exhibits" if item["collection"] == "interactive" else "originals"
        self.write(f"docs/assets/{section}/{item['number']}.png", png_bytes())
        if item.get("web_play"):
            self.write("docs/" + item["web_play"], "<!doctype html><title>Example</title>")

    def publish(self, works=None):
        data = build_gallery(self.works if works is None else works)
        self.write("docs/gallery.json", json.dumps(data, ensure_ascii=False) + "\n")
        return data

    def assert_invalid(self, works=None, mention=None):
        errors = validate_catalog(self.works if works is None else works, self.root)
        self.assertTrue(errors, "Invalid fixture passed catalog validation")
        self.assertTrue(all(isinstance(error, str) for error in errors))
        if mention:
            self.assertIn(mention.lower(), "\n".join(errors).lower())
        return errors

    def test_valid_catalog_is_read_only_and_does_not_execute_sources(self):
        before = {path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(validate_catalog(self.works, self.root), [])
        after = {path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)

    def test_new_work_does_not_require_contiguous_ids_or_fixed_work_count(self):
        item = work(29)
        self.works.append(item)
        self.add_assets(item)
        self.publish()
        self.assertEqual(validate_catalog(self.works, self.root), [])

    def test_cli_reports_success_and_missing_assets_without_repairing_them(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(check_catalog, "ROOT", self.root), \
                patch("run.catalog", return_value=SimpleNamespace(WORKS=self.works)), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(check_catalog.main(), 0)
            self.assertTrue(stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")
            preview = self.root / "docs/assets/exhibits/01.png"
            preview.unlink()
            self.assertEqual(check_catalog.main(), 1)
            self.assertIn("01.png", stderr.getvalue())
            self.assertFalse(preview.exists())

    def test_export_builder_is_pure_and_normalizes_tags_for_json(self):
        before = copy.deepcopy(self.works)
        exported = build_gallery(self.works)
        self.assertEqual(self.works, before)
        self.assertEqual(exported["works"][0]["tags"], ["drawing"])
        self.assertEqual(json.loads(json.dumps(exported)), exported)

    def test_swapped_numbers_cannot_pass_with_unchanged_number_set(self):
        self.works[0]["number"], self.works[1]["number"] = "02", "01"
        self.publish()
        self.assert_invalid(mention="number")

    def test_duplicate_ids_numbers_and_sources_are_rejected(self):
        for field in ("id", "number", "filename"):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.works)
                modified[1][field] = modified[0][field]
                self.publish(modified)
                self.assert_invalid(modified, field)

    def test_invalid_ids_and_noncanonical_numbers_are_rejected(self):
        for field, value in (("id", True), ("id", 0), ("id", 100), ("id", 1.0),
                             ("number", "1"), ("number", "001"), ("number", 1)):
            with self.subTest(field=field, value=value):
                modified = copy.deepcopy(self.works)
                modified[0][field] = value
                self.publish(modified)
                self.assert_invalid(modified, field)

    def test_invalid_metadata_is_reported_without_a_traceback(self):
        for field, value in (("title", ""), ("title", None), ("collection", "unknown"),
                             ("collection", []), ("id", {}), ("number", []),
                             ("filename", {}), ("filename", "scenes/\ud800.py"),
                             ("preview", []), ("web_play", {}),
                             ("tags", "drawing"), ("tags", [17]), ("tags", [""]),
                             ("featured", "yes"), ("creation", 1), ("autoplay", None)):
            with self.subTest(field=field, value=value):
                modified = copy.deepcopy(self.works)
                modified[0][field] = value
                self.assert_invalid(modified, field)
        modified = copy.deepcopy(self.works)
        del modified[0]["title"]
        self.assert_invalid(modified, "title")
        self.assert_invalid([None])
        self.assert_invalid([])

    def test_missing_source_desktop_preview_web_preview_or_online_page_is_reported(self):
        paths = ("scenes/01.py", "previews/01.png", "docs/assets/exhibits/01.png",
                 "docs/assets/originals/02.png", "docs/play/example.html")
        for relative in paths:
            with self.subTest(path=relative):
                path = self.root / relative
                previous = path.read_bytes()
                path.unlink()
                try:
                    self.assert_invalid(mention=path.name)
                finally:
                    path.write_bytes(previous)

    def test_empty_or_non_png_previews_are_rejected(self):
        image = png_bytes()
        invalid_images = (b"", b"This is not a PNG image", image[:8],
                          image[:12] + b"IDAT" + image[16:],
                          image[:16] + struct.pack(">I", 0) + image[20:])
        for relative in ("previews/01.png", "docs/assets/exhibits/01.png",
                         "docs/assets/originals/02.png"):
            for invalid in invalid_images:
                with self.subTest(path=relative, content=invalid):
                    path = self.root / relative
                    path.write_bytes(invalid)
                    try:
                        self.assert_invalid(mention=path.name)
                    finally:
                        path.write_bytes(png_bytes())

    def test_path_casing_is_checked_on_case_insensitive_systems_too(self):
        for field, value in (("filename", "Scenes/01.py"),
                             ("preview", "Previews/01.png"),
                             ("web_play", "play/Example.html")):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.works)
                modified[0][field] = value
                self.publish(modified)
                self.assert_invalid(modified, field)

    def test_paths_cannot_escape_or_use_windows_absolute_forms(self):
        for field in ("filename", "preview", "web_play"):
            for value in ("../outside.py", "/outside.py", "C:/outside.py",
                          "C:\\outside.py", "\\\\server\\share\\outside.py"):
                with self.subTest(field=field, value=value):
                    modified = copy.deepcopy(self.works)
                    modified[0][field] = value
                    self.publish(modified)
                    self.assert_invalid(modified, field)

    def test_stale_and_incomplete_exported_metadata_is_rejected(self):
        for mutation in ("changed_title", "missing_work", "duplicate_work", "wrong_source"):
            with self.subTest(mutation=mutation):
                data = build_gallery(self.works)
                if mutation == "changed_title":
                    data["works"][0]["title"] = "Old title"
                elif mutation == "missing_work":
                    data["works"].pop()
                elif mutation == "duplicate_work":
                    data["works"].append(copy.deepcopy(data["works"][0]))
                else:
                    data["works"][0]["source"] = "https://example.com/wrong.py"
                self.write("docs/gallery.json", json.dumps(data))
                self.assert_invalid(mention="gallery.json")

    def test_missing_or_invalid_export_is_reported_without_a_traceback(self):
        destination = self.root / "docs/gallery.json"
        destination.unlink()
        self.assert_invalid(mention="gallery.json")
        for content in (b"{broken", b"\xff", b"[]", b"null"):
            with self.subTest(content=content):
                destination.write_bytes(content)
                self.assert_invalid(mention="gallery.json")


if __name__ == "__main__":
    unittest.main()

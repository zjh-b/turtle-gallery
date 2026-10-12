"""Protect recording provenance, failed exports and the delivered film."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import render_butterfly_film as film
from tools.capture_butterfly_video import source_hashes, timeline
from tools.render_butterfly_preview import sha, validate_report


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is optional")
class FilmExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture"
        self.capture.mkdir()
        count, events = timeline(30, 20)
        self.report = {"work": 28, "frames": count, "fps": 30, "duration": 20,
                       "events": events, "size": [16, 12],
                       "source_sha256_lf": source_hashes()}
        (self.capture / "capture.json").write_text(json.dumps(self.report), encoding="utf-8")

    def make_frames(self):
        from PIL import Image
        picture = Image.new("RGB", (16, 12), "#101025")
        picture.save(self.capture / "frame-00000.png")
        data = (self.capture / "frame-00000.png").read_bytes()
        for index in range(1, 600):
            (self.capture / f"frame-{index:05d}.png").write_bytes(data)

    def test_existing_output_is_preserved(self):
        output = self.root / "existing"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            film.produce(self.capture, output)
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_missing_and_wrong_sized_frames_fail_before_output_creation(self):
        from PIL import Image
        output = self.root / "out"
        with self.assertRaisesRegex(ValueError, "missing frames"):
            film.produce(self.capture, output)
        self.assertFalse(output.exists())
        self.make_frames()
        Image.new("RGB", (15, 12)).save(self.capture / "frame-00599.png")
        with self.assertRaisesRegex(ValueError, "size changed"):
            film.produce(self.capture, output)
        self.assertFalse(output.exists())

    def test_encoder_failure_removes_partial_media_and_has_no_success_manifest(self):
        self.make_frames()
        output = self.root / "out"
        class BrokenEncoder:
            def __init__(self, executable, path, size, fps):
                Path(path).write_bytes(b"incomplete")
                self.aborted = False
            def write(self, pixels):
                raise RuntimeError("injected encoder failure")
            def abort(self):
                self.aborted = True
        # Use an installed Pillow font path only for this rendering test.
        from PIL import ImageFont
        font = ImageFont.load_default()
        with patch.object(film, "_ffmpeg", return_value="unused"), \
                patch.object(film, "fonts", return_value={key: font for key in
                    ("label", "caption", "small", "headline", "hero", "cover_small")}), \
                patch.object(film, "Encoder", side_effect=BrokenEncoder):
            with self.assertRaisesRegex(RuntimeError, "injected encoder failure"):
                film.produce(self.capture, output)
        self.assertFalse((output / "manifest.json").exists())
        self.assertFalse((output / ".silent.mp4").exists())
        self.assertFalse((output / "video.mp4").exists())
        self.assertEqual(len(list(self.capture.glob("frame-*.png"))), 600)

    def test_cover_and_video_use_the_same_bytes_if_input_changes_during_encoding(self):
        from PIL import Image
        self.make_frames()
        original_hash = sha(self.capture / "frame-00090.png")
        cover_pixels = []
        def rendering(source, seconds, face):
            if seconds == 3:
                Image.new("RGB", (16, 12), "white").save(self.capture / "frame-00090.png")
            return Image.new("RGB", (2, 2))
        def make_cover(source, portrait, face):
            cover_pixels.append(source.convert("RGB").getpixel((0, 0)))
            return Image.new("RGB", (2, 2))
        output = self.root / "out"
        with patch.object(film, "_ffmpeg", return_value="unused"), \
                patch.object(film, "fonts", return_value={}), \
                patch.object(film, "Encoder"), \
                patch.object(film, "compose", side_effect=rendering), \
                patch.object(film, "cover", side_effect=make_cover), \
                patch.object(film, "synthesize", return_value={}), \
                patch.object(film, "mux", side_effect=lambda ff, silent, score, destination:
                             destination.write_bytes(b"fake video")):
            manifest = film.produce(self.capture, output)
        self.assertEqual(cover_pixels, [(16, 16, 37)] * 2)
        self.assertEqual(manifest["input_frame_sha256"]["frame-00090.png"], original_hash)
        self.assertNotEqual(sha(self.capture / "frame-00090.png"), original_hash)


class DeliveredFilmTests(unittest.TestCase):
    def test_film_files_and_sources_match_manifest(self):
        root = Path(__file__).resolve().parents[1]
        assets = root / "docs/assets/social-butterfly-film"
        manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        validate_report(manifest["capture"])
        self.assertEqual(manifest["status"], "candidate; not submitted")
        self.assertEqual(manifest["size"], [1280, 720])
        self.assertEqual((manifest["frames"], manifest["fps"], manifest["duration"]),
                         (600, 30, 20))
        self.assertEqual(set(manifest["files"]), {"video.mp4", "cover.png",
                         "cover-4x3.png", "storyboard.jpg", "captions.zh.srt"})
        for name, expected in manifest["files"].items():
            self.assertEqual(sha(assets / name), expected, name)
        for name, expected in manifest["source_sha256_lf"].items():
            self.assertEqual(sha(root / name, True), expected, name)
        self.assertEqual(len(manifest["input_frame_sha256"]), 600)
        self.assertEqual(manifest["audio"]["channels"], 2)
        self.assertEqual(manifest["audio"]["sample_rate"], 48000)
        self.assertLess(manifest["audio"]["peak_dbfs"], -9)
        self.assertGreater(manifest["audio"]["rms"], .001)
        for audio_at, event in zip(manifest["audio"]["cue_times"], manifest["capture"]["events"]):
            self.assertLessEqual(abs(audio_at - event["time"]), 1 / manifest["fps"])
        self.assertEqual(len(manifest["audio"]["cue_times"]), 7)
        self.assertNotIn(b"\r", (assets / "captions.zh.srt").read_bytes())


if __name__ == "__main__":
    unittest.main()

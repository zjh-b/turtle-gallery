"""Protect rose recording provenance, export cleanup and preview artifacts."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import render_rose_preview as preview
from tools.capture_rose_video import source_hashes


def report_for(fps=30):
    frames = (36, 255, 330, 405, 420) if fps == 30 else (29, 204, 264, 324, 336)
    events = []
    for frame, seconds, action in zip(frames, (1.2, 8.5, 11, 13.5, 14),
                                      ("G", "C", "C", "C", "click")):
        events.append({"frame": frame, "requested_time": seconds,
                       "time": frame / fps, "action": action})
    events[-1]["logical_position"] = [90, 145]
    return {"work": 27, "frames": 600 if fps == 30 else 480, "fps": fps,
            "duration": 20, "warmup_seconds": 7, "events": events,
            "size": [16, 12], "source_sha256_lf": source_hashes()}


class ReportValidationTests(unittest.TestCase):
    def test_complete_story_at_both_supported_rates_is_accepted(self):
        for fps in (24, 30):
            with self.subTest(fps=fps):
                preview.validate_report(report_for(fps))

    def test_incomplete_story_invalid_size_and_stale_sources_are_rejected(self):
        report = report_for()
        changes = (("work", 28), ("fps", 30.0), ("fps", True), ("fps", 25),
                   ("fps", None), ("frames", 599), ("duration", 19.9),
                   ("warmup_seconds", 1), ("events", []),
                   ("source_sha256_lf", {}), ("size", [0, 12]),
                   ("size", [16, -1]), ("size", [16.0, 12]),
                   ("size", [True, 12]), ("size", [16]), ("size", "16x12"))
        for key, value in changes:
            with self.subTest(key=key, value=value):
                invalid = deepcopy(report)
                invalid[key] = value
                with self.assertRaises(ValueError):
                    preview.validate_report(invalid)
        invalid = deepcopy(report)
        invalid["events"][-1]["logical_position"] = [0, 0]
        with self.assertRaises(ValueError):
            preview.validate_report(invalid)


class CaptionTimingTests(unittest.TestCase):
    def test_fractional_cues_have_milliseconds_and_cover_the_complete_story(self):
        self.assertEqual(preview.timestamp(1.2), "00:00:01,200")
        self.assertEqual(preview.timestamp(13.5), "00:00:13,500")
        self.assertEqual(preview.CAPTIONS[0][0], 0)
        self.assertEqual(preview.CAPTIONS[-1][1], 20)
        previous_end = 0
        for start, end, text in preview.CAPTIONS:
            self.assertEqual(start, previous_end)
            self.assertGreater(end, start)
            self.assertTrue(text.strip())
            previous_end = end


class MemoryEncoder:
    """An encoder substitute that retains the real output lifecycle."""
    def __init__(self, executable, path, size, fps):
        self.path = Path(path)
        self.size, self.fps = size, fps
        self.aborted = False
        self.finished = False
        self.written = 0
        self.path.write_bytes(b"partial video")

    def write(self, pixels):
        if len(pixels) != self.size[0] * self.size[1] * 3:
            raise ValueError("Encoder received a wrong-sized RGB frame")
        self.written += 1

    def finish(self):
        self.path.write_bytes(b"finished video")
        self.finished = True

    def abort(self):
        self.aborted = True


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is optional")
class PreviewExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.output = self.root / "preview"
        self.report = report_for()
        # Export safety needs only a few frames; real story validation is above.
        self.report["frames"] = 3
        (self.capture / "capture.json").write_text(
            json.dumps(self.report), encoding="utf-8")
        self.encoders = []

        def make_encoder(*args):
            encoder = MemoryEncoder(*args)
            self.encoders.append(encoder)
            return encoder

        patches = (patch.object(preview, "validate_report"),
                   patch.object(preview, "_ffmpeg", return_value="unused"),
                   patch.object(preview, "fonts", return_value={}),
                   patch.object(preview, "compose", side_effect=lambda source, seconds, face:
                                source.convert("RGB").resize((1280, 720))),
                   patch.object(preview, "Encoder", side_effect=make_encoder))
        for replacement in patches:
            replacement.start()
            self.addCleanup(replacement.stop)

    def make_frames(self):
        from PIL import Image
        for index in range(3):
            Image.new("RGB", (16, 12), "#101025").save(
                self.capture / f"frame-{index:05d}.png")

    def assert_no_owned_output(self):
        for name in ("preview.mp4", "storyboard.jpg", "captions.zh.srt", "manifest.json"):
            self.assertFalse((self.output / name).exists(), name)
        self.assertEqual(len(list(self.capture.glob("frame-*.png"))), 3)

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            preview.produce(self.capture, self.output)
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(self.encoders, [])

    def test_missing_frames_fail_before_encoder_or_output_creation(self):
        with self.assertRaisesRegex(ValueError, "missing frames"):
            preview.produce(self.capture, self.output)
        self.assertEqual(self.encoders, [])
        self.assertFalse(self.output.exists())

    def test_changed_input_size_aborts_and_removes_partial_output(self):
        from PIL import Image
        self.make_frames()
        Image.new("RGB", (15, 12)).save(self.capture / "frame-00001.png")
        with self.assertRaisesRegex(ValueError, "size changed"):
            preview.produce(self.capture, self.output)
        self.assertEqual(len(self.encoders), 1)
        self.assertTrue(self.encoders[0].aborted)
        self.assert_no_owned_output()

    def test_write_failure_cleans_owned_files_and_preserves_unrelated_file(self):
        self.make_frames()
        encoders = []

        class BrokenEncoder(MemoryEncoder):
            def __init__(encoder, *args):
                super().__init__(*args)
                encoders.append(encoder)
                (encoder.path.parent / "keep.txt").write_text("keep", encoding="utf-8")

            def write(encoder, pixels):
                raise RuntimeError("injected write failure")

        with patch.object(preview, "Encoder", BrokenEncoder):
            with self.assertRaisesRegex(RuntimeError, "injected write failure"):
                preview.produce(self.capture, self.output)
        self.assertTrue(encoders[0].aborted)
        self.assert_no_owned_output()
        self.assertEqual((self.output / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_finish_failure_aborts_and_does_not_publish_a_manifest(self):
        self.make_frames()
        with patch.object(MemoryEncoder, "finish", side_effect=RuntimeError("injected finish failure")):
            with self.assertRaisesRegex(RuntimeError, "injected finish failure"):
                preview.produce(self.capture, self.output)
        self.assertTrue(self.encoders[0].aborted)
        self.assert_no_owned_output()

    def test_input_hashes_video_and_storyboard_share_one_read_and_manifest_matches_files(self):
        from PIL import Image
        self.make_frames()
        original = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in self.capture.glob("frame-*.png")}
        reads = Counter()
        read_bytes = Path.read_bytes
        first_pixels = []
        output = self.output
        first_frame = self.capture / "frame-00000.png"

        def read_once(path):
            if path.parent == self.capture and path.suffix == ".png":
                reads[path.name] += 1
            return read_bytes(path)

        class ChangingEncoder(MemoryEncoder):
            def write(encoder, pixels):
                super().write(pixels)
                if encoder.written == 1:
                    first_pixels.append(tuple(pixels[:3]))
                    Image.new("RGB", (16, 12), "white").save(first_frame)
                if (output / "manifest.json").exists():
                    raise AssertionError("Manifest published before encoding finished")

            def finish(encoder):
                if (output / "manifest.json").exists():
                    raise AssertionError("Manifest published before encoding finished")
                super().finish()

        with patch.object(Path, "read_bytes", read_once), \
                patch.object(preview, "Encoder", ChangingEncoder):
            result = preview.produce(self.capture, self.output)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result, manifest)
        self.assertEqual(reads, Counter({name: 1 for name in original}))
        self.assertEqual(manifest["input_frame_sha256"], original)
        self.assertNotEqual(hashlib.sha256(first_frame.read_bytes()).hexdigest(),
                            original[first_frame.name])
        self.assertEqual(first_pixels, [(16, 16, 37)])
        with Image.open(self.output / "storyboard.jpg") as board:
            for actual, expected in zip(board.convert("RGB").getpixel((320, 180)), (16, 16, 37)):
                self.assertLessEqual(abs(actual - expected), 2)
        self.assertEqual(manifest["status"], "silent rehearsal; not submitted")
        self.assertIs(manifest["audio"], False)
        self.assertEqual(manifest["size"], [1280, 720])
        self.assertEqual((manifest["frames"], manifest["fps"], manifest["duration"]), (3, 30, 20))
        self.assertEqual(manifest["capture"], self.report)
        self.assertEqual(set(manifest["files"]), {"preview.mp4", "storyboard.jpg", "captions.zh.srt"})
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(set(manifest["source_sha256_lf"]),
                         {"tools/render_rose_preview.py", "tools/render_video.py", "社团展示/高清导出.py"})
        repository = Path(__file__).resolve().parents[1]
        for name, expected in manifest["source_sha256_lf"].items():
            data = (repository / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
        self.assertNotIn(b"\r", (self.output / "captions.zh.srt").read_bytes())


class DeliveredRosePreviewTests(unittest.TestCase):
    def test_delivered_preview_files_and_sources_match_manifest(self):
        repository = Path(__file__).resolve().parents[1]
        assets = repository / "docs/assets/social-rose"
        manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        preview.validate_report(manifest["capture"])
        self.assertEqual(manifest["status"], "silent rehearsal; not submitted")
        self.assertIs(manifest["audio"], False)
        self.assertEqual(manifest["size"], [1280, 720])
        self.assertEqual((manifest["frames"], manifest["fps"], manifest["duration"]), (600, 30, 20))
        for key in ("frames", "fps", "duration"):
            self.assertEqual(manifest[key], manifest["capture"][key])
        self.assertEqual(set(manifest["files"]), {"preview.mp4", "storyboard.jpg", "captions.zh.srt"})
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((assets / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(set(manifest["source_sha256_lf"]),
                         {"tools/render_rose_preview.py", "tools/render_video.py", "社团展示/高清导出.py"})
        for name, expected in manifest["source_sha256_lf"].items():
            data = (repository / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected, name)
        frame_hashes = manifest["input_frame_sha256"]
        self.assertEqual(set(frame_hashes), {f"frame-{index:05d}.png" for index in range(600)})
        for value in frame_hashes.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
        srt = (assets / "captions.zh.srt").read_bytes()
        self.assertNotIn(b"\r", srt)
        for cue in (b"00:00:00,000", b"00:00:01,200", b"00:00:13,500", b"00:00:20,000"):
            self.assertIn(cue, srt)


if __name__ == "__main__":
    unittest.main()

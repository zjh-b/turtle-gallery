"""Check recording timing and the actual butterfly interaction callbacks."""
import hashlib
import json
import math
from pathlib import Path
import unittest

from test_demos import make_app
from tools import capture_butterfly_video, render_butterfly_preview


class ButterflyCaptureTests(unittest.TestCase):
    def setUp(self):
        self.capture = capture_butterfly_video

    def test_timeline_quantizes_events_and_trims_short_previews(self):
        for fps in (24, 30):
            frames, events = self.capture.timeline(fps, 20)
            self.assertEqual(frames, 20 * fps)
            self.assertEqual(len(events), 7)
            self.assertEqual(events[0]["frame"], round(.8 * fps))
            for event in events:
                self.assertAlmostEqual(event["time"], event["frame"] / fps)
                self.assertLess(event["frame"], frames)
            short_frames, short_events = self.capture.timeline(fps, .5)
            self.assertEqual(short_frames, math.ceil(.5 * fps))
            self.assertEqual(short_events, [])

    def test_invalid_capture_lengths_and_rates_are_rejected(self):
        for seconds in (0, -1, 20.1, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.capture.timeline(30, seconds)
        for fps in (0, 15, True, 30.0):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                self.capture.timeline(fps, 20)

    def test_click_uses_logical_coordinates_at_a_scaled_window(self):
        app = make_app("NeonButterfly")
        app.stage.screen.setup(1500, 1080)
        _, events = self.capture.timeline(30, 20)
        self.capture.apply_event(app, events[0])
        self.assertEqual(app.target, [280.0, 150.0, 6.0])
        with self.assertRaises(ValueError):
            self.capture.apply_event(app, {"action": "close"})

    def test_story_reaches_three_themes_and_holds_only_position(self):
        app = make_app("NeonButterfly")
        fps = 24
        count, events = self.capture.timeline(fps, 20)
        themes, frozen, frozen_time = set(), None, None
        for index in range(count):
            self.capture.render_frame(app, index, fps, events)
            themes.add(app.theme)
            if index == round(10.5 * fps):
                frozen, frozen_time = app.offset[:], app.time
            if round(10.5 * fps) < index < 14 * fps:
                self.assertEqual(app.offset, frozen)
                self.assertGreater(app.time, frozen_time)
        self.assertEqual(themes, {0, 1, 2})
        self.assertTrue(app.motion)
        self.assertNotEqual(app.offset, frozen)
        self.assertEqual(app.target[:2], [230, 145])


class ButterflyPreviewTests(unittest.TestCase):
    def setUp(self):
        self.preview = render_butterfly_preview
        from tools.capture_butterfly_video import source_hashes, timeline
        frames, events = timeline(30, 20)
        self.report = {"work": 28, "fps": 30, "frames": frames, "duration": 20,
                       "size": [1000, 550], "events": events,
                       "source_sha256_lf": source_hashes()}

    def test_stale_or_unexpected_sources_are_rejected(self):
        self.preview.validate_report(self.report)
        first = next(iter(self.report["source_sha256_lf"]))
        self.report["source_sha256_lf"][first] = "stale"
        with self.assertRaises(ValueError):
            self.preview.validate_report(self.report)
        self.report["source_sha256_lf"]["../unknown.py"] = "unknown"
        with self.assertRaises(ValueError):
            self.preview.validate_report(self.report)

    def test_partial_or_different_stories_are_rejected(self):
        for field, wrong in (("work", 29), ("frames", 599), ("fps", 60),
                             ("duration", 19), ("events", []), ("size", [0, 700])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.preview.validate_report(dict(self.report, **{field: wrong}))


class DeliveredButterflyPreviewTests(unittest.TestCase):
    def test_delivered_preview_matches_its_sources_and_files(self):
        from tools.render_butterfly_preview import validate_report
        root = Path(__file__).resolve().parents[1]
        assets = root / "docs/assets/social-butterfly"
        manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        validate_report(manifest["capture"])
        self.assertEqual(manifest["status"], "silent rehearsal; not submitted")
        self.assertFalse(manifest["audio"])
        self.assertEqual(manifest["size"], [1280, 720])
        self.assertEqual(set(manifest["files"]),
                         {"preview.mp4", "storyboard.jpg", "captions.zh.srt"})
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((assets / name).read_bytes()).hexdigest(), expected)
        for name, expected in manifest["source_sha256_lf"].items():
            data = (root / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
        self.assertEqual(set(manifest["input_frame_sha256"]),
                         {f"frame-{index:05d}.png" for index in range(manifest["frames"])})
        # Git enforces LF for SRT. Windows output must already use LF so that
        # its recorded byte hash survives checkout on every CI platform.
        self.assertNotIn(b"\r", (assets / "captions.zh.srt").read_bytes())


if __name__ == "__main__":
    unittest.main()

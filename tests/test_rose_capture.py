"""Headless checks for the rose story and the window capture lifecycle."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_demos import HeadlessStage, STAGE, make_app
from 社团展示 import 作品导出 as artwork_export

try:
    from tools import capture_rose_video
except ImportError:
    capture_rose_video = None


class RoseCaptureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(capture_rose_video, "Rose capture tool is missing")
        self.capture = capture_rose_video

    def test_timeline_quantizes_replay_and_trims_events_at_the_end(self):
        for fps, expected in ((24, [29, 204, 264, 324, 336]),
                              (30, [36, 255, 330, 405, 420])):
            with self.subTest(fps=fps):
                frames, events = self.capture.timeline(fps, 20)
                self.assertEqual(frames, 20 * fps)
                self.assertEqual([event["frame"] for event in events], expected)
                self.assertEqual([event["action"] for event in events],
                                 ["G", "C", "C", "C", "click"])
                self.assertEqual([event["requested_time"] for event in events],
                                 [1.2, 8.5, 11, 13.5, 14])
                self.assertEqual(events[-1]["logical_position"], [90, 145])
                for event in events:
                    self.assertEqual(event["time"], event["frame"] / fps)
                self.assertEqual(self.capture.timeline(fps, 1), (fps, []))
                _, short = self.capture.timeline(fps, 14)
                self.assertEqual([event["action"] for event in short],
                                 ["G", "C", "C", "C"])
        self.assertEqual(self.capture.timeline(30, .001), (1, []))

    def test_invalid_capture_lengths_and_rates_are_rejected(self):
        for seconds in (0, -1, 20.1, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.capture.timeline(30, seconds)
        for fps in (0, 15, True, 30.0):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                self.capture.timeline(fps, 20)

    def test_warmup_records_a_mature_flower_without_advancing_first_frame(self):
        for fps in (24, 30):
            with self.subTest(fps=fps):
                app = make_app("GalaxyRose")
                self.capture.prepare_scene(app, fps)
                self.assertEqual(app.growth, 7)
                self.assertEqual(app.time, 7)
                self.capture.render_frame(app, 0, fps, [])
                self.assertEqual(app.growth, 7)
                self.assertEqual(app.time, 7)
                visible = [item for item in app.stage.canvas.items.values()
                           if item["options"].get("state") != "hidden"]
                self.assertGreater(sum(item["kind"] == "polygon" for item in visible), 100)

    def test_replay_preserves_background_time_theme_speed_and_stardust(self):
        app = make_app("GalaxyRose")
        app.frame(7)
        app.change_theme()
        app.change_speed(.5)
        app.stardust(0, 0)
        self.capture.apply_event(app, {"action": "G"})
        self.assertEqual(app.growth, 0)
        self.assertEqual((app.time, app.theme, app.speed, len(app.particles)),
                         (7, 1, 1.5, 24))
        with self.assertRaises(ValueError):
            self.capture.apply_event(app, {"action": "close"})

    def test_click_uses_logical_coordinates_at_a_scaled_window(self):
        app = make_app("GalaxyRose")
        app.stage.screen.setup(1500, 1080)
        self.capture.apply_event(app, {"action": "click", "logical_position": [90, 145]})
        self.assertEqual(len(app.particles), 24)
        self.assertTrue(all(particle[:2] == [90, 145] for particle in app.particles))
        sample = self.capture.state(app, 420, 30)
        self.assertEqual(sample["time"], 14)
        self.assertEqual(sample["particle_count"], 24)
        self.assertEqual(sample["growth"], 0)
        self.assertEqual(sample["scene_time"], 0)
        self.assertEqual(sample["theme"], 0)
        self.assertEqual(sample["speed"], 1)

    def test_story_replays_growth_cycles_themes_and_expires_stardust(self):
        app = make_app("GalaxyRose")
        fps = 24
        self.capture.prepare_scene(app, fps)
        frames, events = self.capture.timeline(fps, 20)
        themes, previous_time = set(), app.time
        for index in range(frames):
            self.capture.render_frame(app, index, fps, events)
            themes.add(app.theme)
            if index:
                self.assertGreater(app.time, previous_time)
            previous_time = app.time
            if index == 28:
                self.assertEqual(app.growth, 7)
            elif index == 29:
                self.assertAlmostEqual(app.growth, 1 / 24)
            elif index == 204:
                self.assertEqual((app.growth, app.theme), (7, 1))
            elif index == 264:
                self.assertEqual(app.theme, 2)
            elif index == 324:
                self.assertEqual(app.theme, 0)
            elif index == 336:
                self.assertEqual(len(app.particles), 24)
            elif index == 395:
                self.assertEqual(app.particles, [])
        self.assertEqual(themes, {0, 1, 2})
        self.assertEqual(app.growth, 7)
        self.assertEqual(app.speed, 1)
        self.assertEqual(app.particles, [])

    def test_closed_window_stops_warmup_and_recording(self):
        app = make_app("GalaxyRose")
        app.stage.close()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.capture.prepare_scene(app, 30)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.capture.render_frame(app, 36, 30, [{"frame": 36, "action": "G"}])
        self.assertEqual(app.time, 0)

    def test_source_hashes_normalize_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scene.py"
            source.write_bytes(b"one\r\ntwo\r\n")
            with patch.object(self.capture, "ROOT", root), \
                    patch.object(self.capture, "SOURCES", (source,)):
                self.assertEqual(self.capture.source_hashes(), {
                    "scene.py": hashlib.sha256(b"one\ntwo\n").hexdigest()})


class Snapshot:
    """Only the external screenshot is replaced; the scene still draws."""
    def __init__(self, size=(1000, 550)):
        self.size = size

    def save(self, path):
        path.write_bytes(b"headless window screenshot fixture")


@contextmanager
def capture_window(snapshot=None, update=None):
    stages = []

    def create_stage(*args, **kwargs):
        stage = HeadlessStage(*args, **kwargs)
        stage.root.geometry = Mock()
        stage.root.update = Mock()
        stage.root.winfo_screenwidth = lambda: 1920
        stage.root.winfo_screenheight = lambda: 1080
        if update:
            stage.screen.update.side_effect = lambda: update(stage)
        stages.append(stage)
        return stage

    with patch.dict(sys.modules, {"舞台": STAGE}), \
            patch.object(STAGE, "Stage", side_effect=create_stage), \
            patch.object(artwork_export, "export_support", return_value=(True, "")), \
            patch.object(artwork_export, "capture_artwork", side_effect=snapshot or (lambda stage: Snapshot())):
        yield stages


class RoseCaptureLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(capture_rose_video, "Rose capture tool is missing")
        self.capture = capture_rose_video

    def test_capture_writes_complete_manifest_and_keeps_only_escape_bound(self):
        with tempfile.TemporaryDirectory() as directory, capture_window() as stages:
            output = Path(directory) / "frames"
            report = self.capture.capture(output, 30, .1)
            self.assertEqual(json.loads((output / "capture.json").read_text(encoding="utf-8")), report)
            self.assertEqual(sorted(path.name for path in output.glob("*.png")),
                             ["frame-00000.png", "frame-00001.png", "frame-00002.png"])
            self.assertEqual((report["work"], report["frames"], report["fps"]), (27, 3, 30))
            self.assertEqual((report["warmup_seconds"], report["duration"]), (7, .1))
            self.assertEqual(report["size"], [1000, 550])
            self.assertEqual(report["frame_pattern"], "frame-%05d.png")
            self.assertEqual(report["state_samples"][0]["growth"], 7)
            self.assertEqual(report["state_samples"][0]["scene_time"], 7)
            self.assertEqual(set(report["source_sha256_lf"]), {
                "社团展示/27_星河玫瑰.py", "社团展示/舞台.py",
                "社团展示/作品导出.py", "tools/capture_rose_video.py"})
            stage = stages[0]
            self.assertTrue(stage.closed)
            self.assertIsNone(stage.screen.click)
            self.assertEqual({key for key, callback in stage.screen.keys.items() if callback},
                             {"Escape"})

    def test_existing_output_is_rejected_before_opening_a_window(self):
        with tempfile.TemporaryDirectory() as directory, capture_window() as stages:
            marker = Path(directory) / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.capture.capture(directory)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertEqual(stages, [])

    def test_size_change_and_screenshot_failure_do_not_publish_manifest(self):
        for failure in (Snapshot((999, 550)), RuntimeError("screenshot failed")):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, \
                    capture_window(snapshot=Mock(side_effect=[Snapshot(), failure])) as stages:
                output = Path(directory) / "frames"
                with self.assertRaises(RuntimeError):
                    self.capture.capture(output, 30, .1)
                self.assertFalse((output / "capture.json").exists())
                self.assertTrue(stages[0].closed)

    def test_source_change_does_not_publish_manifest(self):
        original = self.capture.source_hashes()
        changed = dict(original, **{"社团展示/27_星河玫瑰.py": "changed"})
        with tempfile.TemporaryDirectory() as directory, capture_window() as stages, \
                patch.object(self.capture, "source_hashes", side_effect=[original, changed]):
            output = Path(directory) / "frames"
            with self.assertRaisesRegex(RuntimeError, "Sources changed"):
                self.capture.capture(output, 30, .1)
            self.assertFalse((output / "capture.json").exists())
            self.assertTrue(stages[0].closed)

    def test_early_close_during_warmup_does_not_publish_manifest(self):
        with tempfile.TemporaryDirectory() as directory, \
                capture_window(update=lambda stage: stage.close()) as stages:
            output = Path(directory) / "frames"
            with self.assertRaisesRegex(RuntimeError, "closed"):
                self.capture.capture(output, 30, .1)
            self.assertFalse((output / "capture.json").exists())
            self.assertFalse(list(output.glob("*.png")))
            self.assertTrue(stages[0].closed)

    def test_close_on_last_screenshot_does_not_publish_manifest(self):
        def close_window(stage):
            stage.close()
            return Snapshot()

        with tempfile.TemporaryDirectory() as directory, \
                capture_window(snapshot=close_window) as stages:
            output = Path(directory) / "frames"
            with self.assertRaisesRegex(RuntimeError, "closed"):
                self.capture.capture(output, 30, .001)
            self.assertFalse((output / "capture.json").exists())
            self.assertTrue(stages[0].closed)


if __name__ == "__main__":
    unittest.main()

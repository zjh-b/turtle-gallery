"""The video adapter samples the real artworks without opening a desktop."""
import copy
import importlib
import importlib.util
from pathlib import Path
import sys
import tkinter
import turtle
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from video_scene import SceneFrames


class VideoSceneTests(unittest.TestCase):
    def test_real_initialization_and_rendering_never_create_a_window_or_patch_stage(self):
        stage = importlib.import_module("舞台")
        original_stage, original_paint = stage.Stage, stage.Paint
        with patch.object(turtle, "Screen", side_effect=AssertionError("Opened Turtle")), \
                patch.object(tkinter, "Tk", side_effect=AssertionError("Opened Tk")):
            for work_id in (25, 26):
                scene = SceneFrames(work_id)
                commands = scene.commands(1 / 30)
                self.assertGreater(len(commands), 200)
                self.assertEqual(scene.view, (540, 960))
                self.assertIs(stage.Stage, original_stage)
                self.assertIs(stage.Paint, original_paint)
        self.assertIsNone(tkinter._default_root)

    def test_seeded_inputs_repeat_the_same_frames_and_hold_does_not_advance(self):
        for work_id in (25, 26):
            for fps in (24, 30):
                with self.subTest(work=work_id, fps=fps):
                    first = SceneFrames(work_id, {"seed": 810, "theme": 1}, fps)
                    second = SceneFrames(work_id, {"seed": 810, "theme": 1}, fps)
                    for index in range(18):
                        if index == 4:
                            action = "meteor" if work_id == 25 else "burst"
                            first.event(action, 30, 40)
                            second.event(action, 30, 40)
                        if index == 11:
                            first.event("theme")
                            second.event("theme")
                        self.assertEqual(first.commands(1 / fps), second.commands(1 / fps))
                    held = first.commands()
                    animation_time = first.app.time
                    self.assertEqual(first.commands(), held)
                    self.assertEqual(first.app.time, animation_time)
                    self.assertNotEqual(first.commands(1 / fps), held)

    def test_recorded_inputs_follow_real_bloom_meteor_and_burst_lifetimes(self):
        lily = SceneFrames(25, {"speed": 2})
        lily.commands(1 / 30)
        self.assertAlmostEqual(lily.app.bloom, 2 / 30)
        lily.event("meteor", 20, 40)
        self.assertEqual(lily.app.meteors, [[20, 40, 0]])
        lily.commands(1 / 30)
        self.assertAlmostEqual(lily.app.meteors[0][2], 1 / 30)
        lily.event("replay")
        self.assertEqual(lily.app.bloom, 0)
        self.assertAlmostEqual(lily.app.time, 4 / 30)
        for _ in range(50):
            lily.commands(1 / 30)
        self.assertEqual(lily.app.meteors, [])
        heart = SceneFrames(26)
        heart.event("burst", 0, 0)
        self.assertEqual(heart.app.burst_age, 0)
        heart.commands(1 / 30)
        self.assertAlmostEqual(heart.app.burst_age, 1 / 30)
        for _ in range(108):
            heart.commands(1 / 30)
        self.assertIsNone(heart.app.burst_age)
        heart.event("burst", 9999, 9999)
        self.assertIsNone(heart.app.burst_age)

    def test_lettering_filter_keeps_every_nontext_vector_and_snapshots_are_independent(self):
        for work_id in (25, 26):
            labelled = SceneFrames(work_id)
            clean = SceneFrames(work_id, hide_lettering=True)
            source = labelled.commands(1 / 30)
            filtered = clean.commands(1 / 30)
            self.assertIsInstance(source, tuple)
            self.assertTrue(any(kind == "text" for kind, _, _ in source))
            self.assertEqual(filtered, tuple(item for item in source if item[0] != "text"))
            previous = copy.deepcopy(source)
            labelled.commands(1 / 30)
            self.assertEqual(source, previous)
            source[0][2]["fill"] = "#FFFFFF"
            self.assertNotEqual(source, labelled.commands())

    def test_invalid_configuration_is_rejected(self):
        for work_id in (True, "25", 24, 27, None):
            with self.subTest(work=work_id), self.assertRaises(ValueError):
                SceneFrames(work_id)
        for fps in (True, "30", 30.0, 0, 29, 60, None):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                SceneFrames(25, fps=fps)
        for parameters in ({"aspect": 0}, {"aspect": 4}, {"seed": -1},
                           {"theme": 3}, {"speed": float("nan")}, {"unknown": 1}):
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                SceneFrames(25, parameters)

    def test_invalid_steps_and_events_do_not_mutate_animation(self):
        for work_id in (25, 26):
            scene = SceneFrames(work_id)
            before = scene.commands()
            for dt in (-1, 1, 1 / 24, True, "0", float("nan"), float("inf")):
                with self.subTest(work=work_id, dt=dt), self.assertRaises(ValueError):
                    scene.commands(dt)
            unsupported = "burst" if work_id == 25 else "replay"
            for action, x, y in ((unsupported, 0, 0), ("reset", 0, 0),
                                 (None, 0, 0), ("theme", True, 0),
                                 ("theme", float("nan"), 0), ("theme", 0, float("inf"))):
                with self.subTest(work=work_id, action=action), self.assertRaises(ValueError):
                    scene.event(action, x, y)
            self.assertEqual(scene.commands(), before)

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is optional")
    def test_pillow_renders_authentic_frames_without_fonts_when_lettering_is_hidden(self):
        from PIL import ImageChops
        for work_id in (25, 26):
            scene = SceneFrames(work_id, hide_lettering=True)
            with scene.render((180, 320), (None, None)) as initial:
                for _ in range(35):
                    scene.commands(1 / 30)
                with scene.render((180, 320), (None, None), 1 / 30) as later:
                    self.assertEqual(later.size, (180, 320))
                    self.assertEqual(later.mode, "RGB")
                    self.assertIsNotNone(ImageChops.difference(initial, later).getbbox())


if __name__ == "__main__":
    unittest.main()

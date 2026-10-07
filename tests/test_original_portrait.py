"""Eye tracking, transient expressions and safe input on the original portrait."""
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalPortraitTests(unittest.TestCase):
    def setUp(self):
        self.module = load_original('哆啦A梦.py')
        with patch.object(self.module, 'Stage', HeadlessStage):
            self.app = self.module.DoraemonPortrait()

    def test_pupils_stay_inside_each_eye_for_extreme_targets(self):
        for target in ((-500, 250), (500, -280), (0, 250), (0, -280)):
            for eye_x in (-38, 38):
                dx, dy = self.module.pupil_offset(eye_x, *target)
                self.assertLessEqual((dx / 9) ** 2 + (dy / 11) ** 2, 1 + 1e-10)
                self.assertLess(abs(dx) + 12, 37)
                self.assertLess(abs(dy) + 23, 48)

    def test_click_uses_scaled_scene_coordinates_and_target_expires(self):
        self.app.stage.screen.width, self.app.stage.screen.height = 760, 580
        scale = self.app.stage.scale
        self.app.look(240 * scale, 180 * scale)
        self.assertAlmostEqual(self.app.target[0], 240)
        self.assertAlmostEqual(self.app.target[1], 180)
        self.app.frame(.2)
        self.assertGreater(self.app.gaze[0], 0)
        self.app.frame(5)
        self.assertIsNone(self.app.target)
        self.assertAlmostEqual(self.app.gaze[0], 0, places=5)

    def test_manual_blink_closes_then_opens_and_pause_freezes_it(self):
        self.app.blink()
        self.app.frame(.16)
        self.assertLess(self.app.eye_open(), .1)
        self.app.stage.paused = True
        before = state(self.app)
        self.app.frame(0)
        self.app.blink()
        self.app.look(0, -184 * self.app.stage.scale)
        self.assertEqual(state(self.app), before)
        self.app.stage.paused = False
        self.app.frame(.17)
        self.assertGreater(self.app.eye_open(), .99)

    def test_bell_hit_is_local_and_ringing_expires(self):
        self.app.stage.screen.width, self.app.stage.screen.height = 760, 580
        scale = self.app.stage.scale
        self.app.look(80 * scale, -184 * scale)
        self.assertEqual(self.app.ring, 0)
        self.app.look(0, -184 * scale)
        self.assertGreater(self.app.ring, 0)
        self.app.frame(2)
        self.assertEqual(self.app.ring, 0)
        before = state(self.app)
        self.app.look(0, 400 * scale)
        self.assertEqual(state(self.app), before)

    def test_expressions_and_repeated_interaction_keep_a_fixed_size_scene(self):
        for _ in range(3):
            for step in range(35):
                self.app.look(0, -184 * self.app.stage.scale)
                if step % 7 == 0:
                    self.app.toggle_smile()
                    self.app.cycle_palette()
                self.app.frame(.04)
            self.assertLess(len(self.app.stage.canvas.items), 650)
        count = len(self.app.stage.canvas.items)
        for _ in range(100):
            self.app.frame(.04)
        self.assertEqual(len(self.app.stage.canvas.items), count)


if __name__ == '__main__':
    unittest.main()

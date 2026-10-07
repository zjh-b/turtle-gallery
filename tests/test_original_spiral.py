"""The original forward/turn/square rule stays intact in its gallery presentation."""
import math
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalSpiralTests(unittest.TestCase):
    def app(self):
        module = load_original('import turtle.py')
        with patch.object(module, 'Stage', HeadlessStage):
            app = module.SquareSpiral()
        return module, app

    def test_original_44_degree_rule_starts_with_hand_checked_coordinates(self):
        module = load_original('import turtle.py')
        squares = module.square_geometry(44, 230)
        self.assertEqual(len(squares), 230)
        self.assertEqual(squares[0][0], (0, 0))
        self.assertAlmostEqual(squares[0][1][0], 3.596699001693256)
        self.assertAlmostEqual(squares[0][1][1], -3.4732918522949863)
        self.assertAlmostEqual(squares[1][0][0], .7193398003386512)
        self.assertAlmostEqual(squares[1][0][1], -.6946583704589973)
        self.assertAlmostEqual(squares[1][1][0], .8981997209389677)
        self.assertAlmostEqual(squares[1][1][1], -5.816536362868289)

    def test_all_presets_close_four_equal_perpendicular_sides_and_fit_the_stage(self):
        module = load_original('import turtle.py')
        for angle in module.ANGLE_PRESETS:
            raw = module.square_geometry(angle)
            normalized = module.fit_geometry(raw)
            for index, square in enumerate(raw):
                self.assertEqual(len(square), 5)
                self.assertEqual(square[0], square[-1])
                edges = [(b[0] - a[0], b[1] - a[1])
                         for a, b in zip(square, square[1:])]
                for dx, dy in edges:
                    self.assertAlmostEqual(math.hypot(dx, dy), 5 + index / 8)
                self.assertAlmostEqual(sum(a * b for a, b in zip(edges[0], edges[1])), 0)
            for square in normalized:
                for x, y in square:
                    self.assertLessEqual(math.hypot(x, y), 235)

    def test_replay_uses_elapsed_time_and_stops_at_the_complete_drawing(self):
        _, first = self.app()
        _, second = self.app()
        self.assertEqual(first.progress, 230)
        first.replay()
        second.replay()
        for _ in range(100):
            first.frame(.01)
        for _ in range(10):
            second.frame(.1)
        self.assertAlmostEqual(first.progress, second.progress)
        self.assertGreater(first.progress, 0)
        self.assertLess(first.progress, 230)
        first.frame(100)
        self.assertEqual(first.progress, 230)

    def test_replay_reveals_real_square_lines_and_speed_changes_its_duration(self):
        _, app = self.app()

        def visible_lines():
            return sum(item['kind'] == 'line' and item['options']['state'] == 'normal'
                       for item in app.stage.canvas.items.values()
                       if 'square-spiral-lines' in item['options'].get('tags', ()))

        app.frame(0)
        complete = visible_lines()
        self.assertGreaterEqual(complete, 230)
        app.replay()
        app.frame(0)
        self.assertEqual(visible_lines(), 0)
        app.frame(.5)
        normal = app.progress
        self.assertGreater(visible_lines(), 0)
        self.assertLess(visible_lines(), complete)
        app.replay()
        app.change_speed(1)
        app.frame(.5)
        self.assertAlmostEqual(app.progress, 2 * normal)
        app.frame(20)
        self.assertEqual(visible_lines(), complete)

    def test_paused_replay_and_outside_click_leave_progress_unchanged(self):
        _, app = self.app()
        app.frame(.2)
        before = state(app)
        app.frame(0)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        app.stage.screen.keys['g']()
        app.stage.screen.click(0, 0)
        self.assertEqual(state(app), before)
        app.stage.screen.keys['c']()
        self.assertNotEqual(app.palette, before['palette'])
        self.assertEqual(app.progress, before['progress'])
        app.stage.paused = False
        app.stage.screen.click(0, 320 * app.stage.scale)
        self.assertEqual(app.progress, 230)
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.stage.screen.click(100 * app.stage.scale, 60 * app.stage.scale)
        self.assertEqual(app.progress, 0)

    def test_complete_frames_reuse_static_geometry_and_interactions_stay_bounded(self):
        module, app = self.app()
        app.frame(.04)
        ids = set(app.stage.canvas.items)
        updates = app.stage.canvas.coordinate_updates
        for _ in range(15):
            app.frame(.04)
        self.assertEqual(set(app.stage.canvas.items), ids)
        self.assertLess(app.stage.canvas.coordinate_updates - updates, 250)
        for _ in range(9):
            app.stage.screen.keys['c']()
            app.stage.screen.keys['Right']()
            app.replay()
            app.frame(.1)
            app.frame(20)
        self.assertLess(len(app.stage.canvas.items), 1200)
        self.assertEqual(app.angle, 44)
        self.assertTrue({'Left', 'Right', 'Up', 'Down', 'g', 'c'} <= app.stage.screen.keys.keys())
        for _ in range(30):
            app.stage.screen.keys['Down']()
        self.assertGreater(app.speed, 0)


if __name__ == '__main__':
    unittest.main()

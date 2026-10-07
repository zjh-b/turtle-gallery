"""The original two semicircles remain a closed, interactive heart."""
import math
import unittest
from unittest.mock import Mock, patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalHeartTests(unittest.TestCase):
    def app(self):
        module = load_original('xin.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return module, module.ArcHeart()

    def test_import_does_not_start_turtle_or_mainloop(self):
        opened = []
        with patch('turtle.Turtle', side_effect=lambda: opened.append('pen') or Mock()), \
                patch('turtle.done', side_effect=lambda: opened.append('mainloop')):
            load_original('xin.py')
        self.assertEqual(opened, [])

    def test_semicircle_path_closes_and_has_mirrored_sides(self):
        module, _ = self.app()
        point = module.heart_point
        for progress in (0, .03, .12, .29, .38, .5, .72, 1):
            a, b = point(progress), point(1 - progress)
            self.assertAlmostEqual(a[0], -b[0])
            self.assertAlmostEqual(a[1], b[1])
        self.assertLess(math.dist(point(0), point(1)), 1e-8)
        # With radius sqrt(2), shoulders are (+/-2, -1) and tip is (0, -3).
        first_arc = math.pi / (2 * math.pi + 4)
        shoulder = point(first_arc, math.sqrt(2))
        self.assertAlmostEqual(shoulder[0], 2)
        self.assertAlmostEqual(shoulder[1], -1)
        self.assertAlmostEqual(point(.5, math.sqrt(2))[1], -3)

    def test_hits_follow_heart_shape_scale_and_replay_visibility(self):
        module, app = self.app()
        for size in ((1000, 720), (760, 580)):
            app.stage.screen.width, app.stage.screen.height = size
            app.frame(.21)
            cx, cy, zoom = app.pose()
            before = state(app)
            # Above the notch is empty, although it is inside the bounding box.
            app.pulse(cx * app.stage.scale, (cy + 100 * zoom) * app.stage.scale)
            self.assertEqual(state(app), before)
            # Below the diagonal shoulder is also empty.
            app.pulse((cx + 170 * zoom) * app.stage.scale,
                      (cy - 140 * zoom) * app.stage.scale)
            self.assertEqual(state(app), before)
            app.pulse(cx * app.stage.scale, cy * app.stage.scale)
            self.assertEqual(app.burst_age, 0)
            app.frame(module.BURST_SECONDS)
            self.assertIsNone(app.burst_age)
        app.replay()
        app.pulse(0, 0)
        self.assertIsNone(app.burst_age)

    def test_pause_freezes_replay_and_click_effects(self):
        _, app = self.app()
        app.frame(.1)
        app.stage.paused = True
        frozen = state(app)
        app.replay()
        app.pulse(0, 0)
        app.frame(0)
        self.assertEqual(state(app), frozen)

    def test_hit_boundary_tracks_the_pulsing_surface(self):
        module, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.frame(.37)
        cx, cy, zoom = app.pose()
        # Rightmost point of the r=110 semicircle is r + r/sqrt(2).
        edge = 187.78174593052023
        app.pulse((cx + (edge + .1) * zoom) * app.stage.scale,
                  cy * app.stage.scale)
        self.assertIsNone(app.burst_age)
        app.pulse((cx + (edge - .1) * zoom) * app.stage.scale,
                  cy * app.stage.scale)
        self.assertEqual(app.burst_age, 0)
        app.frame(module.BURST_SECONDS)
        self.assertIsNone(app.burst_age)

    def test_replay_finishes_preserves_palette_and_restarts_outline(self):
        module, app = self.app()
        app.cycle_palette()
        app.replay()
        self.assertEqual(app.progress, 0)
        app.frame(module.TRACE_SECONDS / 2)
        self.assertAlmostEqual(app.progress, .5)
        app.frame(module.TRACE_SECONDS)
        self.assertEqual(app.progress, 1)
        self.assertEqual(app.palette, 1)
        app.replay()
        self.assertEqual(app.progress, 0)

    def test_heartbeat_tracks_elapsed_time_and_rate_bounds(self):
        _, first = self.app()
        _, second = self.app()
        for _ in range(10):
            first.frame(.1)
        second.frame(1)
        self.assertAlmostEqual(first.phase, second.phase)
        self.assertAlmostEqual(first.pose()[2], second.pose()[2])
        first.change_speed(-100)
        self.assertGreater(first.speed, 0)
        first.change_speed(100)
        self.assertLessEqual(first.speed, 2)

    def test_repeated_clicks_palette_and_replay_keep_canvas_bounded(self):
        _, app = self.app()
        counts = []
        for _ in range(3):
            app.cycle_palette()
            for step in range(80):
                if step % 8 == 0:
                    app.pulse(0, 0)
                app.frame(.05)
            app.replay()
            app.frame(.1)
            app.frame(8)
            counts.append(len(app.stage.canvas.items))
        self.assertLess(max(counts), 1200)
        self.assertLessEqual(counts[-1], counts[-2] + 5)
        self.assertTrue({'c', 'g', 'Up', 'Down', 'space', 'F11'} <= set(app.stage.screen.keys))


if __name__ == '__main__':
    unittest.main()

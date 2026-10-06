"""Geometry, elapsed-time motion and bounded input for the original Taiji."""
import math
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


def contains(points, x, y):
    """Ray crossing, independent from the artwork's arc construction."""
    inside = False
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


class OriginalTaijiTests(unittest.TestCase):
    def app(self):
        module = load_original('太极.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return getattr(module, 'YinYang')()

    def test_fish_is_half_a_disc_with_complementary_lobes(self):
        module = load_original('太极.py')
        radius = 184
        points = module.fish_path(radius)
        area = abs(sum(ax * by - ay * bx for (ax, ay), (bx, by)
                       in zip(points, points[1:] + points[:1]))) / 2
        self.assertAlmostEqual(area / (math.pi * radius ** 2), .5, delta=.0002)
        self.assertTrue(all(math.hypot(x, y) <= radius + 1e-9 for x, y in points))
        self.assertTrue(contains(points, 0, radius / 2))
        self.assertFalse(contains(points, 0, -radius / 2))
        # The 180-degree counterpart fills the rest, with no overlap or gap.
        for x in range(-170, 171, 17):
            for y in range(-170, 171, 17):
                x1, y1 = x + .137, y + .293
                if math.hypot(x1, y1) < radius - 1:
                    self.assertNotEqual(contains(points, x1, y1), contains(points, -x1, -y1))

    def test_pause_and_invalid_clicks_leave_artwork_state_unchanged(self):
        app = self.app()
        app.frame(.1)
        before = state(app)
        app.frame(0)
        self.assertEqual(state(app), before)
        for x, y in ((0, 280), (501, 0), (0, -290)):
            app.ripple(x * app.stage.scale, y * app.stage.scale)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        app.ripple(0, 0)
        self.assertEqual(state(app), before)
        self.assertTrue({'c', 'C', 'd', 'D', 'l', 'L', 'Up', 'Down'} <= set(app.stage.screen.keys))

    def test_rotation_uses_elapsed_time_and_supports_reverse_and_stop(self):
        first, second = self.app(), self.app()
        for _ in range(100):
            first.frame(.01)
        for _ in range(10):
            second.frame(.1)
        self.assertAlmostEqual(first.angle, second.angle, places=12)
        first.reverse()
        angle = first.angle
        first.frame(.1)
        self.assertAlmostEqual((first.angle - angle) % math.tau,
                               (-first.ROTATION_RATE * first.speed * .1) % math.tau)
        first.change_speed(-100)
        angle = first.angle
        first.frame(1)
        self.assertEqual(first.angle, angle)
        first.change_speed(100)
        self.assertEqual(first.speed, 3)

    def test_ripples_expire_and_repeated_controls_keep_canvas_bounded(self):
        app = self.app()
        for index in range(80):
            app.ripple((index - 40) * app.stage.scale, 30 * app.stage.scale)
        self.assertEqual(len(app.ripples), app.RIPPLE_SLOTS)
        self.assertTrue(all(value is not None for value in app.ripples))
        self.assertAlmostEqual(app.ripples[(app.ripple_cursor - 1) % app.RIPPLE_SLOTS][0], 39)
        app.frame(app.RIPPLE_SECONDS)
        self.assertTrue(all(value is None for value in app.ripples))
        peaks = []
        for _ in range(3):
            for frame in range(24):
                if frame % 4 == 0:
                    app.change_palette()
                    app.toggle_ornament()
                    app.ripple(120 * app.stage.scale, 20 * app.stage.scale)
                app.frame(.05)
            peaks.append(len(app.stage.canvas.items))
        self.assertLess(max(peaks), 650)
        self.assertLessEqual(peaks[-1], peaks[-2] + 2)


if __name__ == '__main__':
    unittest.main()

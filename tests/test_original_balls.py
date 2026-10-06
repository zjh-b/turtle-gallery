"""Physical invariants and bounded input for the original ball scene."""
import math
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


def ball(x, y, vx, vy, radius=24):
    return dict(x=x, y=y, vx=vx, vy=vy, r=radius, color=0, flash=0.)


class OriginalBallTests(unittest.TestCase):
    def setUp(self):
        self.module = load_original('下落的小球.py')
        with patch.object(self.module, 'Stage', HeadlessStage):
            self.app = self.module.PrismBalls()

    def test_head_on_collision_preserves_momentum_and_energy(self):
        a, b = ball(-20, 0, 60, 0), ball(20, 0, -40, 0, 32)
        mass_a, mass_b = a['r'] ** 2, b['r'] ** 2
        momentum = mass_a * a['vx'] + mass_b * b['vx']
        energy = mass_a * a['vx'] ** 2 + mass_b * b['vx'] ** 2
        self.module.collide(a, b)
        self.assertAlmostEqual(mass_a * a['vx'] + mass_b * b['vx'], momentum)
        self.assertAlmostEqual(mass_a * a['vx'] ** 2 + mass_b * b['vx'] ** 2, energy)
        self.assertLess(a['vx'], b['vx'])
        self.assertGreaterEqual(math.hypot(a['x'] - b['x'], a['y'] - b['y']), 56 - 1e-8)

    def test_separating_balls_do_not_collide_twice(self):
        a, b = ball(-20, 0, -50, 0), ball(20, 0, 50, 0)
        self.module.collide(a, b)
        self.assertEqual((a['vx'], b['vx']), (-50, 50))
        # A coincident pair must separate without dividing by zero.
        a, b = ball(0, 0, 10, 0), ball(0, 0, -10, 0)
        self.module.collide(a, b)
        self.assertGreater(math.hypot(a['x'] - b['x'], a['y'] - b['y']), 47.9)

    def test_walls_include_ball_radius_and_point_velocity_inward(self):
        left, right, bottom, top = self.module.BOUNDS
        self.app.balls = [ball(right + 10, bottom - 10, 250, -250, 30)]
        self.app.update(.05)
        item = self.app.balls[0]
        self.assertLessEqual(item['x'] + item['r'], right)
        self.assertGreaterEqual(item['y'] - item['r'], bottom)
        self.assertLess(item['vx'], 0)
        self.assertGreater(item['vy'], 0)

    def test_fixed_steps_agree_across_frame_rates_and_pause_freezes(self):
        with patch.object(self.module, 'Stage', HeadlessStage):
            other = self.module.PrismBalls()
        for _ in range(60):
            self.app.update(1 / 60)
        for _ in range(20):
            other.update(.05)
        for a, b in zip(self.app.balls, other.balls):
            for field in ('x', 'y', 'vx', 'vy'):
                self.assertAlmostEqual(a[field], b[field], places=7)
        self.app.frame(.025)
        before = state(self.app)
        self.app.frame(0)
        self.assertEqual(state(self.app), before)

    def test_gravity_and_clicks_are_visible_bounded_and_respect_pause(self):
        self.app.balls = [ball(0, 0, 0, 0)]
        self.app.toggle_gravity()
        self.app.update(.1)
        self.assertLess(self.app.balls[0]['vy'], 0)
        self.app.stage.screen.width, self.app.stage.screen.height = 760, 580
        scale = self.app.stage.scale
        for _ in range(40):
            self.app.push(-70 * scale, -90 * scale)
        self.assertEqual(len(self.app.ripples), self.module.RIPPLE_SLOTS)
        self.assertLessEqual(math.hypot(self.app.balls[0]['vx'], self.app.balls[0]['vy']),
                             self.module.MAX_SPEED + 1e-8)
        self.app.stage.paused = True
        before = state(self.app)
        self.app.push(0, 0)
        self.assertEqual(state(self.app), before)
        self.app.stage.paused = False
        self.app.push(0, 400 * scale)
        self.assertEqual(state(self.app), before)
        for _ in range(20):
            self.app.update(.1)
        self.assertTrue(all(ripple is None for ripple in self.app.ripples))

    def test_edge_click_rings_remain_within_the_exhibition_bounds(self):
        scale = self.app.stage.scale
        self.app.push(440 * scale, 195 * scale)
        self.app.frame(.2)
        rings = []
        for item in self.app.stage.canvas.items.values():
            if item['kind'] != 'oval':
                continue
            x1, y1, x2, y2 = item['coords']
            if abs((x1 + x2) / 2 / scale - 440) < .01 and abs(-(y1 + y2) / 2 / scale - 195) < .01:
                rings.append(item)
                left, right, bottom, top = self.module.BOUNDS
                self.assertGreaterEqual(min(x1, x2) / scale, left)
                self.assertLessEqual(max(x1, x2) / scale, right)
                self.assertGreaterEqual(min(-y1, -y2) / scale, bottom)
                self.assertLessEqual(max(-y1, -y2) / scale, top)
        self.assertEqual(len(rings), 2)


if __name__ == '__main__':
    unittest.main()

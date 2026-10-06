"""Real-time clock correctness and retained drawing, without a Tk window."""
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalClockTests(unittest.TestCase):
    def app(self, moment=None):
        module = load_original('时钟.py')
        instant = moment or datetime(2026, 10, 7, 10, 8, 35, 250000)
        with patch.object(module, 'Stage', HeadlessStage), patch.object(module, 'datetime') as clock:
            clock.now.return_value = instant
            app = module.GalleryClock()
        return module, app

    def test_angles_include_fractional_hours_and_minutes(self):
        module, _ = self.app()
        instant = datetime(2026, 10, 7, 3, 15, 30, 500000)
        hour, minute, second = module.clock_angles(instant, True)
        self.assertAlmostEqual(second, 183)
        self.assertAlmostEqual(minute, 93.05)
        self.assertAlmostEqual(hour, 97.7541666667)
        self.assertEqual(module.clock_angles(instant, False)[2], 180)
        midnight = module.clock_angles(datetime(2026, 10, 8), True)
        self.assertEqual(midnight, (0, 0, 0))

    def test_zero_delta_freezes_time_and_resuming_reads_wall_clock(self):
        module, app = self.app()
        app.frame(0)
        before = state(app)
        later = app.moment + timedelta(hours=2)
        with patch.object(module, 'datetime') as clock:
            clock.now.return_value = later
            app.frame(0)
            self.assertEqual(state(app), before)
            app.frame(.025)
        self.assertEqual(app.moment, later)

    def test_demo_uses_elapsed_time_and_returning_live_resynchronizes(self):
        module, app = self.app(datetime(2026, 10, 7, 23, 59, 50))
        app.toggle_demo()
        start = app.moment
        app.frame(.5)
        self.assertEqual(app.moment, start + timedelta(seconds=30))
        app.frame(0)
        self.assertEqual(app.moment.day, 8)
        app.change_speed(10000)
        self.assertLessEqual(app.speed, 600)
        app.change_speed(-10000)
        self.assertGreaterEqual(app.speed, 1)
        actual = datetime(2026, 10, 8, 7, 30, 15)
        with patch.object(module, 'datetime') as clock:
            clock.now.return_value = actual
            app.toggle_demo()
        self.assertFalse(app.demo)
        self.assertEqual(app.moment, actual)

    def test_click_uses_scaled_dial_and_ignores_pause_and_outside(self):
        _, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        before = app.digital
        app.click_dial(300 * app.stage.scale, 0)
        self.assertEqual(app.digital, before)
        app.click_dial(80 * app.stage.scale, -50 * app.stage.scale)
        self.assertNotEqual(app.digital, before)
        app.stage.paused = True
        frozen = state(app)
        app.click_dial(0, 0)
        self.assertEqual(state(app), frozen)

    def test_fixed_dial_reuses_items_and_moving_hands_update_few_shapes(self):
        _, app = self.app()
        app.toggle_demo()
        app.frame(.025)
        canvas = app.stage.canvas
        ids = set(canvas.items)
        before = canvas.coordinate_updates
        app.frame(.025)
        self.assertEqual(set(canvas.items), ids)
        self.assertLessEqual(canvas.coordinate_updates - before, 24)
        for _ in range(12):
            app.cycle_palette()
            app.toggle_tick()
            app.frame(.025)
        self.assertEqual(set(canvas.items), ids)
        self.assertLess(len(ids), 650)
        self.assertTrue({'c', 't', 'd', 'Up', 'Down'} <= set(app.stage.screen.keys))


if __name__ == '__main__':
    unittest.main()

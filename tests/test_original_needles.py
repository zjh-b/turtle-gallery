"""Real needle-game arrival physics, wrapped angles and bounded interactions."""
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class NeedleGameTests(unittest.TestCase):
    def app(self):
        module = load_original('见缝插针.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return module.NeedleGame()

    def test_angles_wrap_at_full_turn(self):
        module = load_original('见缝插针.py')
        self.assertEqual(module.angular_distance(359, 1), 2)
        self.assertEqual(module.angular_distance(1, 359), 2)
        self.assertEqual(module.angular_distance(-180, 180), 0)

    def test_flight_arrives_once_and_scores_only_on_success(self):
        app = self.app()
        app.needles = []
        app.fire()
        app.fire()
        self.assertEqual(app.needles, [])
        app.frame(app.FLIGHT_SECONDS / 2)
        self.assertEqual(app.score, 0)
        app.frame(app.FLIGHT_SECONDS / 2)
        self.assertEqual((app.score, app.best, len(app.needles)), (1, 1, 1))
        self.assertIsNone(app.flight)
        self.assertAlmostEqual((app.needles[0] + app.angle) % 360, 180)

    def test_collision_checks_rotated_wheel_at_arrival(self):
        app = self.app()
        # This pin is clear of the firing line at launch, but arrives with the shot.
        app.needles = [(180 - app.speed * app.FLIGHT_SECONDS) % 360]
        before = list(app.needles)
        app.fire()
        app.frame(app.FLIGHT_SECONDS)
        self.assertEqual(app.phase, 'lost')
        self.assertEqual(app.needles, before)
        self.assertEqual(app.score, 0)
        self.assertIsNotNone(app.failed_angle)
        angle = app.angle
        app.frame(2)
        self.assertEqual(app.angle, angle)

    def test_event_time_does_not_depend_on_frame_size(self):
        coarse, fine = self.app(), self.app()
        for app in (coarse, fine):
            app.needles = []
            app.fire()
        coarse.frame(.7)
        for _ in range(70):
            fine.frame(.01)
        self.assertEqual(coarse.score, fine.score)
        self.assertAlmostEqual(coarse.angle, fine.angle)
        self.assertAlmostEqual(coarse.needles[0], fine.needles[0])

    def test_pause_and_chrome_do_not_fire(self):
        app = self.app()
        app.frame(.05)
        before = state(app)
        app.click(0, 320 * app.stage.scale)
        app.frame(0)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        before = state(app)
        app.click(0, 0)
        app.fire()
        self.assertEqual(state(app), before)

    def test_completion_is_bounded_and_restart_keeps_session_best(self):
        app = self.app()
        app.score = app.TARGET - 1
        app.needles = []
        app.fire()
        app.frame(app.FLIGHT_SECONDS)
        self.assertEqual(app.phase, 'won')
        self.assertEqual(app.best, app.TARGET)
        for _ in range(100):
            app.fire()
        self.assertEqual(len(app.needles), 1)
        app.reset()
        self.assertEqual((app.score, app.best, app.phase), (0, app.TARGET, 'playing'))

    def test_all_palettes_reuse_canvas_after_restarts_and_collisions(self):
        app = self.app()
        counts = []
        for cycle in range(3):
            for _ in range(12):
                app.reset()
                app.change_palette()
                app.fire()
                app.frame(.8)
                app.stage.screen.width, app.stage.screen.height = 760, 580
                app.frame(0)
            counts.append(len(app.stage.canvas.items))
        self.assertLess(max(counts), 1200)
        self.assertLessEqual(counts[-1], counts[-2] + 5)


if __name__ == '__main__':
    unittest.main()

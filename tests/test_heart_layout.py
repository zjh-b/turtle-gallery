"""Heart composition stays interactive and stable across artwork formats."""
import copy
import math
import unittest

from test_demos import make_app, state


class HeartLayoutTests(unittest.TestCase):
    def test_largest_bursts_fit_every_new_frame_throughout_dispersion(self):
        app = make_app("ParticleHeart")
        for aspect in (1, 2, 3):
            for seed in (0, 2147483647):
                app.apply_parameters(dict(app.get_parameters(), aspect=aspect, seed=seed,
                                          size=1.1, particle_count=1000))
                app.time = app.beat_time = .279  # Primary heartbeat peak.
                for age in (0, .45, .9, 1.35, 1.8):
                    with self.subTest(aspect=aspect, seed=seed, burst_age=age):
                        app.burst_age = age
                        app.frame(0)
                        left, top, right, bottom = app.stage.artwork.bounds
                        for kind, _, coords, options in app.paint.items[:app.paint.index]:
                            if kind != "oval" or coords[2]-coords[0] >= 30:
                                continue
                            x1, y1, x2, y2 = coords
                            self.assertGreaterEqual(x1, left-.02)
                            self.assertLessEqual(x2, right+.02)
                            self.assertGreaterEqual(y1, -top-.02)
                            self.assertLessEqual(y2, -bottom+.02)

    def test_switching_formats_preserves_particles_and_animation_phase(self):
        app = make_app("ParticleHeart")
        app.burst(0, 0)
        app.frame(.7)
        original = state(app)
        original_drawing = copy.deepcopy([
            app.stage.canvas.items[item] for item in app.stage.canvas.matching("particle-heart")])
        particles, motion, stars = app.particles, app._motion, app.stars
        parameters = app.get_parameters()
        self.assertIn("aspect", parameters)
        for aspect in (2, 1, 3, 0):
            with self.subTest(aspect=aspect):
                app.apply_parameters(dict(parameters, aspect=aspect))
                self.assertEqual(app.get_parameters()["aspect"], aspect)
                self.assertEqual(app.stage.artwork.aspect, aspect)
                app.frame(0)
                self.assertEqual(state(app), original)
                self.assertIs(app.particles, particles)
                self.assertIs(app._motion, motion)
                self.assertIs(app.stars, stars)
        restored_drawing = [app.stage.canvas.items[item]
                            for item in app.stage.canvas.matching("particle-heart")
                            if app.stage.canvas.items[item]["options"]["state"] != "hidden"]
        self.assertEqual(restored_drawing, original_drawing)

    def test_clicks_follow_artwork_after_resize_and_ignore_matte(self):
        app = make_app("ParticleHeart")
        for aspect in (1, 2, 3):
            app.stage.artwork.aspect = aspect
            for width, height in ((1000, 720), (760, 580), (1600, 900)):
                with self.subTest(aspect=aspect, window=(width, height)):
                    app.stage.screen.width, app.stage.screen.height = width, height
                    left, top, right, bottom = app.stage.artwork.bounds
                    cx, cy = (left + right) / 2, (top + bottom) / 2
                    app.burst_age = None
                    app.burst(cx, cy)
                    self.assertEqual(app.burst_age, 0)
                    app.frame(.25)
                    for point in ((left - 2, cy), (right + 2, cy),
                                  (cx, top + 2), (cx, bottom - 2)):
                        age = app.burst_age
                        app.burst(*point)
                        self.assertEqual(app.burst_age, age)
                    app.stage.paused = True
                    age = app.burst_age
                    app.burst(cx, cy)
                    self.assertEqual(app.burst_age, age)
                    app.stage.paused = False

    def test_portrait_and_square_keep_subject_and_captions_inside_artwork(self):
        app = make_app("ParticleHeart")
        for aspect in (2, 3):
            with self.subTest(aspect=aspect):
                app.stage.artwork.aspect = aspect
                app.burst_age = 1.8
                app.frame(0)
                left, top, right, bottom = app.stage.artwork.bounds
                items = [app.stage.canvas.items[item]
                         for item in app.stage.canvas.matching("particle-heart")]
                texts = [item for item in items if item["kind"] == "text"
                         and item["options"]["state"] != "hidden"]
                self.assertGreaterEqual(len(texts), 4)
                for item in texts:
                    x, y = item["coords"]
                    self.assertTrue(left < x < right)
                    self.assertTrue(-top < y < -bottom)
                # Stars, constellations and burst particles all remain circles.
                circles = [item for item in items if item["kind"] == "oval"
                           and item["coords"][2] - item["coords"][0] < 30]
                self.assertGreater(len(circles), app.particle_count)
                for item in circles:
                    x1, y1, x2, y2 = item["coords"]
                    self.assertAlmostEqual(x2 - x1, y2 - y1, delta=.02)
                    self.assertGreaterEqual(x1, left - .02)
                    self.assertLessEqual(x2, right + .02)
                    self.assertGreaterEqual(y1, -top - .02)
                    self.assertLessEqual(y2, -bottom + .02)

    def test_format_switches_and_bursts_reuse_a_finite_canvas_pool(self):
        app = make_app("ParticleHeart")
        for _ in range(3):
            for aspect in (0, 1, 2, 3):
                app.stage.artwork.aspect = aspect
                app.burst_age = 0
                for dt in (0, .15, 1.65, 1.8):
                    app.frame(dt)
                    self.assertLess(len(app.stage.canvas.items), 1100)
                    for item in app.stage.canvas.items.values():
                        self.assertTrue(all(math.isfinite(value) for value in item["coords"]))
        before = len(app.stage.canvas.items)
        app.frame(.025)
        self.assertEqual(len(app.stage.canvas.items), before)


if __name__ == "__main__":
    unittest.main()

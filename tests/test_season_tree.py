"""Interaction and bounded rendering checks for the four-season painting."""
import unittest

from test_demos import make_app, state


class SeasonTreeTests(unittest.TestCase):
    def test_gust_ignores_pause_and_controls_and_freezes_at_zero_delta(self):
        app = make_app("SeasonTree")
        before = state(app)
        app.blow(0, app.stage.height / 2)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        app.blow(100, 100)
        self.assertEqual(state(app), before)
        app.stage.paused = False
        app.blow(-100, 100)
        self.assertEqual(app.gust_side, -1)
        self.assertEqual(app.gust, app.GUST_SECONDS)
        app.frame(.05)
        frozen = state(app)
        app.frame(0)
        self.assertEqual(state(app), frozen)
        app.frame(app.GUST_SECONDS)
        self.assertEqual(app.gust, 0)

    def test_repeated_gusts_reuse_a_fixed_pool_and_canvas_items(self):
        app = make_app("SeasonTree")
        app.frame(.025)
        initial_items = set(app.stage.canvas.items)
        for i in range(24):
            app.blow(100 if i % 2 else -100, 30)
            app.frame(.05)
            self.assertLessEqual(app.gust, app.GUST_SECONDS)
        self.assertEqual(set(app.stage.canvas.items), initial_items)
        self.assertEqual(len(app.falling), 56)
        self.assertLess(len(initial_items), 1500)

    def test_all_seasons_are_repeatable_and_remain_bounded_after_regrowth(self):
        app = make_app("SeasonTree")
        for season in range(4):
            with self.subTest(season=season):
                app.set_season(season)
                app.change_wind(20)
                app.regrow()
                app.frame(8)
                self.assertEqual(app.season, season)
                self.assertEqual(app.growth, 8)
                self.assertEqual(app.wind, 3)
                self.assertLess(len(app.stage.canvas.items), 1500)
                frozen = state(app)
                snapshot = {key: (item["coords"], dict(item["options"]))
                            for key, item in app.stage.canvas.items.items()}
                app.frame(0)
                self.assertEqual(state(app), frozen)
                self.assertEqual(snapshot, {key: (item["coords"], dict(item["options"]))
                                            for key, item in app.stage.canvas.items.items()})
        app.reset()
        self.assertEqual((app.time, app.season, app.wind, app.growth, app.gust),
                         (0, 0, 1, 8, 0))


if __name__ == "__main__":
    unittest.main()

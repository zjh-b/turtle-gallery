"""The original random recursion stays connected, repeatable and bounded."""
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalRandomTreeTests(unittest.TestCase):
    def app(self):
        module = load_original('分形树.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return module, module.BlossomTree()

    def test_recursive_branches_connect_and_stay_within_artwork(self):
        module, app = self.app()
        for seed in (202610, 1, 9, 100, 718):
            branches, flowers = module.generate_tree(seed)
            self.assertGreater(len(branches), 70)
            self.assertLessEqual(len(branches), 255)
            self.assertLessEqual(len(flowers), 220)
            for index, branch in enumerate(branches):
                self.assertLessEqual(branch.depth, 7)
                self.assertGreater(branch.start_width, branch.end_width)
                if index:
                    parent = branches[branch.parent]
                    self.assertEqual(branch.points[0], parent.points[-1])
                    self.assertTrue(10 <= abs(branch.turn) <= 40)
                    self.assertTrue(10 <= parent.length - branch.length <= 20)
                for x, y in branch.points:
                    self.assertTrue(-390 <= x <= 390)
                    self.assertTrue(-200 <= y <= 230)
            for x, y, radius, angle, branch_index, shade in flowers:
                self.assertTrue(-410 < x - radius < x + radius < 410)
                self.assertTrue(-220 < y - radius < y + radius < 250)

    def test_seed_reproduces_geometry_and_palette_preserves_it(self):
        module, app = self.app()
        first = app.branches, app.flowers
        app.cycle_palette()
        self.assertEqual((app.branches, app.flowers), first)
        app.next_tree()
        second_seed, second = app.seed, (app.branches, app.flowers)
        self.assertNotEqual(second, first)
        self.assertEqual(module.generate_tree(second_seed), second)
        app.reset()
        self.assertEqual((app.branches, app.flowers), first)
        app.next_tree()
        self.assertEqual((app.seed, app.branches, app.flowers), (second_seed, *second))

    def test_growth_and_actions_obey_pause_and_large_time_steps(self):
        _, app = self.app()
        app.replay_growth()
        self.assertEqual(app.growth, 0)
        app.frame(.5)
        self.assertGreater(app.growth, 0)
        self.assertLess(app.growth, app.GROWTH_END)
        app.stage.paused = True
        before = state(app)
        app.next_tree()
        app.replay_growth()
        app.blow(100, 100)
        app.frame(0)
        self.assertEqual(state(app), before)
        app.stage.paused = False
        app.frame(30)
        self.assertEqual(app.growth, app.GROWTH_END)

    def test_gust_waits_until_the_first_blossom_is_actually_visible(self):
        _, app = self.app()
        first_opening = min(app.branches[flower[4]].depth for flower in app.flowers) + 1
        for growth in (first_opening, first_opening + .04):
            app.growth = growth
            app.frame(0)
            app.blow(0, 0)
            self.assertEqual(app.petals, [])
        app.growth = first_opening + 1 / 12
        app.frame(0)
        app.blow(0, 0)
        self.assertGreater(len(app.petals), 0)

    def test_clicks_are_scaled_bounded_and_expire_without_rebuilding_tree(self):
        _, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.frame(.01)
        before = state(app)
        app.blow(0, 330 * app.stage.scale)
        self.assertEqual(state(app), before)
        for _ in range(80):
            app.blow(120 * app.stage.scale, 100 * app.stage.scale)
        self.assertGreater(len(app.petals), 0)
        self.assertLessEqual(len(app.petals), 48)
        geometry = app.branches, app.flowers
        app.frame(10)
        self.assertFalse(app.petals)
        self.assertEqual((app.branches, app.flowers), geometry)
        app.frame(.1)
        items = set(app.stage.canvas.items)
        for _ in range(50):
            app.frame(.025)
        self.assertEqual(set(app.stage.canvas.items), items)
        for _ in range(10):
            app.next_tree()
            app.cycle_palette()
            app.blow(0, 0)
            app.frame(.1)
            self.assertLess(len(app.stage.canvas.items), 1200)


if __name__ == '__main__':
    unittest.main()

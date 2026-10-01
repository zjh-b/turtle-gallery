"""Regression checks for the orbital exhibit's fixed geometry and depth."""
import copy
import math
import unittest

from test_demos import DEMOS, make_app, state


class GalaxyTests(unittest.TestCase):
    def test_seeded_scene_is_reproducible_and_zero_delta_is_cached(self):
        first, second = make_app("Galaxy"), make_app("Galaxy")
        for app in (first, second):
            app.frame(3.75)
        self.assertEqual(first.stage.canvas.items, second.stage.canvas.items)
        before = state(first)
        drawing = copy.deepcopy(first.stage.canvas.items)
        updates = (first.stage.canvas.coordinate_updates, first.stage.canvas.option_updates)
        first.frame(0)
        self.assertEqual(state(first), before)
        self.assertEqual(first.stage.canvas.items, drawing)
        self.assertEqual((first.stage.canvas.coordinate_updates,
                          first.stage.canvas.option_updates), updates)

    def test_selection_orbits_depth_and_resize_reuse_the_same_canvas_pool(self):
        app = make_app("Galaxy")
        app.frame(0)
        ids = set(app.stage.canvas.items)
        allocated = app.stage.canvas.next_id
        self.assertLess(len(ids), 1250)
        for frame in range(90):
            app.selected = frame % 6 if frame % 6 < 5 else None
            app.show_orbits = frame % 3 != 0
            app.stage.screen.width, app.stage.screen.height = ((760, 580) if frame % 2 else (1000, 720))
            app.frame(0.8)
        self.assertEqual(set(app.stage.canvas.items), ids)
        self.assertEqual(app.stage.canvas.next_id, allocated)
        app.reset()
        self.assertEqual((app.time, app.speed, app.selected, app.show_orbits), (0, 1, None, True))

    def test_planet_and_selection_bounds_fit_the_smallest_scene(self):
        app = make_app("Galaxy")
        app.stage.screen.width, app.stage.screen.height = 760, 580
        for index, (orbit, radius, color, speed, phase, name) in enumerate(DEMOS["Galaxy"].PLANETS):
            # Includes the outer selection ring and its small pointer.
            reach = radius * (2.06 if index == 3 else 1) + 12
            for sample in range(180):
                x, y = app.orbit(orbit, sample * math.tau / 180)
                with self.subTest(planet=name, sample=sample):
                    self.assertLess(abs(x) + reach, app.stage.view[0] / 2 - 20)
                    self.assertLess(y + reach + 3, 265)
                    self.assertGreater(y - reach, -285)

    def test_planet_returning_behind_sun_restores_occlusion(self):
        app = make_app("Galaxy")
        canvas, order = app.stage.canvas, []
        create = canvas._create

        def create_and_track(*args, **kwargs):
            item = create(*args, **kwargs)
            order.append(item)
            return item

        def raise_and_track(item_or_tag):
            matching = set(canvas.matching(item_or_tag))
            order[:] = [item for item in order if item not in matching] + [
                item for item in order if item in matching]

        canvas._create, canvas.tag_raise = create_and_track, raise_and_track
        # Mercury begins behind, crosses in front, and then returns behind.
        for time in (0, 6, 9):
            app.time = time
            app.frame(0)
            sun = next(key for key, item in canvas.items.items()
                       if item["options"].get("fill") == "#ed7b38")
            radius = DEMOS["Galaxy"].PLANETS[0][1] + 2
            mercury = next(key for key, item in canvas.items.items()
                           if item["kind"] == "oval"
                           and item["options"].get("fill") == "#090F20"
                           and abs(item["coords"][2] - item["coords"][0]
                                   - 2 * radius * app.stage.scale) < 0.02)
            _, y = app.orbit(88, time * 0.65 + 0.8)
            self.assertEqual(order.index(mercury) > order.index(sun), y <= -5)


if __name__ == "__main__":
    unittest.main()

"""Responsive lily composition preserves its geometry and viewport interaction."""
import copy
import math
import unittest

from test_demos import make_app


def rendered_art(app):
    return [(entry[0], entry[2], copy.deepcopy(entry[3]))
            for entry in app.paint.items[:app.paint.index]]


class LilyLayoutTests(unittest.TestCase):
    def set_aspect(self, app, aspect):
        app.apply_parameters(dict(app.get_parameters(), aspect=aspect))

    def test_switching_ratios_preserves_geometry_time_and_native_rendering(self):
        app = make_app("StarryLily")
        app.frame(8)
        app.meteor(30, 40)
        app.frame(0)
        native = rendered_art(app)
        geometry = {key: getattr(app, key) for key in
                    ("stars", "dust", "florets", "branches", "stem")}
        timing = (app.time, app.bloom, copy.deepcopy(app.meteors))
        for aspect in (1, 2, 3, 0):
            with self.subTest(aspect=aspect):
                self.set_aspect(app, aspect)
                app.frame(0)
                self.assertEqual(app.stage.artwork.aspect, aspect)
                self.assertEqual((app.time, app.bloom, app.meteors), timing)
                for key, original in geometry.items():
                    self.assertIs(getattr(app, key), original)
        self.assertEqual(rendered_art(app), native)

    def test_meteors_use_viewport_coordinates_and_reject_matte(self):
        app = make_app("StarryLily")
        for aspect in (1, 2, 3):
            with self.subTest(aspect=aspect):
                self.set_aspect(app, aspect)
                app.meteors.clear()
                art = app.stage.artwork
                x, y = art.view[0]*.3, art.view[1]*.4
                ox, oy = art.offset
                for _ in range(12):
                    app.meteor(ox+x*art.scale, oy+y*art.scale)
                self.assertEqual(len(app.meteors), 5)
                self.assertAlmostEqual(app.meteors[-1][0], x)
                self.assertAlmostEqual(app.meteors[-1][1], y)
                before = copy.deepcopy(app.meteors)
                app.meteor(art.bounds[0]-1, oy)
                app.meteor(ox, art.bounds[1]+1)
                self.assertEqual(app.meteors, before)
                app.frame(0)
                heads = [entry for entry in app.paint.items[:app.paint.index]
                         if entry[0] == "oval" and entry[3].get("fill") == "#fff2dc"]
                self.assertEqual(len(heads), 5)
                app.frame(2)
                self.assertFalse(app.meteors)

    def test_new_compositions_fit_viewport_and_keep_canvas_pool_bounded(self):
        app = make_app("StarryLily")
        app.frame(8)
        for window in ((760, 580), (1100, 800)):
            app.stage.screen.width, app.stage.screen.height = window
            for aspect in (1, 2, 3):
                with self.subTest(window=window, aspect=aspect):
                    self.set_aspect(app, aspect)
                    app.frame(0)
                    left, top, right, bottom = app.stage.artwork.bounds
                    for kind, coords, options in rendered_art(app):
                        self.assertTrue(all(math.isfinite(value) for value in coords))
                        # The gradient overlaps the boundary slightly to avoid seams.
                        if kind == "rectangle":
                            continue
                        for x, canvas_y in zip(coords[::2], coords[1::2]):
                            self.assertGreaterEqual(x, left-.02)
                            self.assertLessEqual(x, right+.02)
                            self.assertGreaterEqual(-canvas_y, bottom-.02)
                            self.assertLessEqual(-canvas_y, top+.02)
                    count = len(app.stage.canvas.items)
                    self.assertLess(count, 1600)
                    for _ in range(5):
                        app.frame(.05)
                    self.assertLessEqual(len(app.stage.canvas.items), count+10)

if __name__ == "__main__":
    unittest.main()

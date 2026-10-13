"""The rose must grow from its stem, with unchanged fully open geometry."""
import math
import unittest
from unittest.mock import patch

from test_demos import make_app


def inside(point, polygon):
    x, y = point
    result = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            result = not result
    return result


class RoseGrowthTests(unittest.TestCase):
    def test_growing_petals_cover_the_visible_stem_tip(self):
        for size in ((1000, 720), (760, 580)):
            for theme in range(3):
                app = make_app("GalaxyRose")
                app.stage.screen.setup(*size)
                app.theme = theme
                for growth in (1.7, 1.9, 2., 2.5, 3., 3.4, 4.3, 5.3, 7.):
                    app.time = app.growth = growth
                    with patch.object(app.paint, "poly", wraps=app.paint.poly) as polygons, \
                            patch.object(app.paint, "line", wraps=app.paint.line) as lines:
                        app.frame(0)
                    stem = next(call.args[0] for call in lines.call_args_list
                                if call.args[1] == "#264A42")
                    # Base petal outlines have >=45 sampled points; leaves and
                    # sepals are smaller. Include shading in the actual union.
                    petals = [call.args[0] for call in polygons.call_args_list
                              if len(call.args[0]) >= 45]
                    with self.subTest(size=size, theme=theme, growth=growth):
                        self.assertTrue(petals)
                        self.assertTrue(any(inside(stem[-1], shape) for shape in petals),
                                        "The flower is disconnected from its visible stem tip")

    def test_emerging_sepals_share_the_stem_tip(self):
        app = make_app("GalaxyRose")
        app.time = app.growth = 1.7
        with patch.object(app.paint, "poly", wraps=app.paint.poly) as polygons, \
                patch.object(app.paint, "line", wraps=app.paint.line) as lines:
            app.frame(0)
        tip = next(call.args[0][-1] for call in lines.call_args_list
                   if call.args[1] == "#264A42")
        sepals = [call.args[0] for call in polygons.call_args_list
                  if call.args[1] == "#315044"]
        self.assertEqual(len(sepals), 3)
        self.assertTrue(all(math.dist(point, tip) < 1 for shape in sepals for point in shape),
                        "New sepals should unfold at the stem tip")

    def test_fully_open_petals_keep_original_coordinates(self):
        app = make_app("GalaxyRose")
        app.growth = 7
        for time in (0, 3.4, 7.6, 29):
            app.time = time
            sway = math.sin(time*.65)*3.3
            for outline, _, _ in app.petals:
                expected = [(35+x+sway, 98+y) for x, y in outline]
                self.assertEqual(app.transform(outline, 1), expected)


if __name__ == "__main__":
    unittest.main()

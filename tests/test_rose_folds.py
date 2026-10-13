"""Fold highlights must stay on their petals as the rose opens and overlaps."""
import math
import unittest

from test_demos import make_app


# The eight hand-drawn creases belong to these back-to-front petal outlines.
FOLD_PETALS = (2, 3, 4, 5, 6, 7, 8, 10)


def points(item):
    coords = item["coords"]
    return list(zip(coords[::2], coords[1::2]))


def inside(point, polygon):
    x, y = point
    result = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            result = not result
    return result


def flower_items(app):
    """Select actual Canvas output, keeping Paint's retained-item ordering."""
    canvas = app.stage.canvas
    visible = [(key, canvas.items[key]) for key in canvas.stacking
               if canvas.items[key]["options"].get("state") != "hidden"]
    # Base petal outlines are the large, outlined polygons; their inset color
    # planes have no outline. Leaves and sepals have fewer sampled points.
    petals = [(key, item) for key, item in visible
              if item["kind"] == "polygon" and len(item["coords"]) >= 90
              and item["options"].get("outline")]
    # Creases are the only 21-point polylines after the stem has fully grown.
    folds = [(key, item) for key, item in visible
             if item["kind"] == "line" and len(item["coords"]) == 42]
    return petals, folds


class RoseFoldTests(unittest.TestCase):
    def test_front_petals_occlude_overlapping_back_petals_folds(self):
        app = make_app("GalaxyRose")
        # Replaying replaces/hides some retained Canvas slots, so check the
        # first mature frame and a mature frame after the flower disappears.
        for cycle in range(2):
            app.time = 7 + cycle * 17
            app.growth = 7
            app.frame(0)
            petals, folds = flower_items(app)
            self.assertEqual((len(petals), len(folds)), (12, 8))
            stacking = {key: index for index, key in enumerate(app.stage.canvas.stacking)}
            overlaps = 0
            for fold_index, ((fold_id, fold), owner) in enumerate(zip(folds, FOLD_PETALS)):
                # Everything filled between adjacent base outlines belongs to
                # this petal. A fold above only the base can still disappear
                # beneath its own shading; do not assume a fixed layer count.
                start = stacking[petals[owner][0]]
                stop = stacking[petals[owner+1][0]]
                fills = [key for key in app.stage.canvas.stacking[start:stop]
                         if app.stage.canvas.items[key]["kind"] == "polygon"
                         and app.stage.canvas.items[key]["options"].get("fill")
                         and app.stage.canvas.items[key]["options"].get("state") != "hidden"]
                self.assertGreater(len(fills), 1, "The petal must include actual shaded planes")
                with self.subTest(cycle=cycle, fold=fold_index):
                    self.assertGreater(stacking[fold_id], max(stacking[key] for key in fills),
                                       "A crease must remain above all of its own fill layers")
                for foreground_id, foreground in petals[owner+1:]:
                    if any(inside(point, points(foreground)) for point in points(fold)[1:-1]):
                        overlaps += 1
                        with self.subTest(cycle=cycle, fold=fold_index,
                                          foreground=petals.index((foreground_id, foreground))):
                            self.assertLess(stacking[fold_id], stacking[foreground_id],
                                            "A rear crease shines through a foreground petal")
            self.assertGreater(overlaps, 0, "The fixture must contain real overlapping geometry")
            app.growth = 0
            app.frame(0)

    def test_growing_fold_moves_with_its_own_petal(self):
        for size in ((1000, 720), (760, 580)):
            app = make_app("GalaxyRose")
            app.stage.screen.setup(*size)
            for growth in (2.5, 3.4, 4.3):
                app.growth = growth
                app.time = growth + 17  # A replay need not share the growth clock.
                app.frame(0)
                petals, folds = flower_items(app)
                self.assertEqual((len(petals), len(folds)), (12, 8))
                for fold_index, ((_, fold), owner) in enumerate(zip(folds, FOLD_PETALS)):
                    original = app.petals[owner][0]
                    drawn = points(petals[owner][1])
                    # Infer each axis' transform from the rendered petal's
                    # widest span, independently of the production growth law.
                    axes = []
                    for axis in (0, 1):
                        lo = min(range(len(original)), key=lambda i: original[i][axis])
                        hi = max(range(len(original)), key=lambda i: original[i][axis])
                        scale = ((drawn[hi][axis]-drawn[lo][axis]) /
                                 (original[hi][axis]-original[lo][axis]))
                        axes.append((scale, drawn[lo][axis]-scale*original[lo][axis]))
                    expected = [tuple(scale*point[axis]+offset
                                      for axis, (scale, offset) in enumerate(axes))
                                for point in app.fold_lines[fold_index]]
                    error = max(math.dist(a, b) for a, b in zip(points(fold), expected))
                    with self.subTest(size=size, growth=growth, fold=fold_index):
                        # Paint rounds Canvas coordinates to 0.01 pixels.
                        self.assertLess(error, .04,
                                        "The crease expands at a different rate from its petal")


if __name__ == "__main__":
    unittest.main()

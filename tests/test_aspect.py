"""Artwork framing shares one transform between preview, input and export."""
import os
import tkinter as tk
import unittest

from test_demos import HeadlessStage, STAGE, make_app


class ArtworkTests(unittest.TestCase):
    def setUp(self):
        self.stage = HeadlessStage("Artwork", "Controls")

    def test_original_view_and_input_remain_unchanged(self):
        art = self.stage.artwork
        self.assertEqual(art.view, self.stage.view)
        self.assertEqual(art.scale, self.stage.scale)
        self.assertEqual(art.offset, (0, 0))
        self.assertEqual(art.point(30, 40), self.stage.point(30, 40))
        self.assertEqual(art.in_scene(0, -290), self.stage.in_scene(0, -290))

    def test_requested_ratios_fit_between_hud_and_footer_at_every_window_size(self):
        art = self.stage.artwork
        for width, height in ((760, 580), (1000, 720), (1920, 1080), (800, 1200)):
            self.stage.screen.width, self.stage.screen.height = width, height
            for aspect, ratio in ((1, (16, 9)), (2, (9, 16)), (3, (1, 1))):
                with self.subTest(window=(width, height), aspect=aspect):
                    art.aspect = aspect
                    left, top, right, bottom = art.bounds
                    self.assertEqual((right-left)*ratio[1], (top-bottom)*ratio[0])
                    self.assertTrue(all(int(v) == v for v in art.bounds))
                    self.assertLessEqual(top, height/2 - 100*self.stage.scale)
                    self.assertGreaterEqual(bottom, -height/2 + 78*self.stage.scale)
                    self.assertGreater(left, -width/2)
                    self.assertLess(right, width/2)
                    self.assertFalse(art.in_scene(*art.point(left-1, 0)))
                    self.assertTrue(art.in_scene(*art.point(*art.offset)))

    def test_group_transform_is_uniform_and_resets_at_each_frame(self):
        art = self.stage.artwork
        art.aspect = 2
        paint = STAGE.Paint(art, "art")
        paint.begin()
        paint.transform(scale=.75, x=20, y=-30)
        paint.circle(10, 20, 4, "#ffffff")
        coords = self.stage.canvas.items[paint.items[0][1]]["coords"]
        expected_x = art.offset[0] + (20+10*.75)*art.scale
        expected_y = art.offset[1] + (-30+20*.75)*art.scale
        self.assertAlmostEqual((coords[0]+coords[2])/2, expected_x, places=2)
        self.assertAlmostEqual(-(coords[1]+coords[3])/2, expected_y, places=2)
        self.assertAlmostEqual(coords[2]-coords[0], coords[3]-coords[1], places=2)
        paint.end()
        paint.begin()
        paint.circle(0, 0, 4, "#ffffff")
        coords = self.stage.canvas.items[paint.items[0][1]]["coords"]
        self.assertAlmostEqual((coords[0]+coords[2])/2, art.offset[0], places=2)
        self.assertAlmostEqual(-(coords[1]+coords[3])/2, art.offset[1], places=2)

    def test_matte_and_guides_clear_when_restoring_original_view(self):
        art = self.stage.artwork
        art.aspect, art.show_safe_area = 2, True
        self.stage.hud()
        matte = list(self.stage.canvas.matching("artwork-matte"))
        guides = list(self.stage.canvas.matching("artwork-guide"))
        self.assertGreaterEqual(len(matte), 4)
        self.assertTrue(guides)
        art.aspect = 0
        self.stage.hud()
        for item in matte + guides:
            self.assertEqual(self.stage.canvas.items[item]["options"]["state"], "hidden")


@unittest.skipUnless(os.environ.get("TURTLE_GALLERY_GUI_TESTS") == "1",
                     "Opt in to desktop font checks with TURTLE_GALLERY_GUI_TESTS=1")
class ArtworkFontTests(unittest.TestCase):
    def test_real_text_bounds_fit_safe_area_without_collisions(self):
        # Normal CI stays headless. This opt-in check uses the desktop's actual
        # font metrics in an unshown Tk root; no Turtle window is created.
        root = tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        canvas = tk.Canvas(root)
        for name in ("StarryLily", "ParticleHeart"):
            app = make_app(name)
            app.frame(8)
            for window in ((760, 580), (1100, 900)):
                app.stage.screen.width, app.stage.screen.height = window
                for aspect in (1, 2, 3):
                    app.apply_parameters(dict(app.get_parameters(), aspect=aspect))
                    app.frame(0)
                    left, top, right, bottom = app.stage.artwork.bounds
                    dx, dy = (right-left)*.06, (top-bottom)*.06
                    boxes = []
                    for kind, _, coords, options in app.paint.items[:app.paint.index]:
                        if kind != "text":
                            continue
                        with self.subTest(scene=name, window=window, aspect=aspect, text=options["text"]):
                            item = canvas.create_text(*coords, **options)
                            x1, y1, x2, y2 = canvas.bbox(item)
                            self.assertGreaterEqual(x1, left+dx)
                            self.assertLessEqual(x2, right-dx)
                            self.assertGreaterEqual(y1, -top+dy)
                            self.assertLessEqual(y2, -bottom-dy)
                            for a1, b1, a2, b2 in boxes:
                                self.assertTrue(x2 <= a1 or x1 >= a2 or y2 <= b1 or y1 >= b2,
                                                "Artwork text must not overlap")
                            boxes.append((x1, y1, x2, y2))
                            canvas.delete(item)


if __name__ == "__main__":
    unittest.main()

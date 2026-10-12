"""Keep click feedback above the wings, including after Canvas pool reuse."""
import copy
import unittest

from test_demos import make_app, state


def markers(app, x, y):
    scale = app.stage.scale
    result = []
    for item_id, item in app.stage.canvas.items.items():
        if item["kind"] != "oval" or item["options"].get("state") == "hidden":
            continue
        left, top, right, bottom = item["coords"]
        if abs((left+right)/2-x*scale) < .02 and abs((top+bottom)/2+y*scale) < .02:
            radius = (right-left)/2/scale
            if item["options"].get("fill") == "" or abs(radius-2) < .02:
                result.append((item_id, radius, item["options"]))
    return result


def artwork(app):
    return {key: item for key, item in app.stage.canvas.items.items()
            if "neon-butterfly" in item["options"].get("tags", ())}


class ButterflyFeedbackTests(unittest.TestCase):
    def test_core_and_small_open_ring_stay_above_art_after_pool_reuse(self):
        for size in ((1000, 720), (760, 580)):
            for theme in range(3):
                app = make_app("NeonButterfly")
                app.stage.screen.setup(*size)
                app.theme = theme
                for x, y in ((170, 110), (-280, 110), (170, 110)):
                    app.attract(x*app.stage.scale, y*app.stage.scale)
                    for dt in (.2, .8):
                        app.frame(dt)
                        with self.subTest(size=size, theme=theme, target=(x, y), dt=dt):
                            found = markers(app, x, y)
                            self.assertEqual(len(found), 2)
                            self.assertTrue(any(options["fill"].upper() == "#FFEEFC"
                                                for _, _, options in found))
                            ids = {item_id for item_id, _, _ in found}
                            for item_id, radius, options in found:
                                self.assertLessEqual(radius, 18.02)
                                if radius > 2.02:
                                    self.assertEqual(options["fill"], "")
                                below = app.stage.canvas.stacking.index(item_id)
                                for art_id, item in app.stage.canvas.items.items():
                                    if (item["kind"] == "text"
                                            and "neon-butterfly" in item["options"].get("tags", ())):
                                        self.assertLess(below, app.stage.canvas.stacking.index(art_id))
                                    if (art_id not in ids and item["kind"] != "text"
                                            and item["options"].get("state") != "hidden"
                                            and "neon-butterfly" in item["options"].get("tags", ())):
                                        self.assertLess(app.stage.canvas.stacking.index(art_id), below)
                    app.frame(6)
                    self.assertEqual(markers(app, x, y), [])

    def test_marker_freezes_fades_expires_and_uses_a_bounded_pool(self):
        app = make_app("NeonButterfly")
        app.stage.reset_action = app.reset
        app.frame(0)
        counts = []
        for _ in range(6):
            app.attract(170*app.stage.scale, 110*app.stage.scale)
            app.frame(.2)
            before = state(app), copy.deepcopy(artwork(app))
            app.stage.paused = True
            app.attract(0, 0)
            app.change_theme()
            app.toggle_motion()
            app.frame(0)
            self.assertEqual((state(app), artwork(app)), before)
            app.stage.paused = False
            app.frame(5.6)
            core = next(options["fill"] for _, radius, options in markers(app, 170, 110)
                        if abs(radius-2) < .02)
            self.assertNotEqual(core.upper(), "#FFEEFC", "The foreground cue fades before expiry")
            app.frame(.3)
            self.assertIsNone(app.target)
            self.assertEqual(markers(app, 170, 110), [])
            app.attract(170*app.stage.scale, 110*app.stage.scale)
            app.frame(0)
            app.stage.reset()
            app.frame(0)
            self.assertEqual(markers(app, 170, 110), [])
            counts.append((len(app.stage.canvas.items), len(app.paint.items)))
        self.assertEqual(len(set(counts)), 1)


if __name__ == "__main__":
    unittest.main()

"""The new exhibits reuse real animation and bounded Canvas pools."""
import math
import unittest
from unittest.mock import patch

from test_demos import DEMOS, make_app, state

NAMES = ("AuroraLandscape", "Armillary", "CrystalGarden")


class ImmersiveArtTests(unittest.TestCase):
    def test_registered_scenes_freeze_and_reset_deterministically(self):
        for name in NAMES:
            with self.subTest(scene=name):
                self.assertIn(name, DEMOS)
                app = make_app(name)
                initial = state(app)
                for _ in range(12):
                    app.frame(.025)
                self.assertGreater(len(app.stage.canvas.items), 80)
                app.stage.paused = True
                before = state(app)
                app.frame(0)
                app.frame(0)
                self.assertEqual(state(app), before)
                app.stage.reset_action = app.reset
                app.stage.reset()
                self.assertEqual(state(app), initial)

    def test_palettes_and_scaled_windows_use_bounded_finite_geometry(self):
        for name in NAMES:
            with self.subTest(scene=name):
                self.assertIn(name, DEMOS)
                app = make_app(name)
                for width, height in ((1000, 720), (760, 580)):
                    app.stage.screen.width, app.stage.screen.height = width, height
                    for _ in range(3):
                        app.change_theme()
                        app.frame(.05)
                    self.assertEqual(app.theme, 0)
                    self.assertLess(len(app.stage.canvas.items), 2000)
                peak = len(app.stage.canvas.items)
                for _ in range(80):
                    app.frame(.05)
                self.assertLessEqual(len(app.stage.canvas.items), peak + 40)

    def test_paused_clicks_and_scene_shortcuts_preserve_state(self):
        for name in NAMES:
            with self.subTest(scene=name):
                self.assertIn(name, DEMOS)
                app = make_app(name)
                app.frame(.05)
                app.stage.paused = True
                before = state(app)
                for key in ("C", "Up", "Down", "D", "G", "B", "W"):
                    if key in app.stage.screen.keys:
                        app.stage.screen.keys[key]()
                app.stage.screen.click(100, 50)
                self.assertEqual(state(app), before)

    def test_aurora_pointer_scaling_bounded_pools_and_expiry(self):
        self.assertIn("AuroraLandscape", DEMOS)
        app = make_app("AuroraLandscape")
        app.stage.screen.width, app.stage.screen.height = 760, 580
        scale = app.stage.scale
        for _ in range(30):
            app.touch(140*scale, 100*scale)
            app.touch(-100*scale, -175*scale)
        self.assertEqual(len(app.pulses), 6)
        self.assertEqual(len(app.ripples), 8)
        self.assertAlmostEqual(app.pulses[-1][0], 140)
        self.assertAlmostEqual(app.ripples[-1][1], -175)
        before = state(app)
        app.touch(0, 500*scale)
        self.assertEqual(state(app), before)
        app.frame(4)
        self.assertEqual(app.pulses, [])
        self.assertEqual(app.ripples, [])
        app.change_speed(100)
        self.assertEqual(app.speed, 2)
        app.change_speed(-100)
        self.assertEqual(app.speed, .25)

    def test_armillary_camera_projection_and_material_reset(self):
        app = make_app("Armillary")
        app.stage.screen.width, app.stage.screen.height = 760, 580
        scale = app.stage.scale
        app.select(-460*scale, -220*scale)
        self.assertEqual(app.target_yaw, -.62)
        old_yaw = app.view_yaw
        app.frame(.1)
        self.assertLess(app.view_yaw, old_yaw)
        self.assertGreater(app.view_yaw, app.target_yaw)
        for elapsed in (0, 30, 120, 600):
            app.time = elapsed
            for basis, (radius, _, _, _) in zip(app.bases(), app.RINGS):
                for step in range(16):
                    angle = step*math.tau/16
                    point = app.on_ring(basis, (math.cos(angle), math.sin(angle)), radius)
                    self.assertTrue(all(math.isfinite(value) for value in point))
                    self.assertLess(abs(point[0]), 470)
                    self.assertLess(abs(point[1]), 260)
        app.change_theme()
        app.reverse()
        app.stage.paused = True
        app.stage.reset_action = app.reset
        app.stage.reset()
        self.assertEqual((app.theme, app.direction, app.speed), (1, 1, 1))

    def test_crystal_light_tracks_scaled_pointer_and_freezes(self):
        app = make_app("CrystalGarden")
        app.stage.screen.width, app.stage.screen.height = 760, 580
        scale = app.stage.scale
        app.illuminate(450*scale, 240*scale)
        self.assertEqual(app.target, (430, 230))
        old_source = tuple(app.source)
        app.frame(.1)
        self.assertGreater(app.source[0], old_source[0])
        self.assertLess(app.source[0], app.target[0])
        app.frame(100)
        x, y = app.light_position()
        self.assertTrue(-454 <= x <= 445 and -242 <= y <= 234)
        app.toggle_beams()
        self.assertFalse(app.beams)
        before = state(app)
        app.illuminate(0, 900*scale)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        app.frame(.5)
        self.assertEqual(state(app), before)

    def test_armillary_reuses_stationary_globe_and_stays_within_draw_budget(self):
        app = make_app("Armillary")
        app.frame(0)
        canvas = app.stage.canvas
        globe = {key: item["coords"] for key, item in canvas.items.items()
                 if item["kind"] == "oval" and 98 < min(item["coords"][::2])
                 and max(item["coords"][::2]) < 193
                 and -80 < min(item["coords"][1::2]) < max(item["coords"][1::2]) < 20}
        self.assertGreater(len(globe), 12, "The globe should use native oval gradients")
        self.assertLessEqual(len(canvas.items), 1000)
        ids = set(canvas.items)
        with patch.object(canvas, "coords", wraps=canvas.coords) as update:
            app.frame(.025)
        changed = {call.args[0] for call in update.call_args_list}
        self.assertFalse(changed & globe.keys(), "Stationary globe coordinates should be retained")
        self.assertEqual(ids, set(canvas.items))
        for key, coords in globe.items():
            self.assertEqual(canvas.items[key]["coords"], coords)
        for width, height in ((760, 580), (1200, 840)):
            app.stage.screen.width, app.stage.screen.height = width, height
            app.change_theme()
            app.select(350*app.stage.scale, -100*app.stage.scale)
            app.frame(.3)
            self.assertEqual(ids, set(canvas.items))

    def test_armillary_retained_items_follow_depth_through_camera_changes(self):
        app = make_app("Armillary")
        app.frame(0)
        ids = set(app.stage.canvas.items)
        for elapsed, yaw, pitch in ((0, .27, .2), (1, -.62, .5),
                                     (38, .62, -.15), (300, .1, .3)):
            app.time = elapsed
            app.view_yaw = app.target_yaw = yaw
            app.view_pitch = app.target_pitch = pitch
            app.change_theme()
            app.frame(0)
            painter = app.paint
            expected = [entry[1][1] for entry in sorted(
                zip(painter.depth_values, painter.items[painter.depth_start:painter.index]),
                key=lambda entry: entry[0])]
            visible_order = [item for item in app.stage.canvas.stacking if item in set(expected)]
            self.assertEqual(visible_order, expected)
            self.assertEqual(list(painter.depth_order), expected)
            self.assertEqual(set(app.stage.canvas.items), ids)
            with patch.object(app.stage.canvas, "tag_raise", wraps=app.stage.canvas.tag_raise) as reorder:
                app.frame(0)
            # Background/foreground tags may be raised, individual pieces need no reorder.
            self.assertFalse(any(isinstance(call.args[0], int) for call in reorder.call_args_list))

    def test_armillary_ring_sampling_retains_subpixel_curvature(self):
        app = make_app("Armillary")
        for elapsed, yaw, pitch in ((0, .27, .2), (1, -.62, .5),
                                     (38, .62, -.15), (300, .1, .3)):
            app.time, app.view_yaw, app.view_pitch = elapsed, yaw, pitch
            for basis, (radius, width, count, _) in zip(app.bases(), app.RINGS):
                for index in range(count):
                    points = [app.on_ring(basis, (math.cos(a), math.sin(a)), radius+width/2)
                              for a in ((index+offset)*math.tau/count for offset in (0, .5, 1))]
                    a, middle, b = points
                    error = math.hypot(middle[0]-(a[0]+b[0])/2, middle[1]-(a[1]+b[1])/2)
                    self.assertLess(error, .3, "Ring simplification must preserve smooth curves")


if __name__ == "__main__":
    unittest.main()

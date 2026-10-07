"""The original four-way recursion stays measurable and interactive."""
import math
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalCircleTests(unittest.TestCase):
    def app(self):
        module = load_original('2.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return getattr(module, 'RecursiveCircles')()

    def test_recursion_halves_radius_and_places_four_tangent_children(self):
        module = load_original('2.py')
        nodes = module.circle_tree(2, radius=80)
        self.assertEqual(len(nodes), 21)
        root = nodes[0]
        self.assertEqual((root.x, root.y, root.radius, root.level), (0, 0, 80, 0))
        children = [node for node in nodes if node.level == 1]
        self.assertEqual({(node.x, node.y, node.radius) for node in children},
                         {(120, 0, 40), (-120, 0, 40), (0, 120, 40), (0, -120, 40)})
        parents = {node.path: node for node in nodes}
        for node in nodes[1:]:
            parent = parents[node.path[:-1]]
            self.assertAlmostEqual(math.hypot(node.x-parent.x, node.y-parent.y),
                                   parent.radius + node.radius)
            self.assertAlmostEqual(node.radius, parent.radius / 2)

    def test_depth_limits_bound_geometry_and_keep_the_full_pattern_in_view(self):
        app = self.app()
        for _ in range(20):
            app.stage.screen.keys['Up']()
        self.assertEqual(len(app.nodes), 341)
        for node in app.nodes:
            self.assertLessEqual(abs(node.x) + node.radius, 248)
            self.assertLessEqual(abs(node.y) + node.radius, 248)
        for _ in range(20):
            app.stage.screen.keys['Down']()
        self.assertEqual(len(app.nodes), 1)
        self.assertEqual(app.visible_depth, 0)

    def test_replay_advances_by_time_and_stops_at_requested_depth(self):
        app = self.app()
        app.change_palette()
        app.replay()
        self.assertEqual(app.visible_depth, 0)
        app.frame(.1)
        self.assertEqual(app.visible_depth, 0)
        app.frame(1)
        self.assertEqual(app.visible_depth, 1)
        app.frame(10)
        self.assertEqual(app.visible_depth, app.depth)
        self.assertEqual(app.palette, 1)
        app.stage.paused = True
        before = state(app)
        app.replay()
        app.frame(0)
        self.assertEqual(state(app), before)

    def test_pointer_uses_window_scale_and_selects_the_smallest_containing_circle(self):
        app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.frame(0)
        target = next(node for node in app.nodes if node.path == (0, 0, 0, 0))
        app.select(target.x * app.stage.scale, (target.y + app.CENTER_Y) * app.stage.scale)
        self.assertEqual(app.selected, target.path)
        before = state(app)
        app.select(420 * app.stage.scale, 180 * app.stage.scale)
        self.assertEqual(state(app), before)
        app.stage.paused = True
        app.select(0, app.CENTER_Y * app.stage.scale)
        self.assertEqual(state(app), before)
        app.stage.paused = False
        app.replay()
        app.select(target.x * app.stage.scale, (target.y + app.CENTER_Y) * app.stage.scale)
        self.assertIsNone(app.selected)

    def test_drawing_reuses_items_across_depth_selection_and_palette_changes(self):
        app = self.app()
        app.frame(.1)
        canvas = app.stage.canvas
        count = len(canvas.items)
        updates = canvas.coordinate_updates
        app.frame(.1)
        # Only a small set of moving rim lights needs new coordinates.
        self.assertLess(canvas.coordinate_updates - updates, 30)
        self.assertLess(count, 1200)
        for _ in range(3):
            for level in range(5):
                app.change_depth(-10)
                app.change_depth(level)
                app.change_palette()
                app.frame(.1)
                target = app.nodes[-1]
                app.select(target.x * app.stage.scale,
                           (target.y + app.CENTER_Y) * app.stage.scale)
                app.frame(.1)
            app.stage.screen.width, app.stage.screen.height = 760, 580
            app.frame(0)
        self.assertLess(len(canvas.items), 1200)
        self.assertLessEqual(len(canvas.items), count + 20)
        before = state(app)
        app.frame(0)
        self.assertEqual(state(app), before)


if __name__ == '__main__':
    unittest.main()

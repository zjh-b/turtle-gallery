"""Curve fidelity and interaction checks for the layered spirograph."""
import copy
import math
import unittest
from unittest.mock import patch

from test_demos import DEMOS, make_app


class SpirographVisualTests(unittest.TestCase):
    def test_display_curves_keep_subpixel_accuracy_at_every_preset_and_scale(self):
        module = DEMOS["Spirograph"]
        app = make_app("Spirograph")
        for preset in range(len(module.PRESETS)):
            app.choose(preset)
            self.assertEqual(len(app.points), 1601)
            for scale in (.6, 1, 2):
                with self.subTest(preset=preset, scale=scale):
                    app.prepare_display(scale)
                    for trace, indices in zip(app.traces, app.display_indices):
                        self.assertEqual((indices[0], indices[-1]), (0, 1600))
                        self.assertLess(len(indices), len(trace))
                        for left, right in zip(indices, indices[1:]):
                            ax, ay = trace[left]
                            bx, by = trace[right]
                            dx, dy = bx - ax, by - ay
                            length = dx * dx + dy * dy
                            for x, y in trace[left:right + 1]:
                                t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length)) if length else 0
                                error = math.hypot(x - ax - t * dx, y - ay - t * dy)
                                self.assertLessEqual(error * scale, module.TRACE_ERROR_PX + 1e-9)

    def test_palette_layers_and_gears_never_advance_time_or_drawing(self):
        app = make_app("Spirograph")
        app.redraw()
        app.frame(.7)
        state = (app.theta, app.progress, app.time, copy.deepcopy(app.points))
        for key in ("p", "L", "g", "P", "l", "G"):
            app.stage.screen.keys[key]()
            app.frame(0)
            self.assertEqual((app.theta, app.progress, app.time, app.points), state)

    def test_complete_traces_reuse_canvas_until_palette_layer_or_size_changes(self):
        app = make_app("Spirograph")
        app.frame(.1)
        with patch.object(app.paint, "line", wraps=app.paint.line) as draw:
            app.frame(.1)
            self.assertFalse(any(len(call.args[0]) > 100 for call in draw.call_args_list))
            for change in (app.change_palette, app.toggle_layers):
                draw.reset_mock()
                change()
                app.frame(0)
                self.assertTrue(any(len(call.args[0]) > 100 for call in draw.call_args_list))
            draw.reset_mock()
            app.stage.screen.width = 760
            app.stage.screen.height = 580
            app.frame(0)
            self.assertTrue(any(len(call.args[0]) > 100 for call in draw.call_args_list))

    def test_repeated_redraws_and_layer_switches_keep_canvas_bounded(self):
        app = make_app("Spirograph")
        sizes = []
        for cycle in range(3):
            app.redraw()
            for i in range(18):
                app.frame(app.period / 2.2 / 15)
                if i % 4 == 0:
                    app.toggle_layers()
                    app.change_palette()
                    app.toggle_gears()
            app.layered = True
            app.gears = False
            app.frame(0)
            self.assertEqual(app.progress, 1)
            sizes.append(len(app.stage.canvas.items))
        self.assertEqual(sizes[-1], sizes[-2])
        self.assertLess(max(sizes), 350)


if __name__ == "__main__":
    unittest.main()

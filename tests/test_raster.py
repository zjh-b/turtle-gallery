"""Offscreen vector rendering without a Tk window or desktop capture."""
from copy import deepcopy
import importlib
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
try:
    from PIL import Image, ImageChops, ImageFont
except ImportError:
    Image = ImageChops = ImageFont = None


def backend():
    return importlib.import_module("离屏绘制")


class RasterDependencyTests(unittest.TestCase):
    def test_import_does_not_require_pillow(self):
        script = """
import builtins, sys
sys.path.insert(0, sys.argv[1])
original = builtins.__import__
def without_pillow(name, *args, **kwargs):
    if name == 'PIL' or name.startswith('PIL.'):
        raise ImportError('Pillow deliberately unavailable')
    return original(name, *args, **kwargs)
builtins.__import__ = without_pillow
import 离屏绘制
assert callable(离屏绘制.render_commands)
try:
    离屏绘制.render_commands([], (10, 10), (10, 10), font_paths=(None, None))
except RuntimeError as error:
    assert 'Pillow' in str(error)
else:
    raise AssertionError('Rendering requires Pillow')
"""
        result = subprocess.run([sys.executable, "-X", "utf8", "-c", script,
                                 str(ROOT / "社团展示")], capture_output=True,
                                text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(Image is not None, "Pillow is an optional export dependency")
class RasterTests(unittest.TestCase):
    def render(self, commands, view=(100, 100), size=(200, 200), **kwargs):
        return backend().render_commands(commands, view, size,
                                         font_paths=kwargs.pop("font_paths", (None, None)),
                                         **kwargs)

    def test_centered_coordinates_use_canvas_y_down_and_preserve_layer_order(self):
        commands = [
            ("rectangle", (-50, -50, 50, 50), {"fill": "#112233", "outline": ""}),
            ("rectangle", (-40, -35, -10, -10), {"fill": "red", "outline": ""}),
            ("oval", (-30, -25, -20, -15), {"fill": "green", "outline": ""}),
            ("polygon", (10, 0, 40, 0, 25, 30), {"fill": "blue", "outline": ""}),
        ]
        before = deepcopy(commands)
        image = self.render(commands)
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (200, 200))
        self.assertEqual(image.getpixel((25, 40)), (255, 0, 0))
        self.assertEqual(image.getpixel((50, 60)), (0, 128, 0))
        self.assertEqual(image.getpixel((150, 125)), (0, 0, 255))
        self.assertEqual(image.getpixel((50, 150)), (17, 34, 51))
        self.assertEqual(commands, before)

    def test_output_mapping_preserves_landscape_portrait_and_square(self):
        for view, size in (((160, 90), (320, 180)), ((90, 160), (180, 320)),
                           ((100, 100), (200, 200))):
            with self.subTest(view=view):
                picture = self.render([("oval", (-5, -5, 5, 5), {"fill": "white"})],
                                      view, size)
                self.assertEqual(picture.size, size)
                self.assertEqual(picture.getpixel((size[0]//2, size[1]//2)), (255, 255, 255))
                self.assertEqual(picture.getpixel((0, 0)), (0, 0, 0))

    def test_round_line_caps_and_width_scale_with_output(self):
        image = self.render([("line", (-20, 0, 20, 0),
                             {"fill": "white", "width": 10, "capstyle": "round",
                              "joinstyle": "round", "dash": ()})])
        self.assertGreater(image.getpixel((53, 100))[0], 200)
        self.assertGreater(image.getpixel((100, 106))[0], 200)
        self.assertEqual(image.getpixel((100, 116)), (0, 0, 0))

    def test_smooth_line_is_quadratic_and_passes_through_open_endpoints(self):
        image = self.render([("line", (-30, 20, 0, -40, 30, 20),
                             {"fill": "white", "width": 3, "smooth": True})])
        # The quadratic's midpoint is (0, -10), not its control point (0, -40).
        self.assertGreater(image.getpixel((100, 80))[0], 200)
        self.assertEqual(image.getpixel((100, 20)), (0, 0, 0))
        self.assertGreater(image.getpixel((40, 140))[0], 100)
        self.assertGreater(image.getpixel((160, 140))[0], 100)

    def test_closed_smooth_contour_has_rounded_join_without_a_closing_chord(self):
        image = self.render([("line", (-30, -30, 30, -30, 30, 30, -30, 30, -30, -30),
                             {"fill": "white", "width": 3, "smooth": True})])
        self.assertGreater(image.getpixel((55, 55))[0], 180)
        self.assertGreater(image.getpixel((40, 100))[0], 180)
        self.assertGreater(image.getpixel((100, 40))[0], 180)
        self.assertEqual(image.getpixel((40, 40)), (0, 0, 0))
        self.assertEqual(image.getpixel((100, 100)), (0, 0, 0))

    def test_fractional_diagonal_edges_are_antialiased(self):
        image = self.render([("polygon", (-30.25, -30.25, 30.25, 20.5, -30.25, 20.5),
                             {"fill": "white", "outline": ""})])
        self.assertTrue(any(image.getchannel("R").histogram()[1:255]))

    def test_empty_fill_does_not_erase_earlier_shapes_and_hidden_items_are_skipped(self):
        image = self.render([
            ("rectangle", (-50, -50, 50, 50), {"fill": "#224466"}),
            ("oval", (-20, -20, 20, 20), {"fill": "", "outline": "white", "width": 2}),
            ("rectangle", (-10, -10, 10, 10), {"fill": "red", "state": "hidden"}),
        ])
        self.assertEqual(image.getpixel((100, 100)), (34, 68, 102))
        self.assertGreater(image.getpixel((61, 100))[0], 180)

    def test_rejects_invalid_size_and_ratio_before_image_allocation(self):
        cases = [((100, 100), (0, 10)), ((100, 100), (10.0, 10)),
                 ((100, 100), (True, 1)), ((100, 100), (100, 90)),
                 ((100, 100), (4000, 4000)), ((100, 100), (3000, 3000)),
                 ((0, 100), (200, 200)), ((float("nan"), 100), (200, 200))]
        for view, size in cases:
            with self.subTest(view=view, size=size), \
                    patch.object(Image, "new", side_effect=AssertionError("allocated before validation")), \
                    self.assertRaises(ValueError):
                self.render([], view, size)

    def test_rejects_unsupported_or_invalid_commands_before_image_allocation(self):
        commands = [
            ("arc", (0, 0, 10, 10), {}),
            ("line", (0, 0, 10, 10), {"dash": (3, 2)}),
            ("line", (0, 0, float("inf"), 10), {}),
            ("line", (0, 0, 10), {}),
            ("line", (0, 0, 10, 10), {"width": float("nan")}),
            ("polygon", (0, 0, 10, 10, 0, 10), {"smooth": True}),
            ("text", (0, 0), {"text": "hello", "font": ("font", 12, "normal"), "anchor": "ne"}),
        ]
        for command in commands:
            with self.subTest(command=command), \
                    patch.object(Image, "new", side_effect=AssertionError("allocated before validation")), \
                    self.assertRaises(ValueError):
                self.render([command])

    def test_rejects_excessive_commands_and_coordinates_before_image_allocation(self):
        for commands in ([('oval', (-1, -1, 1, 1), {})] * 5001,
                         [('line', (0, 0) * 100001, {})]):
            with self.subTest(count=len(commands)), \
                    patch.object(Image, "new", side_effect=AssertionError("allocated before validation")), \
                    self.assertRaises(ValueError):
                self.render(commands)

    def test_cancelled_request_does_not_allocate_an_image(self):
        cancel = threading.Event()
        cancel.set()
        with patch.object(Image, "new", side_effect=AssertionError("allocated after cancellation")), \
                self.assertRaises(backend().RenderCancelled):
            self.render([], cancel=cancel)

    def test_cancellation_after_downsampling_discards_result(self):
        cancel = threading.Event()
        resize = Image.Image.resize
        def resize_then_cancel(image, *args, **kwargs):
            result = resize(image, *args, **kwargs)
            cancel.set()
            return result
        with patch.object(Image.Image, "resize", resize_then_cancel), \
                self.assertRaises(backend().RenderCancelled):
            self.render([], cancel=cancel)


FONT = next((str(path) for path in (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
) if path.is_file()), None)


@unittest.skipUnless(Image is not None and FONT is not None, "Requires Pillow and a TrueType font")
class RasterFontTests(unittest.TestCase):
    render = RasterTests.render

    def text_image(self, anchor="center", size=10.25, bold=False, font_scale=4/3):
        return self.render([("text", (0, 0), {"text": "Hg", "fill": "white",
                            "font": ("Example", size, "bold" if bold else "normal"),
                            "anchor": anchor})], font_paths=(FONT, None), font_scale=font_scale)

    def test_text_anchor_positions_and_bold_falls_back_to_regular(self):
        centered, left, right = [self.text_image(anchor).getbbox() for anchor in ("center", "w", "e")]
        self.assertLess(abs((centered[0]+centered[2])/2-100), 3)
        self.assertGreaterEqual(left[0], 97)
        self.assertLessEqual(right[2], 103)
        self.assertLess(right[0], centered[0])
        self.assertGreater(left[2], centered[2])
        regular, bold = self.text_image(), self.text_image(bold=True)
        self.assertIsNone(ImageChops.difference(regular, bold).getbbox())

    def test_fractional_point_sizes_are_scaled_before_rounding(self):
        small, large = self.text_image(size=10.1), self.text_image(size=10.4)
        self.assertIsNotNone(ImageChops.difference(small, large).getbbox())
        scaled = self.text_image(size=10.1, font_scale=2)
        self.assertGreater(scaled.getbbox()[2]-scaled.getbbox()[0],
                           small.getbbox()[2]-small.getbbox()[0])

    def test_repeated_text_uses_cached_truetype_font(self):
        # A real load remains necessary; repeated glyphs should reuse its resource.
        with patch.object(ImageFont, "truetype", wraps=ImageFont.truetype) as load:
            self.text_image(size=17.321)
            first_count = load.call_count
            self.text_image(size=17.321)
            self.assertEqual(first_count, 1)
            self.assertEqual(load.call_count, 1)


if __name__ == "__main__":
    unittest.main()

"""Export dependency, pixel framing, and atomic-save behavior without a display."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
import 作品导出 as export

try:
    from PIL import Image
except ImportError:
    Image = None


class ExportDependencyTests(unittest.TestCase):
    def test_support_rejects_non_windows_even_with_pillow(self):
        import 作品导出 as export
        with patch.object(export.sys, "platform", "linux"):
            available, reason = export.export_support()
        self.assertFalse(available)
        self.assertIn("Windows", reason)

    def test_support_requires_window_capture_version(self):
        import 作品导出 as export
        for version, expected in (("11.2.0", False), ("11.2.1", True), ("12.3.0", True)):
            pil = SimpleNamespace(__version__=version, ImageGrab=object())
            with self.subTest(version=version), patch.object(export.sys, "platform", "win32"), \
                    patch.dict(sys.modules, {"PIL": pil}):
                available, reason = export.export_support()
                self.assertEqual(available, expected)
                if not expected:
                    self.assertIn("requirements-export.txt", reason)

    def test_module_import_and_support_work_without_optional_pillow(self):
        script = """
import builtins
import sys
sys.path.insert(0, sys.argv[1])
original_import = builtins.__import__
def without_pillow(name, *args, **kwargs):
    if name == 'PIL' or name.startswith('PIL.'):
        raise ImportError('Pillow deliberately unavailable')
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_pillow
import 作品导出
sys.platform = 'win32'
available, reason = 作品导出.export_support()
assert not available
assert 'python -m pip install -r requirements-export.txt' in reason
"""
        result = subprocess.run([sys.executable, "-X", "utf8", "-c", script, str(ROOT / "社团展示")],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Canvas:
    """Actual Canvas coordinates in a Turtle window with its default border."""
    def __init__(self, width=998, height=718):
        self.width, self.height = width, height

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def cget(self, key):
        return {"borderwidth": "2", "highlightthickness": "1"}[key]

    def winfo_pixels(self, distance):
        return int(distance)

    def canvasy(self, value):
        return value - self.height / 2

    def canvasx(self, value):
        return value - self.width / 2


class Snapshot:
    def __init__(self, size, box=None):
        self.size, self.box, self.mode = size, box, "RGBA"

    def crop(self, box):
        return Snapshot((box[2] - box[0], box[3] - box[1]), box)

    def convert(self, mode):
        self.mode = mode
        return self


class ExportCaptureTests(unittest.TestCase):
    def capture(self, raw_size=(1000, 720), client_size=(1000, 720),
                canvas_bounds=(1, 1, 998, 718), canvas_size=(998, 718), scale=1):
        root = SimpleNamespace(update_idletasks=lambda: None)
        canvas = Canvas(*canvas_size)
        stage = SimpleNamespace(root=root, canvas=SimpleNamespace(_canvas=canvas),
                                scale=scale, closed=False)
        def grab(*, window):
            self.assertEqual(window, 12345)
            return Snapshot(raw_size)
        pil = SimpleNamespace(ImageGrab=SimpleNamespace(grab=grab))
        with patch.object(export, "export_support", return_value=(True, "")), \
                patch.object(export, "_window_info", return_value=(12345, client_size, canvas_bounds)), \
                patch.dict(sys.modules, {"PIL": pil}):
            return export.capture_artwork(stage)

    def test_capture_removes_hud_footer_and_canvas_borders(self):
        image = self.capture()
        self.assertEqual(image.box, (4, 95, 996, 645))
        self.assertEqual(image.size, (992, 550))
        self.assertEqual(image.mode, "RGB")

    def test_capture_tracks_smaller_windows_and_canvas_origin(self):
        image = self.capture(raw_size=(800, 600), client_size=(800, 600),
                             canvas_bounds=(1, 1, 798, 598), canvas_size=(798, 598), scale=.8)
        self.assertEqual(image.box, (4, 88, 796, 528))
        self.assertEqual(image.size, (792, 440))

    def test_capture_maps_real_pixels_without_resizing_at_different_dpi(self):
        image = self.capture(raw_size=(1500, 1080))
        self.assertEqual(image.box, (6, 143, 1494, 967))
        self.assertEqual(image.size, (1488, 824))

    def test_capture_handles_canvas_and_win32_using_different_units(self):
        image = self.capture(raw_size=(2000, 1440), client_size=(2000, 1440),
                             canvas_bounds=(2, 2, 1996, 1436))
        self.assertEqual(image.box, (8, 190, 1992, 1290))
        self.assertEqual(image.size, (1984, 1100))

    def test_capture_rejects_empty_or_outside_drawing_area(self):
        for options in ({"raw_size": (0, 720)}, {"client_size": (0, 720)},
                        {"canvas_bounds": (1200, 1, 998, 718)}):
            with self.subTest(options=options), self.assertRaises(RuntimeError):
                self.capture(**options)

    def test_explicit_viewport_crops_exact_ratios_at_fractional_dpi(self):
        canvas = Canvas()
        for numerator, denominator, bounds in ((16, 9, (-464, 250, 464, -272)),
                                               (9, 16, (-144, 245, 144, -267)),
                                               (1, 1, (-260, 249, 260, -271))):
            for dpi in (1, 1.25, 1.5, 2):
                with self.subTest(ratio=(numerator, denominator), dpi=dpi):
                    box = export._artwork_box(canvas, 1, (int(1000*dpi), int(720*dpi)),
                        (1000, 720), (1, 1, 998, 718), bounds=bounds,
                        ratio=(numerator, denominator))
                    left, top, right, bottom = box
                    self.assertEqual((right-left)*denominator, (bottom-top)*numerator)
                    # Every output pixel is inside the requested artwork rectangle.
                    self.assertGreaterEqual(left, (500+bounds[0])*dpi)
                    self.assertLessEqual(right, (500+bounds[2])*dpi)
                    self.assertGreaterEqual(top, (360-bounds[1])*dpi)
                    self.assertLessEqual(bottom, (360-bounds[3])*dpi)

    def test_capture_restores_preview_guides_after_failure(self):
        visibility = []
        art = SimpleNamespace(aspect=2, bounds=(-144, 245, 144, -267), ratio=(9, 16),
                              draw_guides=visibility.append)
        stage = SimpleNamespace(closed=False, artwork=art, scale=1,
                                root=SimpleNamespace(update_idletasks=lambda: None), canvas=Canvas())
        pil = SimpleNamespace(ImageGrab=SimpleNamespace(grab=lambda **kwargs: None))
        with patch.object(export, "export_support", return_value=(True, "")), \
                patch.object(export, "_window_info", side_effect=RuntimeError("capture failed")), \
                patch.dict(sys.modules, {"PIL": pil}):
            with self.assertRaisesRegex(RuntimeError, "capture failed"):
                export.capture_artwork(stage)
        self.assertEqual(visibility, [False, True])

    def test_capture_rejects_unsupported_system_before_touching_stage(self):
        with patch.object(export, "export_support", return_value=(False, "Windows required")):
            with self.assertRaisesRegex(RuntimeError, "Windows required"):
                export.capture_artwork(None)

    def test_invalid_or_minimized_native_window_is_rejected(self):
        for valid, minimized in ((False, False), (True, True)):
            user32 = SimpleNamespace(GetAncestor=lambda handle, flags: 12345,
                                     IsWindow=lambda handle: valid,
                                     IsIconic=lambda handle: minimized,
                                     IsWindowVisible=lambda handle: True)
            with self.subTest(valid=valid, minimized=minimized), \
                    patch.object(export, "_user32", return_value=user32):
                with self.assertRaises(RuntimeError):
                    export._window_info(SimpleNamespace(winfo_id=lambda: 3), None)


class WritableImage:
    size = (13, 7)

    def __init__(self, fail=False):
        self.fail = fail

    def save(self, stream, **kwargs):
        stream.write(b"new png bytes")
        if self.fail:
            raise OSError("encoding failed")


class ExportSaveTests(unittest.TestCase):
    def test_encoding_failure_preserves_original_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "art.png"
            path.write_bytes(b"original png")
            with self.assertRaisesRegex(OSError, "encoding failed"):
                export.save_png(WritableImage(fail=True), path)
            self.assertEqual(path.read_bytes(), b"original png")
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_replace_failure_preserves_original_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "art.png"
            path.write_bytes(b"original png")
            with patch.object(export.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    export.save_png(WritableImage(), path)
            self.assertEqual(path.read_bytes(), b"original png")
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_atomic_save_uses_destination_directory_and_reports_original_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "作品.png"
            observed = []
            replace = export.os.replace
            def record_replace(source, destination):
                observed.append(Path(source).parent)
                replace(source, destination)
            with patch.object(export.os, "replace", side_effect=record_replace):
                size = export.save_png(WritableImage(), path)
            self.assertEqual(size, (13, 7))
            self.assertEqual(path.read_bytes(), b"new png bytes")
            self.assertEqual(observed, [Path(folder)])
            self.assertEqual(list(Path(folder).iterdir()), [path])

    @unittest.skipUnless(Image is not None, "Pillow is an optional export dependency")
    def test_saved_png_retains_pixels_size_and_unicode_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "实际图像.png"
            picture = Image.new("RGB", (23, 17), (12, 34, 56))
            metadata = {"work_id": 25, "parameters": {"seed": 251, "name": "彼岸花"}}
            self.assertEqual(export.save_png(picture, path, metadata), (23, 17))
            with Image.open(path) as saved:
                self.assertEqual(saved.format, "PNG")
                self.assertEqual(saved.mode, "RGB")
                self.assertEqual(saved.size, (23, 17))
                self.assertEqual(saved.getpixel((10, 8)), (12, 34, 56))
                self.assertEqual(json.loads(saved.info["turtle_gallery"]), metadata)


if __name__ == "__main__":
    unittest.main()

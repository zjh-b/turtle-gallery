"""Keep browser and desktop mirror geometry consistent without opening Tk."""
from collections import deque
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
from 万花筒参数 import mirror_points


class KaleidoscopeFormulaTests(unittest.TestCase):
    def test_export_ignores_platform_trigonometry_roundoff(self):
        spec = importlib.util.spec_from_file_location("gallery_export", ROOT / "tools/export_gallery.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "ROOT", Path(directory)):
            (Path(directory) / "docs").mkdir()
            destination = Path(directory) / "docs/play/kaleidoscope-config.json"
            module.export_kaleidoscope()
            expected = destination.read_bytes()
            for delta in (-1e-13, 1e-13):
                def perturbed(points, count):
                    return [[tuple(value + delta for value in point) for point in stroke]
                            for stroke in mirror_points(points, count)]
                with patch("万花筒参数.mirror_points", side_effect=perturbed):
                    module.export_kaleidoscope()
                self.assertEqual(destination.read_bytes(), expected)

    def test_cardinal_reflections_and_rotations_keep_original_point_order(self):
        actual = mirror_points([(10, 20)], 4)
        expected = [(10, -20), (10, 20), (20, 10), (-20, 10),
                    (-10, 20), (-10, -20), (-20, -10), (20, -10)]
        self.assertEqual(len(actual), len(expected))
        for stroke, wanted in zip(actual, expected):
            for got, want in zip(stroke[0], wanted):
                self.assertAlmostEqual(got, want)

    def test_desktop_add_ink_preserves_scale_canvas_y_direction_and_line_style(self):
        spec = importlib.util.spec_from_file_location("desktop_kaleidoscope", ROOT / "社团展示/03_鼠标万花筒.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = module.Kaleidoscope.__new__(module.Kaleidoscope)
        lines = []

        def create_line(*coords, **style):
            lines.append((coords, style))
            return len(lines)

        app.stage = SimpleNamespace(scale=1.5, canvas=SimpleNamespace(create_line=create_line))
        app.ink = deque()
        app.add_ink(((10, 20), (-30, 40), "#abcdef", 4))
        expected = [(15, 30, -45, 60), (15, -30, -45, -60),
                    (30, -15, 60, 45), (-30, -15, -60, 45),
                    (-15, -30, 45, -60), (-15, 30, 45, 60),
                    (-30, 15, -60, -45), (30, 15, 60, -45)]
        self.assertEqual(len(lines), 8)
        for (coords, style), wanted in zip(lines, expected):
            for got, want in zip(coords, wanted):
                self.assertAlmostEqual(got, want)
            self.assertEqual(style, dict(fill="#abcdef", width=2.25, capstyle="round", tags=("ink",)))
        self.assertEqual(list(app.ink), [list(range(1, 9))])


if __name__ == "__main__":
    unittest.main()

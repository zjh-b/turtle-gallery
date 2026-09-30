"""Shared heart formulas preserve desktop curves and portable browser fixtures."""
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
from 爱心参数 import heart_point, heartbeat, spread_at


class HeartFormulaTests(unittest.TestCase):
    def test_cardinal_points_keep_the_original_heart_orientation(self):
        for angle, expected in ((0, (0, 5)), (math.pi/2, (16, 4)),
                                (math.pi, (0, -17)), (math.pi*1.5, (-16, 4))):
            for actual, wanted in zip(heart_point(angle), expected):
                self.assertAlmostEqual(actual, wanted)

    def test_double_beat_and_spread_retain_the_desktop_motion(self):
        self.assertGreater(heartbeat(.18*1.55), 1)
        self.assertAlmostEqual(heartbeat(.18*1.55), heartbeat(1.55+.18*1.55))
        self.assertGreater(heartbeat(.34*1.55), .57)
        self.assertLess(heartbeat(.75*1.55), .001)
        for age, expected in ((None, 0), (0, 0), (.9, .5), (1.8, 1), (2.7, .5), (3.6, 0)):
            self.assertAlmostEqual(spread_at(age), expected)

    def test_export_ignores_platform_trigonometry_roundoff(self):
        spec = importlib.util.spec_from_file_location("heart_gallery_export", ROOT / "tools/export_gallery.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "ROOT", Path(directory)):
            (Path(directory) / "docs").mkdir()
            destination = Path(directory) / "docs/play/heart-config.json"
            module.export_heart()
            expected = destination.read_bytes()
            for delta in (-1e-13, 1e-13):
                with patch("爱心参数.heart_point", side_effect=lambda angle: tuple(v+delta for v in heart_point(angle))), \
                     patch("爱心参数.heartbeat", side_effect=lambda time: heartbeat(time)+delta), \
                     patch("爱心参数.spread_at", side_effect=lambda age: spread_at(age)+delta):
                    module.export_heart()
                self.assertEqual(destination.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()

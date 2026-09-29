"""Cross-language formulas keep the original desktop artwork geometry."""
import importlib.util
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
from 烟花参数 import initial_velocity, location


class FireworksFormulaTests(unittest.TestCase):
    def test_distinct_shapes_keep_hand_checked_cardinal_velocities(self):
        for kind, index, expected in ((0, 0, (66, 0)), (0, 21, (0, 120)),
                (1, 0, (64.8, 0)), (1, 21, (0, 35.1)),
                (2, 0, (0, 45)), (2, 21, (144, 36)),
                (3, 0, (120, 0)), (3, 63, (0, 144))):
            with self.subTest(kind=kind, index=index):
                actual = initial_velocity(kind, index, 120)
                for got, want in zip(actual, expected):
                    self.assertAlmostEqual(got, want)

    def test_location_retains_gravity_and_clamps_negative_age(self):
        particle = dict(x=5, y=10, vx=0, vy=0, gravity=46)
        self.assertEqual(location(particle, -1), (5, 10))
        self.assertEqual(location(particle, 2), (5, -82))

    def test_desktop_burst_retains_seeded_life_phase_gravity_and_velocity(self):
        spec = importlib.util.spec_from_file_location("desktop_fireworks", ROOT / "社团展示/01_点击烟花.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = module.Fireworks.__new__(module.Fireworks)
        app.particles, app.blooms, app.kind = [], [], 0
        previous = random.getstate()
        try:
            random.seed(51)
            app.burst(12, 34, 3, .2)
        finally:
            random.setstate(previous)
        expected = random.Random(51)
        speed = expected.uniform(95, 145)
        life = expected.uniform(1.65, 2.5)
        particle = app.particles[0]
        self.assertEqual(len(app.particles), 84)
        self.assertEqual((particle["x"], particle["y"], particle["vx"], particle["vy"]), (12, 34, speed, 0))
        self.assertEqual((particle["life"], particle["age"], particle["phase"], particle["gravity"]), (life, .2, 0, 75))


if __name__ == "__main__":
    unittest.main()

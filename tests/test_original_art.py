"""Original source files remain safe to import and usable outside the launcher."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = [('yeizi.py', 'ArcLeaves'), ('yusan.py', 'RainUmbrella'), ('风车.py', 'PaperPinwheel'),
             ('下落的小球.py', 'PrismBalls'), ('太极.py', 'YinYang'), ('时钟.py', 'GalleryClock'),
             ('2.py', 'RecursiveCircles'), ('import turtle.py', 'SquareSpiral'),
             ('哆啦A梦.py', 'DoraemonPortrait'), ('xin.py', 'ArcHeart'),
             ('分形树.py', 'BlossomTree'), ('见缝插针.py', 'NeedleGame'),
             ('弹窗.py', 'KindNotes'), ('测试.py', 'MooncakePacking')]


def load_original(filename):
    spec = importlib.util.spec_from_file_location('original_art_test', ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    with patch('turtle.Screen', side_effect=AssertionError('Import opened a window')):
        spec.loader.exec_module(module)
    return module


class OriginalArtTests(unittest.TestCase):
    def app(self, filename, name):
        module = load_original(filename)
        with patch.object(module, 'Stage', HeadlessStage):
            return getattr(module, name)()

    def test_package_stage_run_without_a_gallery_search_path(self):
        script = (
            'import sys; from types import SimpleNamespace; '
            'sys.path.insert(0, sys.argv[1]); '
            'from 社团展示.舞台 import Stage; '
            'stage = Stage.__new__(Stage); '
            'stage.reset = lambda: None; stage.tick = lambda: None; '
            'stage.screen = SimpleNamespace(mainloop=lambda: None); '
            'stage.run(lambda dt: None, lambda: None)'
        )
        with tempfile.TemporaryDirectory() as folder:
            environment = dict(os.environ)
            environment.pop('TURTLE_GALLERY_TOUR', None)
            result = subprocess.run([sys.executable, '-c', script, str(ROOT)], cwd=folder,
                                    env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_originals_import_without_a_window_and_freeze_on_zero_delta(self):
        for filename, name in ORIGINALS:
            with self.subTest(source=filename):
                module = load_original(filename)
                with patch.object(module, 'Stage', HeadlessStage):
                    app = getattr(module, name)()
                app.reset()
                app.frame(.04)
                self.assertGreater(len(app.stage.canvas.items), 50)
                before = state(app)
                app.frame(0)
                self.assertEqual(state(app), before)
                self.assertTrue({'space', 'r', 'h', 'F11', 'Escape', 'c'} <= set(app.stage.screen.keys))

    def test_repeated_interaction_keeps_rendering_bounded(self):
        for filename, name in ORIGINALS:
            with self.subTest(source=filename):
                module = load_original(filename)
                with patch.object(module, 'Stage', HeadlessStage):
                    app = getattr(module, name)()
                click = (0, -220) if name == 'RainUmbrella' else (120, -140)
                peaks = []
                for cycle in range(3):
                    for frame in range(36):
                        if frame % 6 == 0:
                            app.stage.screen.keys['c']()
                            app.stage.screen.click(*(value * app.stage.scale for value in click))
                        app.frame(.05)
                    app.stage.screen.width, app.stage.screen.height = 760, 580
                    app.frame(0)
                    peaks.append(len(app.stage.canvas.items))
                self.assertLess(max(peaks), 1200)
                self.assertLessEqual(peaks[-1], peaks[-2] + 20)
                app.stage.paused = True
                frozen = state(app)
                app.stage.screen.click(*(value * app.stage.scale for value in click))
                self.assertEqual(state(app), frozen)

    def test_leaf_and_water_clicks_only_affect_their_visible_regions(self):
        leaf = self.app('yeizi.py', 'ArcLeaves')
        umbrella = self.app('yusan.py', 'RainUmbrella')
        for app in (leaf, umbrella):
            app.stage.screen.width, app.stage.screen.height = 760, 580
            app.frame(.1)
            before = state(app)
            app.stage.screen.click(-450 * app.stage.scale, 240 * app.stage.scale)
            self.assertEqual(state(app), before)
        leaf.add_dew(115 * leaf.stage.scale, 113 * leaf.stage.scale)
        self.assertEqual(sum(drop is not None for drop in leaf.drops), 1)
        leaf.frame(3)
        self.assertTrue(all(drop is None for drop in leaf.drops))
        for _ in range(17):
            umbrella.ripple(0, -220 * umbrella.stage.scale)
        self.assertEqual(len(umbrella.ripples), 8)
        self.assertEqual(umbrella.ripple_cursor, 1)
        for x, y, start in umbrella.ripples:
            self.assertAlmostEqual(x, 0)
            self.assertAlmostEqual(y, -220)
            self.assertEqual(start, umbrella.time)

    def test_pinwheel_tracks_elapsed_time_and_gusts_end(self):
        first = self.app('风车.py', 'PaperPinwheel')
        second = self.app('风车.py', 'PaperPinwheel')
        for _ in range(100):
            first.frame(.01)
        for _ in range(10):
            second.frame(.1)
        self.assertAlmostEqual(first.angle, second.angle)
        angle = first.angle
        first.reverse()
        first.frame(.1)
        self.assertLess(first.angle, angle)
        first.blow(120, 20)
        self.assertGreater(first.gust, 0)
        first.frame(first.GUST_SECONDS)
        self.assertEqual(first.gust, 0)
        first.change_speed(-100)
        stopped = first.angle
        first.frame(1)
        self.assertEqual(first.angle, stopped)


if __name__ == '__main__':
    unittest.main()

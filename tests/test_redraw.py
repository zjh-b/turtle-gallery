"""Freeze current geometry and keep background exports independent of Tk."""
import copy
import importlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from test_demos import make_app, state


class RedrawTests(unittest.TestCase):
    def setUp(self):
        self.redraw = importlib.import_module("高清导出")

    def test_target_dimensions_are_explicit_and_reject_unbounded_sizes(self):
        for resolution, expected in ((1080, ((1920,1080),(1080,1920),(1080,1080))),
                                     (2160, ((3840,2160),(2160,3840),(2160,2160)))):
            for aspect, size in enumerate(expected, 1):
                self.assertEqual(self.redraw.target_size(aspect, resolution), size)
        for aspect, resolution in ((0,1080),(4,1080),(True,1080),(1,True),(1,1080.0),(1,99999)):
            with self.subTest(aspect=aspect, resolution=resolution), self.assertRaises(ValueError):
                self.redraw.target_size(aspect,resolution)

    def test_freezing_preserves_current_motion_and_never_touches_live_canvas(self):
        for name in ("StarryLily", "ParticleHeart"):
            for aspect in (1,2,3):
                app = make_app(name)
                app.apply_parameters(dict(app.get_parameters(),aspect=aspect))
                app.frame(3)
                if name == "StarryLily":
                    app.meteors = [[30,40,.3]]
                else:
                    app.burst_age = .6
                app.stage.paused = True
                before = state(app)
                canvas = copy.deepcopy(app.stage.canvas.items)
                updates = (app.stage.canvas.coordinate_updates,app.stage.canvas.option_updates)
                frozen = self.redraw.freeze_artwork(app)
                self.assertEqual(state(app),before)
                self.assertEqual(app.stage.canvas.items,canvas)
                self.assertEqual((app.stage.canvas.coordinate_updates,app.stage.canvas.option_updates),updates)
                self.assertTrue(app.stage.paused)
                self.assertGreater(len(frozen.commands),200)
                self.assertEqual(frozen.parameters,app.get_parameters())
                self.assertEqual(frozen.animation['time'],app.time)
                copied = copy.deepcopy(frozen.commands)
                app.frame(.25)
                app.apply_parameters(dict(app.get_parameters(),theme=(app.theme+1)%3))
                self.assertEqual(frozen.commands,copied)
                self.assertNotEqual(frozen.parameters,app.get_parameters())

    def test_snapshot_is_independent_of_preview_window_size(self):
        app = make_app("StarryLily")
        app.apply_parameters(dict(app.get_parameters(),aspect=2))
        app.frame(8)
        app.stage.screen.width,app.stage.screen.height = 760,580
        small = self.redraw.freeze_artwork(app)
        app.stage.screen.width,app.stage.screen.height = 1600,1000
        large = self.redraw.freeze_artwork(app)
        self.assertEqual(small.commands,large.commands)
        self.assertEqual(small.view,(540,960))

    def test_original_composition_is_rejected_without_mutating_scene(self):
        app = make_app("ParticleHeart")
        before = state(app)
        with self.assertRaises(ValueError):
            self.redraw.freeze_artwork(app)
        self.assertEqual(state(app),before)

    def test_worker_uses_frozen_metadata_and_returns_result_without_tk(self):
        app = make_app("StarryLily")
        app.apply_parameters(dict(app.get_parameters(),aspect=2))
        app.frame(4)
        frozen = self.redraw.freeze_artwork(app)
        image = FakeImage()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'art.png'
            records = []
            def save(picture, destination, metadata=None, cancel=None):
                records.append((picture,destination,metadata))
                return (1080,1920)
            with patch.object(self.redraw,'render_snapshot',return_value=image), \
                    patch.object(self.redraw,'save_png',side_effect=save):
                job = self.redraw.ExportJob(frozen,path,1080)
                job.thread.join(3)
            self.assertFalse(job.thread.is_alive())
            result = job.poll()
            self.assertEqual(result['state'],'saved')
            self.assertEqual(result['size'],(1080,1920))
            self.assertEqual(records[0][2]['Animation']['time'],4)
            self.assertEqual(records[0][2]['Resolution'],[1080,1920])
            self.assertEqual(records[0][2]['Recipe']['parameters'],frozen.parameters)
            self.assertTrue(image.closed)

    def test_cancel_and_failure_do_not_report_success(self):
        app = make_app("ParticleHeart")
        app.apply_parameters(dict(app.get_parameters(),aspect=1))
        frozen = self.redraw.freeze_artwork(app)
        entered, release = threading.Event(),threading.Event()
        def render(snapshot,resolution,cancel=None):
            entered.set()
            release.wait(3)
            return FakeImage()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'art.png'
            with patch.object(self.redraw,'render_snapshot',side_effect=render), \
                    patch.object(self.redraw,'save_png',side_effect=AssertionError('Cancelled export saved')):
                job=self.redraw.ExportJob(frozen,path,1080)
                self.assertTrue(entered.wait(3))
                job.cancel()
                release.set()
                job.thread.join(3)
                self.assertEqual(job.poll()['state'],'cancelled')
            with patch.object(self.redraw,'render_snapshot',side_effect=OSError('disk unavailable')):
                job=self.redraw.ExportJob(frozen,path,1080)
                job.thread.join(3)
                result=job.poll()
                self.assertEqual(result['state'],'error')
                self.assertIn('disk unavailable',result['message'])
            self.assertFalse(path.exists())


class FakeImage:
    closed = False
    def close(self):
        self.closed = True


@unittest.skipUnless(importlib.import_module("高清导出").redraw_support()[0],
                     "Requires Windows, optional Pillow and Microsoft YaHei")
class RedrawIntegrationTests(unittest.TestCase):
    def test_real_worker_draws_and_saves_without_window_capture(self):
        from PIL import Image, ImageGrab
        redraw = importlib.import_module("高清导出")
        with tempfile.TemporaryDirectory() as directory:
            for name, aspect, expected in (("StarryLily",2,(1080,1920)),
                                            ("ParticleHeart",3,(1080,1080))):
                with self.subTest(scene=name):
                    app=make_app(name)
                    app.apply_parameters(dict(app.get_parameters(),aspect=aspect))
                    app.frame(8)
                    snapshot=redraw.freeze_artwork(app)
                    path=Path(directory)/(name+'.png')
                    with patch.object(ImageGrab,'grab',side_effect=AssertionError('Redraw captured a window')):
                        job=redraw.ExportJob(snapshot,path,1080)
                        job.thread.join(10)
                    self.assertFalse(job.thread.is_alive())
                    self.assertEqual(job.poll()['state'],'saved')
                    with Image.open(path) as picture:
                        picture.load()
                        self.assertEqual(picture.size,expected)
                        self.assertGreater(picture.getextrema()[0][1],150)
                        metadata=json.loads(picture.info['turtle_gallery'])
                        self.assertEqual(metadata['Animation']['time'],8)
                        self.assertEqual(metadata['Recipe']['parameters'],snapshot.parameters)


if __name__ == '__main__':
    unittest.main()

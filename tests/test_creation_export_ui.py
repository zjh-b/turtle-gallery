"""Exercise export cancellation and failure through the real creator action."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "社团展示"))
from 创作工坊 import CreatorPanel
from 创作配方 import parameter_specs, preset_parameters
from 巡展 import TourClock


class Status:
    def set(self, value):
        self.value = value


class CreatorExportTests(unittest.TestCase):
    def test_palette_preset_keeps_the_selected_aspect(self):
        panel = CreatorPanel.__new__(CreatorPanel)
        panel.work_id = 25
        panel.presets = SimpleNamespace(current=lambda: 1)
        panel.apply_now = lambda: self.fail("A preset must replace invalid fields without applying them")
        panel.variables = {"aspect": SimpleNamespace(get=lambda: "竖屏 9:16"),
                           "seed": SimpleNamespace(get=lambda: "")}
        panel.app = SimpleNamespace(get_parameters=lambda: {"aspect": 0})
        applied = []
        panel.use_parameters = lambda values, message: applied.append(values)
        panel.choose_preset()
        expected = preset_parameters(25, 1)
        expected["aspect"] = 2
        self.assertEqual(applied, [expected])

    def test_safe_area_toggle_takes_over_tour_without_advancing_animation(self):
        panel = CreatorPanel.__new__(CreatorPanel)
        clock = TourClock(30)
        frames = []
        panel.stage = SimpleNamespace(artwork=SimpleNamespace(show_safe_area=False),
            tour=SimpleNamespace(pause=clock.pause), frame=frames.append, paused=True)
        panel.safe_area = SimpleNamespace(get=lambda: True)
        panel.toggle_safe_area()
        self.assertTrue(panel.stage.artwork.show_safe_area)
        self.assertTrue(clock.paused)
        self.assertEqual(frames, [0])
        self.assertTrue(panel.stage.paused)

    def test_keyboard_slider_takes_over_even_when_binding_stops_propagation(self):
        class Variable:
            value = 1.0
            def get(self):
                return self.value
            def set(self, value):
                self.value = value
        clock = TourClock(30)
        panel = CreatorPanel.__new__(CreatorPanel)
        panel.stage = SimpleNamespace(tour=SimpleNamespace(pause=clock.pause))
        panel._syncing = panel._closed = False
        panel._apply_job = None
        panel.variables, panel.value_labels = {"speed": Variable()}, {}
        panel.window = SimpleNamespace(after=lambda delay, callback: "scheduled")
        spec = next(spec for spec in parameter_specs(25) if spec.key == "speed")
        self.assertEqual(panel.step_slider(spec, 1), "break")
        self.assertAlmostEqual(panel.variables["speed"].get(), 1.05)
        self.assertTrue(clock.paused)

    def make_panel(self, paused=False):
        panel = CreatorPanel.__new__(CreatorPanel)
        panel.stage = SimpleNamespace(paused=paused, frame=lambda dt: None)
        panel.app = SimpleNamespace(get_parameters=lambda: {"seed": 2506})
        panel.work_id, panel.window, panel.status = 25, None, Status()
        panel.apply_now = lambda: True
        return panel

    def test_cancel_and_capture_failure_preserve_pause_state_and_write_nothing(self):
        for paused in (False, True):
            with self.subTest(paused=paused), tempfile.TemporaryDirectory() as directory:
                panel = self.make_panel(paused)
                core = SimpleNamespace(capture_artwork=lambda stage: object(),
                                       save_png=lambda *args, **kwargs: self.fail("Cancel wrote an image"))
                with patch.dict(sys.modules, {"作品导出": core}), \
                        patch("创作工坊.ROOT", Path(directory)), \
                        patch("创作工坊.filedialog.asksaveasfilename", return_value=""):
                    panel.export_png()
                self.assertEqual(panel.stage.paused, paused)
                self.assertFalse(list(Path(directory).rglob("*.png")))
                def unavailable(stage):
                    raise RuntimeError("Install optional export support")
                core.capture_artwork = unavailable
                with patch.dict(sys.modules, {"作品导出": core}), \
                        patch("创作工坊.filedialog.asksaveasfilename",
                              side_effect=AssertionError("Opened dialog after capture failed")):
                    panel.export_png()
                self.assertIn("Install optional export support", panel.status.value)
                self.assertEqual(panel.stage.paused, paused)

    def test_snapshot_is_captured_before_dialog_and_save_reports_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            panel = self.make_panel()
            state = {"frame": 7}
            def capture(stage):
                return state["frame"]
            def dialog(**kwargs):
                state["frame"] = 9  # Animation can run while the native dialog is open.
                return str(Path(directory) / "my-art.png")
            def save(image, path, metadata=None):
                Path(path).write_text(str(image), encoding="utf-8")
                return (1000, 550)
            core = SimpleNamespace(capture_artwork=capture, save_png=save)
            with patch.dict(sys.modules, {"作品导出": core}), \
                    patch("创作工坊.ROOT", Path(directory)), \
                    patch("创作工坊.filedialog.asksaveasfilename", side_effect=dialog):
                panel.export_png()
            self.assertEqual((Path(directory) / "my-art.png").read_text(), "7")
            self.assertIn("1000", panel.status.value)
            self.assertIn("550", panel.status.value)
            self.assertIn("my-art.png", panel.status.value)


if __name__ == "__main__":
    unittest.main()

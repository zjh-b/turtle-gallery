"""Creator actions freeze before dialogs and manage background exports safely."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_creation_export_ui import CreatorPanel, Status


class Variable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Window:
    def __init__(self):
        self.pending = {}
        self.serial = 0
        self.destroyed = False

    def after(self, delay, callback):
        if self.destroyed:
            raise AssertionError("Scheduled a Tk callback after destroy")
        self.serial += 1
        self.pending[self.serial] = callback
        return self.serial

    def after_cancel(self, token):
        self.pending.pop(token, None)

    def run_next(self):
        token = next(iter(self.pending))
        self.pending.pop(token)()

    def destroy(self):
        self.destroyed = True


class Job:
    def __init__(self, snapshot, path, resolution):
        self.snapshot, self.path, self.resolution = snapshot, path, resolution
        self.result = None
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def poll(self):
        return self.result


class HiresCreatorTests(unittest.TestCase):
    def setUp(self):
        def wrong_export(stage):
            raise RuntimeError("High resolution request used the window snapshot path")
        legacy = SimpleNamespace(capture_artwork=wrong_export, save_png=None)
        self.legacy_patch = patch.dict(sys.modules, {"作品导出": legacy})
        self.legacy_patch.start()
        self.addCleanup(self.legacy_patch.stop)

    def make_panel(self, aspect=1, paused=False):
        panel = CreatorPanel.__new__(CreatorPanel)
        panel.work_id = 25
        panel.window, panel.status = Window(), Status()
        panel._closed = False
        panel._apply_job = panel._poll_job = None
        panel._export_job = panel._export_poll_job = None
        panel.export_quality = Variable("高清重绘 · 1080")
        panel.export_hint = Variable()
        panel.button_options = {}
        panel.export_button = SimpleNamespace(configure=lambda **kw: panel.button_options.update(kw))
        panel.stage = SimpleNamespace(paused=paused, closed=False, frame=None,
            screen=SimpleNamespace(listen=lambda: None), artwork=SimpleNamespace(aspect=aspect))
        panel.stage.creator_panel = panel
        panel.parameters = {"aspect": aspect, "seed": 2506}
        panel.app = SimpleNamespace(get_parameters=lambda: dict(panel.parameters), time=7)
        panel.apply_now = lambda: True
        panel.variables = {}
        return panel

    def core(self, jobs):
        def start(snapshot, path, resolution):
            job = Job(snapshot, path, resolution)
            jobs.append(job)
            return job
        return SimpleNamespace(
            redraw_support=lambda: (True, ""),
            target_size=lambda aspect, resolution: {
                1: (resolution * 16 // 9, resolution),
                2: (resolution, resolution * 16 // 9),
                3: (resolution, resolution),
            }[aspect],
            freeze_artwork=lambda app: {"time": app.time, "parameters": app.get_parameters()},
            ExportJob=start,
        )

    def test_highres_freezes_parameters_and_time_before_dialog_without_pausing(self):
        for paused in (False, True):
            with self.subTest(paused=paused), tempfile.TemporaryDirectory() as directory:
                panel, jobs = self.make_panel(paused=paused), []
                def dialog(**kwargs):
                    panel.app.time = 9
                    panel.parameters["seed"] = 42
                    return str(Path(directory) / "picture.png")
                with patch.dict(sys.modules, {"高清导出": self.core(jobs)}), \
                        patch("创作工坊.ROOT", Path(directory)), \
                        patch("创作工坊.filedialog.asksaveasfilename", side_effect=dialog):
                    panel.export_png()
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0].snapshot, {"time": 7, "parameters": {"aspect": 1, "seed": 2506}})
                self.assertEqual(jobs[0].resolution, 1080)
                self.assertEqual(panel.stage.paused, paused)
                self.assertIn("取消", panel.button_options["text"])
                self.assertEqual(len(panel.window.pending), 1)

    def test_cancelled_filename_dialog_creates_no_job(self):
        with tempfile.TemporaryDirectory() as directory:
            panel, jobs = self.make_panel(paused=True), []
            with patch.dict(sys.modules, {"高清导出": self.core(jobs)}), \
                    patch("创作工坊.ROOT", Path(directory)), \
                    patch("创作工坊.filedialog.asksaveasfilename", return_value=""):
                panel.export_png()
            self.assertFalse(jobs)
            self.assertFalse(panel.window.pending)
            self.assertIn("取消", panel.status.value)
            self.assertTrue(panel.stage.paused)

    def test_original_aspect_missing_support_and_invalid_edits_never_open_dialog(self):
        for reason in ("aspect", "dependency", "invalid"):
            with self.subTest(reason=reason):
                panel, jobs = self.make_panel(aspect=0 if reason == "aspect" else 1), []
                core = self.core(jobs)
                if reason == "dependency":
                    core.redraw_support = lambda: (False, "需要安装 Pillow")
                if reason == "invalid":
                    panel.apply_now = lambda: False
                with patch.dict(sys.modules, {"高清导出": core}), \
                        patch("创作工坊.filedialog.asksaveasfilename",
                              side_effect=AssertionError("Invalid export opened file picker")):
                    panel.export_png()
                self.assertFalse(jobs)
                self.assertEqual(panel.parameters["aspect"], 0 if reason == "aspect" else 1)
                if reason == "aspect":
                    self.assertIn("画幅", panel.status.value)
                elif reason == "dependency":
                    self.assertIn("Pillow", panel.status.value)

    def start_job(self, panel, directory, jobs):
        with patch.dict(sys.modules, {"高清导出": self.core(jobs)}), \
                patch("创作工坊.ROOT", Path(directory)), \
                patch("创作工坊.filedialog.asksaveasfilename", return_value=str(Path(directory) / "art.png")):
            panel.export_png()
        self.assertEqual(len(jobs), 1)
        return jobs[0]

    def test_job_results_restore_export_action_and_report_saved_cancelled_or_error(self):
        for state in ("saved", "cancelled", "error"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                panel, jobs = self.make_panel(paused=True), []
                job = self.start_job(panel, directory, jobs)
                panel.window.run_next()
                self.assertEqual(len(panel.window.pending), 1)
                job.result = dict(state=state, path=job.path, size=(1920, 1080), message="磁盘空间不足")
                panel.window.run_next()
                self.assertIsNone(panel._export_job)
                self.assertFalse(panel.window.pending)
                self.assertIn("导出", panel.button_options["text"])
                self.assertNotIn("取消", panel.button_options["text"])
                self.assertTrue(panel.stage.paused)
                if state == "saved":
                    self.assertIn("1920 × 1080", panel.status.value)
                    self.assertIn("art.png", panel.status.value)
                elif state == "cancelled":
                    self.assertIn("取消", panel.status.value)
                else:
                    self.assertIn("磁盘空间不足", panel.status.value)

    def test_click_during_job_cancels_without_reapplying_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            panel, jobs = self.make_panel(), []
            job = self.start_job(panel, directory, jobs)
            panel.apply_now = lambda: self.fail("Cancellation reapplied settings")
            panel.export_png()
            self.assertTrue(job.cancelled)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(len(panel.window.pending), 1)

    def test_close_cancels_worker_and_prevents_callbacks_touching_destroyed_window(self):
        with tempfile.TemporaryDirectory() as directory:
            panel, jobs = self.make_panel(), []
            job = self.start_job(panel, directory, jobs)
            stale_callback = next(iter(panel.window.pending.values()))
            panel.close()
            self.assertTrue(job.cancelled)
            self.assertFalse(panel.window.pending)
            self.assertTrue(panel.window.destroyed)
            stale_callback()
            self.assertFalse(panel.window.pending)

    def test_hint_uses_selected_composition_and_quality(self):
        panel = self.make_panel()
        panel.variables["aspect"] = Variable("竖屏 9:16")
        panel.export_quality.set("高清重绘 · 2160")
        update = getattr(panel, "update_export_hint", None)
        self.assertTrue(callable(update), "Export quality needs a dimension preview")
        with patch.dict(sys.modules, {"高清导出": self.core([])}):
            update()
        self.assertIn("2160 × 3840", panel.export_hint.get())
        panel.variables["aspect"].set("原始画幅")
        with patch.dict(sys.modules, {"高清导出": self.core([])}):
            update()
        self.assertIn("画幅", panel.export_hint.get())


if __name__ == "__main__":
    unittest.main()

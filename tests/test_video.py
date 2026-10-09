"""Video timing and safe encoding; no FFmpeg, Pillow or window required."""
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import json
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))


class VideoTests(unittest.TestCase):
    def setUp(self):
        import render_video
        self.video = render_video

    def test_schedule_uses_integer_frames_and_covers_exact_duration(self):
        for fps in (24, 30):
            schedule = self.video.schedule(fps)
            self.assertEqual(schedule[0]["start_frame"], 0)
            self.assertEqual(schedule[-1]["end_frame"], 22 * fps)
            self.assertEqual([s["end_frame"] for s in schedule[:-1]],
                             [s["start_frame"] for s in schedule[1:]])
            self.assertEqual([s["work_id"] for s in schedule], [25, 25, 25, 26, 26])
        for fps in (0, True, 29.97, 120):
            with self.assertRaises(ValueError):
                self.video.schedule(fps)

    def test_subtitles_are_valid_both_languages_with_exact_endpoints(self):
        for lang in ("zh", "en"):
            srt = self.video.subtitles(lang)
            self.assertEqual(srt.count(" --> "), 5)
            self.assertIn("00:00:00,000 --> 00:00:02,000", srt)
            self.assertIn("00:00:18,000 --> 00:00:22,000", srt)
            self.assertIn("关注" if lang == "zh" else "Follow", srt)
        with self.assertRaises(ValueError):
            self.video.subtitles("unknown")

    def test_encoder_rejects_partial_frames_and_reports_failed_process(self):
        class Sink:
            def write(self, data):
                return len(data)
            def close(self):
                pass
        class Process:
            stdin = Sink()
            returncode = 7
            def wait(self, timeout=None):
                return self.returncode
            def poll(self):
                return self.returncode
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(self.video.subprocess, "Popen", return_value=Process()):
                encoder = self.video.Encoder("ffmpeg", Path(folder) / "test.mp4", (720, 1280), 30)
                with self.assertRaises(ValueError):
                    encoder.write(b"incomplete RGB")
                with self.assertRaisesRegex(RuntimeError, "FFmpeg"):
                    encoder.finish()

    def test_existing_output_is_preserved_without_loading_render_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "existing"
            target.mkdir()
            keep = target / "keep.txt"
            keep.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                self.video.produce(target, width=720, fps=30, language="zh")
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")

    def test_interrupt_during_encoder_finish_reaps_child_process(self):
        process = Mock()
        process.wait.side_effect = [KeyboardInterrupt(), 0]
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(self.video.subprocess, "Popen", return_value=process):
                encoder = self.video.Encoder("ffmpeg", Path(folder) / "test.mp4", (720, 1280), 30)
                with self.assertRaises(KeyboardInterrupt):
                    encoder.finish()
                self.assertTrue(process.kill.called)
                self.assertEqual(process.wait.call_count, 2)
                self.assertTrue(encoder.errors.closed)

    def test_cli_rejects_unsupported_dimensions_before_producing(self):
        parser = self.video.parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--width", "721"])

    def test_published_media_matches_its_recorded_files_and_source(self):
        root = TOOLS.parent
        folder = root / "docs/assets/social-01"
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        for name, data in manifest["files"].items():
            with self.subTest(asset=name):
                self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), data["sha256"])
        for name, digest in manifest["source_sha256"].items():
            with self.subTest(source=name):
                source = (root / name).read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(source).hexdigest(), digest)
        for language in ("zh", "en"):
            self.assertNotIn(b"\r", (folder / f"captions.{language}.srt").read_bytes())


if __name__ == "__main__":
    unittest.main()

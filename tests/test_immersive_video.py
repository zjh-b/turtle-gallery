"""Check that the published film remains traceable to its actual source and assets."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/social-immersive"


class ImmersiveVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))

    def test_delivered_files_match_record(self):
        self.assertEqual(set(self.manifest["files"]),
                         {"video.mp4", "cover.png", "cover-4x3.png", "storyboard.jpg", "captions.zh.srt"})
        for name, expected in self.manifest["files"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ASSETS / name).read_bytes()).hexdigest(), expected)

    def test_all_capture_and_compositor_sources_match(self):
        records = [self.manifest, *self.manifest["captures"]]
        for record in records:
            for name, expected in record["source_sha256_lf"].items():
                with self.subTest(source=name):
                    data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
                    self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_interactions_fit_the_delivered_timeline(self):
        self.assertEqual(self.manifest["size"], [1920, 1080])
        self.assertEqual(self.manifest["duration"], 20)
        self.assertEqual(sum(c["frames"] for c in self.manifest["captures"]),
                         self.manifest["frames"])
        for shot, capture in zip(self.manifest["shots"], self.manifest["captures"]):
            self.assertEqual(shot["work"], capture["work"])
            self.assertEqual(shot["end"] - shot["start"], capture["duration"])
            self.assertEqual(capture["frames"], capture["duration"] * self.manifest["fps"])
            self.assertEqual(len(capture["events"]), 2)
            for event in capture["events"]:
                self.assertLess(event["frame"], capture["frames"])
                self.assertGreaterEqual(event["frame"], 0)
                self.assertAlmostEqual(event["time"], event["frame"] / capture["fps"])


if __name__ == "__main__":
    unittest.main()

"""Verify the delivered audio samples, not just synthesis metadata."""
from array import array
import importlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import unittest
import uuid
import wave


class ButterflyAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(__file__).resolve().parents[1] / (
            ".test-butterfly-audio-" + uuid.uuid4().hex)
        cls.directory.mkdir()
        cls.addClassCleanup(shutil.rmtree, cls.directory)

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("tools.butterfly_audio"),
                             "The butterfly soundtrack synthesizer is missing")
        self.audio = importlib.import_module("tools.butterfly_audio")
        if not hasattr(type(self), "samples"):
            cls = type(self)
            cls.path = cls.directory / "soundtrack.wav"
            cls.metrics = self.audio.synthesize(cls.path, sample_rate=8000)
            with wave.open(str(cls.path), "rb") as recording:
                cls.parameters = recording.getparams()
                cls.samples = array("h", recording.readframes(recording.getnframes()))
            if sys.byteorder != "little":
                cls.samples.byteswap()

    def rms(self, begin, end):
        samples = self.samples[round(begin * 8000) * 2:round(end * 8000) * 2]
        return math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768

    def test_wav_has_exact_story_duration_and_pcm_stereo_format(self):
        self.assertEqual(self.parameters.nchannels, 2)
        self.assertEqual(self.parameters.sampwidth, 2)
        self.assertEqual(self.parameters.framerate, 8000)
        self.assertEqual(self.parameters.nframes, 160000)
        self.assertEqual(self.parameters.comptype, "NONE")
        self.assertEqual(len(self.samples), 320000)
        self.assertEqual(self.metrics["duration"], 20.0)
        self.assertEqual(self.metrics["channels"], 2)
        self.assertEqual(self.metrics["sample_rate"], 8000)
        self.assertEqual(self.metrics["cue_times"], [.8, 4., 8., 10.5, 12., 14., 14.2])
        json.dumps(self.metrics, allow_nan=False)

    def test_samples_are_non_silent_stereo_and_have_restrained_peak(self):
        peak = max(abs(value) for value in self.samples) / 32768
        rms = self.rms(0, 20)
        self.assertGreater(peak, .05)
        self.assertLessEqual(peak, 10 ** (-9 / 20))
        self.assertGreater(rms, .002)
        self.assertLess(rms, .10)
        self.assertNotEqual(self.samples[::2], self.samples[1::2])
        self.assertAlmostEqual(self.metrics["peak"], peak, places=6)
        self.assertAlmostEqual(self.metrics["rms"], rms, places=6)
        self.assertGreater(self.rms(.85, 1.), self.rms(.6, .75) * 1.5)
        self.assertGreater(self.rms(8.05, 8.3), self.rms(7.7, 7.95) * 1.5)

    def test_endpoints_are_silent_and_fades_are_smooth(self):
        self.assertEqual(list(self.samples[:2]), [0, 0])
        self.assertEqual(list(self.samples[-2:]), [0, 0])
        self.assertLess(self.rms(0, .02), self.rms(.15, .2) * .10)
        self.assertLess(self.rms(19.98, 20), self.rms(18.9, 19) * .01)
        self.assertLess(self.rms(19.7, 19.8), self.rms(19.1, 19.2) * .30)

    def test_repeated_synthesis_produces_identical_bytes_and_metrics(self):
        other = self.directory / "repeat.wav"
        metrics = self.audio.synthesize(other, sample_rate=8000)
        self.assertEqual(other.read_bytes(), self.path.read_bytes())
        self.assertEqual(metrics, self.metrics)

    def test_invalid_sample_rates_fail_before_creating_output(self):
        for rate in (0, -8000, True, 8000.0, 4000):
            with self.subTest(rate=rate):
                destination = self.directory / "invalid.wav"
                with self.assertRaises(ValueError):
                    self.audio.synthesize(destination, sample_rate=rate)
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()

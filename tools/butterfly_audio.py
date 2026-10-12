"""Original, deterministic music for the butterfly's 20-second story.

All sounds come from sine oscillators: a quiet, slowly moving chord and soft
glass bells. No recordings, downloaded samples, random sources or audio
dependencies are used. ``synthesize`` writes a stereo PCM16 WAV and returns
measurements of its quantized samples; peak/RMS are linear full-scale ratios.
"""
from array import array
import math
from pathlib import Path
import sys
import wave


DURATION = 20.0
# The capture story: three attractions, two palette changes and two motion
# toggles. Palette changes have a small rising figure; toggles use a lower bell.
_CUES = ((.8, "click", 783.9909, .30),
         (4., "click", 659.2551, -.30),
         (8., "color", 523.2511, 0.),
         (10.5, "motion", 391.9954, 0.),
         (12., "color", 587.3295, 0.),
         (14., "motion", 293.6648, 0.),
         (14.2, "click", 880., .25))


def _ease(amount):
    """Raised-cosine attack/release, with zero slope at both ends."""
    return .5 - .5 * math.cos(math.pi * min(1., max(0., amount)))


def _bell(left, right, sample_rate, start, frequency, strength, pan):
    offset = round(start * sample_rate)
    length = round(2.4 * sample_rate)
    gain_left = math.sqrt((1. - pan) / 2.)
    gain_right = math.sqrt((1. + pan) / 2.)
    for index in range(min(length, len(left) - offset)):
        elapsed = index / sample_rate
        phase = math.tau * frequency * elapsed
        # Slightly inharmonic upper partials make a gentle glass timbre.
        tone = (math.sin(phase) + .24 * math.sin(2.003 * phase)
                + .055 * math.sin(3.97 * phase))
        envelope = (_ease(elapsed / .018) * math.exp(-elapsed / .48)
                    * _ease((length - 1 - index) / sample_rate / .18))
        value = strength * tone * envelope
        left[offset + index] += value * gain_left
        right[offset + index] += value * gain_right


def synthesize(path, sample_rate=48000):
    """Write exactly 20 seconds of PCM16 stereo and return JSON-safe metrics.

    ``sample_rate`` must be an integer of at least 8000 Hz so every synthesized
    partial remains below Nyquist. Output peak is normalized to at most 0.32
    full scale (about -9.9 dBFS); fades are 0.2 seconds in and 1 second out.
    Identical inputs produce identical bytes on the same Python platform.
    """
    if type(sample_rate) is not int or sample_rate < 8000:
        raise ValueError("sample_rate must be an integer of at least 8000 Hz")
    frames = round(DURATION * sample_rate)
    left = array("d", [0.]) * frames
    right = array("d", [0.]) * frames
    chord = ((130.8128, .008), (195.9977, .006),
             (293.6648, .004), (329.6276, .003))
    for index in range(frames):
        elapsed = index / sample_rate
        swell = .78 + .22 * math.sin(math.tau * .065 * elapsed)
        for voice, (frequency, strength) in enumerate(chord):
            phase = math.tau * frequency * elapsed
            left[index] += swell * strength * math.sin(phase + voice * .35)
            right[index] += swell * strength * math.sin(phase * 1.0007 + voice * .47)

    for start, kind, frequency, pan in _CUES:
        if kind == "color":
            notes = ((523.2511, 659.2551, 783.9909) if start == 8.
                     else (587.3295, 783.9909, 880.))
            for step, note in enumerate(notes):
                _bell(left, right, sample_rate, start + step * .095,
                      note, .072, (step - 1) * .18)
        else:
            strength = .11 if kind == "click" else .048
            _bell(left, right, sample_rate, start, frequency, strength, pan)

    peak = 0.
    for index in range(frames):
        envelope = (_ease(index / sample_rate / .2)
                    * _ease((frames - 1 - index) / sample_rate))
        left[index] *= envelope
        right[index] *= envelope
        peak = max(peak, abs(left[index]), abs(right[index]))

    gain = .32 / peak
    pcm = array("h")
    sample_peak = 0
    sum_squares = 0
    for values in zip(left, right):
        for value in values:
            sample = round(value * gain * 32767)
            pcm.append(sample)
            sample_peak = max(sample_peak, abs(sample))
            sum_squares += sample * sample
    peak = sample_peak / 32768
    rms = math.sqrt(sum_squares / len(pcm)) / 32768
    if sys.byteorder != "little":
        pcm.byteswap()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as recording:
        recording.setnchannels(2)
        recording.setsampwidth(2)
        recording.setframerate(sample_rate)
        recording.writeframes(pcm.tobytes())
    return {"duration": frames / sample_rate, "channels": 2,
            "sample_rate": sample_rate, "peak": peak, "rms": rms,
            "peak_dbfs": 20 * math.log10(peak),
            "rms_dbfs": 20 * math.log10(rms),
            "cue_times": [cue[0] for cue in _CUES]}

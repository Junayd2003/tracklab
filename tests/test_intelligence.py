"""Tests for backend.audio.intelligence.

BPM and key detection are library calls with no firm ground truth
(decisions.md, 2026-08-22), so these tests check sane types, ranges,
and behaviour on synthetic signals -- not tight-tolerance correctness
the way Stages 3-5's from-scratch DSP is tested.
"""

import numpy as np
import pytest

from backend.audio.intelligence import _MAJOR_PROFILE, _MINOR_PROFILE, detect_bpm, detect_key

FS = 44_100


def _click_track(bpm: float, duration_s: float = 8.0, fs: int = FS) -> np.ndarray:
    """A synthetic click track: short percussive bursts at a fixed tempo."""
    n = int(fs * duration_s)
    signal = np.zeros(n)
    interval = int(fs * 60.0 / bpm)
    click_len = int(fs * 0.01)  # 10ms click
    for start in range(0, n - click_len, interval):
        signal[start : start + click_len] = 1.0
    return signal


def _chord_tone(root_freq: float, duration_s: float = 4.0, fs: int = FS) -> np.ndarray:
    """A simple triad (root, major third, fifth) to give chroma detection
    something with real harmonic content, rather than a single pitch."""
    t = np.arange(int(fs * duration_s)) / fs
    root = np.sin(2 * np.pi * root_freq * t)
    third = np.sin(2 * np.pi * root_freq * 2 ** (4 / 12) * t)
    fifth = np.sin(2 * np.pi * root_freq * 2 ** (7 / 12) * t)
    return root + third + fifth


def test_detect_bpm_returns_a_plain_float():
    bpm = detect_bpm(_click_track(120.0), FS)
    assert isinstance(bpm, float)


def test_detect_bpm_is_in_a_plausible_range():
    # Not asserting exact agreement -- beat tracking has no firm ground
    # truth (decisions.md) -- just that it lands somewhere musically
    # plausible rather than returning nonsense.
    bpm = detect_bpm(_click_track(120.0), FS)
    assert 20.0 < bpm < 400.0


def test_detect_key_returns_a_known_pitch_class_and_mode():
    key, mode = detect_key(_chord_tone(261.63), FS)  # C4 major triad
    assert key in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    assert mode in ["major", "minor"]


def test_detect_key_prefers_major_for_a_major_triad():
    key, mode = detect_key(_chord_tone(261.63), FS)  # C4 major triad
    assert mode == "major"


def test_key_profiles_are_correctly_shaped():
    # Sanity check on the Krumhansl-Kessler data itself: 12 chromatic
    # pitch classes, tonic rated most stable in both profiles.
    assert _MAJOR_PROFILE.shape == (12,)
    assert _MINOR_PROFILE.shape == (12,)
    assert np.argmax(_MAJOR_PROFILE) == 0
    assert np.argmax(_MINOR_PROFILE) == 0

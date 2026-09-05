"""Tests for backend.audio.frequency_balance."""

import numpy as np
import pytest

from backend.audio.frequency_balance import frequency_balance
from backend.audio.spectral import BAND_RANGES

FS = 44_100


def _sine(freq_hz: float, duration_s: float = 3.0, fs: int = FS) -> np.ndarray:
    t = np.arange(int(fs * duration_s)) / fs
    return np.sin(2 * np.pi * freq_hz * t)


def test_all_bands_present():
    balance = frequency_balance(_sine(1000.0), FS)
    assert set(balance.keys()) == set(BAND_RANGES.keys())


def test_all_values_are_at_most_zero_db():
    # Every band holds at most the track's entire energy, so relative
    # to the total, nothing can exceed 0dB.
    balance = frequency_balance(_sine(1000.0), FS)
    assert all(db <= 0.0 for db in balance.values())


def test_single_tone_dominates_its_own_band():
    # A pure 1kHz tone belongs entirely to "mid" (800-4000Hz) -- that
    # band should sit close to 0dB (holds ~all the energy), others
    # far below it.
    balance = frequency_balance(_sine(1000.0), FS)
    assert balance["mid"] > -1.0
    for name, db in balance.items():
        if name != "mid":
            assert db < balance["mid"] - 10.0


def test_linear_energies_sum_to_one():
    # Converting each dB value back to a linear fraction and summing
    # should recover the whole track's energy exactly (up to floating
    # point) -- a direct check that "relative to total" was computed
    # consistently.
    balance = frequency_balance(_sine(1000.0), FS)
    linear_fractions = [10 ** (db / 10) for db in balance.values()]
    assert sum(linear_fractions) == pytest.approx(1.0, rel=1e-9)


def test_low_end_balance_is_the_difference_between_sub_and_bass():
    balance = frequency_balance(_sine(100.0), FS)  # sits in "bass" (60-200Hz)
    low_end_balance = balance["sub"] - balance["bass"]
    # A bass-only tone should show strongly bass-heavy (negative) balance.
    assert low_end_balance < -10.0


def test_silence_returns_negative_infinity():
    silence = np.zeros(FS * 2)
    balance = frequency_balance(silence, FS)
    assert all(db == float("-inf") for db in balance.values())

"""Validate the from-scratch Welch implementation against scipy.signal.welch.

detrend=False is passed to scipy throughout: our implementation doesn't
remove each segment's mean first, since audio doesn't carry a
meaningful DC offset the way arbitrary sensor data might. Leaving
scipy's detrend='constant' default in place would compare two
deliberately different things and call the mismatch a bug.
"""

import numpy as np
import pytest
from scipy.signal import get_window
from scipy.signal import welch as scipy_welch

from backend.audio.spectral import _periodic_hann, _windowed_periodogram, welch

FS = 44_100
NPERSEG = 4096
NOVERLAP = 2048


def _sine(freq_hz: float, duration_s: float, fs: int = FS) -> np.ndarray:
    t = np.arange(int(fs * duration_s)) / fs
    return np.sin(2 * np.pi * freq_hz * t)


def test_periodic_hann_matches_scipy():
    mine = _periodic_hann(NPERSEG)
    reference = get_window("hann", NPERSEG)
    assert np.allclose(mine, reference, rtol=1e-12)


def test_periodic_hann_differs_from_symmetric_hann():
    # np.hanning is the symmetric variant -- confirming it's genuinely
    # different guards against silently reverting the window fix.
    assert not np.allclose(_periodic_hann(NPERSEG), np.hanning(NPERSEG))


def test_single_segment_periodogram_matches_scipy_welch():
    # noverlap=0, nperseg=len(signal) reduces scipy's Welch to exactly
    # one segment -- the same thing _windowed_periodogram computes alone.
    signal = _sine(1000.0, duration_s=NPERSEG / FS)
    window = _periodic_hann(NPERSEG)

    mine = _windowed_periodogram(signal, window, FS)
    _, reference = scipy_welch(
        signal, fs=FS, window=window, nperseg=NPERSEG, noverlap=0, detrend=False
    )
    assert np.allclose(mine, reference, rtol=1e-9)


@pytest.mark.parametrize("freq_hz", [100.0, 1000.0, 8000.0])
def test_welch_matches_scipy_on_pure_sine(freq_hz):
    signal = _sine(freq_hz, duration_s=2.0)

    freqs_mine, psd_mine = welch(signal, FS, nperseg=NPERSEG, noverlap=NOVERLAP)
    freqs_ref, psd_ref = scipy_welch(
        signal, fs=FS, window="hann", nperseg=NPERSEG, noverlap=NOVERLAP, detrend=False
    )

    assert np.allclose(freqs_mine, freqs_ref)
    assert np.allclose(psd_mine, psd_ref, rtol=1e-9)


def test_welch_matches_scipy_on_white_noise():
    rng = np.random.default_rng(42)
    signal = rng.standard_normal(FS * 2)

    freqs_mine, psd_mine = welch(signal, FS, nperseg=NPERSEG, noverlap=NOVERLAP)
    freqs_ref, psd_ref = scipy_welch(
        signal, fs=FS, window="hann", nperseg=NPERSEG, noverlap=NOVERLAP, detrend=False
    )

    assert np.allclose(freqs_mine, freqs_ref)
    assert np.allclose(psd_mine, psd_ref, rtol=1e-9)


def test_welch_locates_a_pure_tone_correctly():
    # A meaningful check beyond "matches scipy": does the estimate
    # actually mean anything on its own terms, in case both
    # implementations somehow shared a mistake.
    signal = _sine(1000.0, duration_s=2.0)
    freqs, psd = welch(signal, FS, nperseg=NPERSEG, noverlap=NOVERLAP)

    peak_freq = freqs[np.argmax(psd)]
    bin_width = FS / NPERSEG
    assert abs(peak_freq - 1000.0) < bin_width


def test_welch_rejects_signal_shorter_than_one_segment():
    signal = np.zeros(NPERSEG - 1)
    with pytest.raises(ValueError):
        welch(signal, FS, nperseg=NPERSEG)

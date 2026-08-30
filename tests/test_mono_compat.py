"""Validate mono_compatibility against theory: for two equal-amplitude
sinusoids at phase difference phi, the fraction of energy lost on
mono-summing is sin^2(phi/2) -- constructed ground truth, since there's
no reference library for "phase cancellation on mono sum" to validate
against instead.
"""

import numpy as np
import pytest

from backend.audio.mono_compat import mono_compatibility

FS = 44_100
DURATION_S = 3.0


def _phase_shifted_stereo(freq_hz: float, phi: float, duration_s: float = DURATION_S) -> np.ndarray:
    t = np.arange(int(FS * duration_s)) / FS
    left = np.sin(2 * np.pi * freq_hz * t)
    right = np.sin(2 * np.pi * freq_hz * t + phi)
    return np.stack([left, right])


@pytest.mark.parametrize(
    "phi,expected_loss",
    [
        (0.0, 0.0),  # in phase: nothing lost
        (np.pi / 2, 0.5),  # quadrature: half the energy lost
        (np.pi, 1.0),  # fully inverted: complete cancellation
    ],
)
def test_loss_matches_theoretical_prediction(phi, expected_loss):
    # 1kHz falls in the "mid" band (800-4000Hz).
    stereo = _phase_shifted_stereo(1000.0, phi)
    report = mono_compatibility(stereo, FS)
    assert report.band_loss["mid"] == pytest.approx(expected_loss, abs=0.01)


def test_worst_band_identifies_the_actual_affected_band():
    stereo = _phase_shifted_stereo(1000.0, np.pi)  # mid band
    report = mono_compatibility(stereo, FS)
    assert report.worst_band == "mid"


def test_score_reflects_severity():
    in_phase = mono_compatibility(_phase_shifted_stereo(1000.0, 0.0), FS)
    inverted = mono_compatibility(_phase_shifted_stereo(1000.0, np.pi), FS)
    assert in_phase.score == pytest.approx(100.0, abs=0.1)
    assert inverted.score == pytest.approx(0.0, abs=0.1)


def test_negligible_energy_bands_are_not_falsely_flagged():
    # A single 1kHz tone has virtually all its energy in "mid" -- the
    # sub/bass/low_mid/high bands only pick up spectral leakage, which
    # (before this was fixed) carried the same phase relationship as
    # the real tone and produced a spurious loss fraction there too.
    stereo = _phase_shifted_stereo(1000.0, np.pi / 2)
    report = mono_compatibility(stereo, FS)
    for band in ["sub", "bass", "low_mid", "high"]:
        assert report.band_loss[band] == 0.0


def test_mixed_content_score_is_proportional_to_energy_share():
    # Equal-energy bass (in phase, no loss) and mid (inverted, total
    # loss) tones should split the score roughly 50/50 -- proportional
    # to how much of the actual signal is affected, not an unweighted
    # average across all five fixed bands regardless of their content.
    t = np.arange(int(FS * DURATION_S)) / FS
    bass = np.sin(2 * np.pi * 100.0 * t)
    mid_left = np.sin(2 * np.pi * 1000.0 * t)
    mid_right = -mid_left

    left = bass + mid_left
    right = bass + mid_right
    stereo = np.stack([left, right])

    report = mono_compatibility(stereo, FS)
    assert report.score == pytest.approx(50.0, abs=1.0)


def test_real_signal_shape_gives_a_plausible_score():
    # A signal with content spread across multiple bands, all in
    # phase, should score close to perfect -- a basic sanity check
    # beyond the single-tone cases above.
    t = np.arange(int(FS * DURATION_S)) / FS
    mono = (
        np.sin(2 * np.pi * 100.0 * t)
        + np.sin(2 * np.pi * 1000.0 * t)
        + np.sin(2 * np.pi * 6000.0 * t)
    )
    stereo = np.stack([mono, mono])
    report = mono_compatibility(stereo, FS)
    assert report.score == pytest.approx(100.0, abs=0.1)

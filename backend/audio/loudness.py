"""Integrated loudness measurement per ITU-R BS.1770-4 (K-weighting + gating).

Uses the RBJ "Audio EQ Cookbook" biquad formulas for the K-weighting
filters -- a public, standard reference (see CONCEPTS.md), not a
library-specific choice. Filter *design* (deriving b/a coefficients)
and the two-stage gating algorithm are the from-scratch work; applying
an already-derived biquad via scipy.signal.lfilter is an execution
primitive, the same role np.fft.rfft played in spectral.py.
"""

import numpy as np
from scipy.signal import lfilter

# ITU-R BS.1770-4's defined calibration offset. Not derived from
# anything else in this file -- it's a fixed constant the standard
# specifies as part of what "LUFS" means.
_LUFS_OFFSET = -0.691

_ABSOLUTE_GATE_LUFS = -70.0
_RELATIVE_GATE_LU = -10.0

_BLOCK_DURATION_S = 0.400
_OVERLAP = 0.75


def _high_shelf_coefficients(fc: float, gain_db: float, q: float, fs: int):
    """RBJ cookbook high-shelf biquad. Approximates the boost in
    apparent loudness from head diffraction at high frequencies."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)
    sqrt_A = np.sqrt(A)

    b = np.array(
        [
            A * ((A + 1) + (A - 1) * cos_w0 + 2 * sqrt_A * alpha),
            -2 * A * ((A - 1) + (A + 1) * cos_w0),
            A * ((A + 1) + (A - 1) * cos_w0 - 2 * sqrt_A * alpha),
        ]
    )
    a = np.array(
        [
            (A + 1) - (A - 1) * cos_w0 + 2 * sqrt_A * alpha,
            2 * ((A - 1) - (A + 1) * cos_w0),
            (A + 1) - (A - 1) * cos_w0 - 2 * sqrt_A * alpha,
        ]
    )
    return b / a[0], a / a[0]


def _high_pass_coefficients(fc: float, q: float, fs: int):
    """RBJ cookbook high-pass biquad ("RLB" stage). Approximates reduced
    human sensitivity to low frequencies."""
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)

    b = np.array([(1 + cos_w0) / 2, -(1 + cos_w0), (1 + cos_w0) / 2])
    a = np.array([1 + alpha, -2 * cos_w0, 1 - alpha])
    return b / a[0], a / a[0]


def _k_weight(channel: np.ndarray, fs: int) -> np.ndarray:
    """Apply the full K-weighting chain: high-shelf, then high-pass."""
    b_shelf, a_shelf = _high_shelf_coefficients(fc=1500.0, gain_db=4.0, q=1 / np.sqrt(2), fs=fs)
    stage1 = lfilter(b_shelf, a_shelf, channel)

    b_hp, a_hp = _high_pass_coefficients(fc=38.0, q=0.5, fs=fs)
    return lfilter(b_hp, a_hp, stage1)


def integrated_loudness(stereo: np.ndarray, fs: int) -> float:
    """Measure integrated loudness in LUFS, per ITU-R BS.1770-4.

    `stereo` has shape (n_channels, n_samples), matching
    `LoadedAudio.stereo`. Both channels are weighted equally (gain 1.0
    each) -- BS.1770 only weights surround channels differently, which
    doesn't apply here.
    """
    n_channels, n_samples = stereo.shape
    weighted = np.stack([_k_weight(stereo[ch], fs) for ch in range(n_channels)])

    block_samples = int(_BLOCK_DURATION_S * fs)
    step_fraction = 1.0 - _OVERLAP  # fraction of a block advanced per step
    total_duration_s = n_samples / fs

    n_blocks = int(round((total_duration_s - _BLOCK_DURATION_S) / (_BLOCK_DURATION_S * step_fraction))) + 1
    if n_blocks < 1:
        raise ValueError(
            f"signal is {total_duration_s:.3f}s, shorter than one {_BLOCK_DURATION_S}s gating block"
        )

    channel_gain = np.ones(n_channels)  # BS.1770 stereo: both channels weighted 1.0

    # Mean square of the K-weighted signal, per channel, per block.
    z = np.zeros((n_channels, n_blocks))
    for j in range(n_blocks):
        lo = int(_BLOCK_DURATION_S * (j * step_fraction) * fs)
        hi = int(_BLOCK_DURATION_S * (j * step_fraction + 1) * fs)
        z[:, j] = np.mean(weighted[:, lo:hi] ** 2, axis=1)

    def block_loudness(z_col: np.ndarray) -> float:
        return _LUFS_OFFSET + 10.0 * np.log10(np.sum(channel_gain * z_col))

    with np.errstate(divide="ignore"):
        block_loudness_values = np.array([block_loudness(z[:, j]) for j in range(n_blocks)])

    # Stage 1: absolute gate. Drops near-silent blocks (e.g. a quiet
    # intro) that would otherwise drag the measured loudness down --
    # silence isn't part of what a listener perceives as "how loud is
    # this track."
    absolute_gated = block_loudness_values >= _ABSOLUTE_GATE_LUFS
    z_avg_absolute = np.mean(z[:, absolute_gated], axis=1)

    with np.errstate(divide="ignore"):
        relative_threshold = block_loudness(z_avg_absolute) + _RELATIVE_GATE_LU

    # Stage 2: relative gate. Drops blocks quiet *relative to the
    # track's own average* (e.g. a sparse breakdown) -- without this, a
    # loud track with one quiet section would measure as quieter than
    # it perceptually reads as a whole.
    doubly_gated = absolute_gated & (block_loudness_values > relative_threshold)
    z_avg_final = np.mean(z[:, doubly_gated], axis=1)

    with np.errstate(divide="ignore"):
        return block_loudness(z_avg_final)

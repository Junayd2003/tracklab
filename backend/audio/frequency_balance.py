"""Frequency balance: per-band energy relative to a track's own total.

Built on Stage 3's Welch estimator and band_energy() -- no genre
reference data lives here. A "genre reference curve" is just this same
function called on a track the user designates as a reference; picking
that track is a dashboard concern (Stage 8), not something to hardcode
here (see decisions.md, 2026-09-05).
"""

import numpy as np

from .spectral import BAND_RANGES, band_energy, welch


def frequency_balance(mono: np.ndarray, fs: int) -> dict[str, float]:
    """Each band's energy in dB, relative to the track's own total energy.

    Expressing every band relative to the track's own total (rather
    than an absolute level) normalises for loudness: two tracks with
    the same spectral *shape* get the same result here even if one is
    mixed several dB louder overall. Every value is <= 0dB, since a
    band can hold at most all of the total energy.

    Sub-vs-bass balance falls out of this for free: `result["sub"] -
    result["bass"]` is the dB relationship between the two bands
    (positive means sub-heavy), with no separate function needed --
    both are already expressed relative to the same total.
    """
    freqs, psd = welch(mono, fs)
    energy = band_energy(freqs, psd)
    total = sum(energy.values())

    if total <= 0:
        return {name: float("-inf") for name in BAND_RANGES}

    return {
        name: 10.0 * np.log10(e / total) if e > 0 else float("-inf")
        for name, e in energy.items()
    }

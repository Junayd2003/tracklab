"""Mono compatibility: per-band energy loss when summing stereo to mono."""

from dataclasses import dataclass

import numpy as np

from .spectral import BAND_RANGES, band_energy, welch


@dataclass
class MonoCompatibilityReport:
    band_loss: dict[str, float]  # band name -> fraction of energy lost on mono sum, in [0, 1]
    worst_band: str  # the band losing the most energy
    score: float  # 0-100, 100 = no phase cancellation detected in any band


def mono_compatibility(stereo: np.ndarray, fs: int) -> MonoCompatibilityReport:
    """Measure how much energy each frequency band loses when summed to mono.

    `mono` is derived here as `stereo.mean(axis=0)`, the same convention
    `load_audio()` uses -- not accepted as a separate argument, so this
    can never be called with a mono signal that wasn't actually derived
    from the same stereo pair being compared against.

    For two equal-amplitude sinusoids at phase difference phi, summing
    them and halving (the mean) gives an amplitude of cos(phi/2) times
    the original -- so the fraction of *energy* (amplitude squared)
    retained is cos^2(phi/2), and the fraction lost is sin^2(phi/2).
    At phi=0 (in phase), nothing is lost. At phi=pi (fully inverted),
    everything is. This is exactly what's being measured here, band by
    band, using each band's actual energy rather than a single
    frequency in isolation.
    """
    left, right = stereo[0], stereo[1]
    mono = stereo.mean(axis=0)

    freqs, psd_left = welch(left, fs)
    _, psd_right = welch(right, fs)
    _, psd_mono = welch(mono, fs)

    energy_left = band_energy(freqs, psd_left)
    energy_right = band_energy(freqs, psd_right)
    energy_mono = band_energy(freqs, psd_mono)

    # Average of the two channels' own energy per band: the baseline
    # "how much energy exists in the source", independent of what
    # summing does to it.
    source_energy = {name: (energy_left[name] + energy_right[name]) / 2 for name in BAND_RANGES}
    total_energy = sum(source_energy.values())

    # Spectral leakage puts a tiny residual of real signal content into
    # every band, not just the one it's actually in -- and that leaked
    # energy carries the same phase relationship as the tone it leaked
    # from, so a band with negligible real energy can still show a
    # spurious loss fraction that looks like a genuine finding. A band
    # needs a meaningful share of total energy before its loss fraction
    # means anything.
    _NEGLIGIBLE_ENERGY_FRACTION = 1e-6

    band_loss = {}
    for name in BAND_RANGES:
        if total_energy <= 0 or source_energy[name] / total_energy < _NEGLIGIBLE_ENERGY_FRACTION:
            band_loss[name] = 0.0
            continue
        loss = 1.0 - (energy_mono[name] / source_energy[name])
        band_loss[name] = float(np.clip(loss, 0.0, 1.0))

    worst_band = max(band_loss, key=band_loss.get)

    # Weighted by each band's actual share of the signal's energy, not
    # a plain average across the five fixed bands -- a track that's
    # entirely mid-range and loses all of it on mono-summing should
    # score near 0, not have that severity diluted by four other bands
    # that never had any real content to lose in the first place.
    if total_energy > 0:
        weighted_loss = sum(band_loss[name] * source_energy[name] for name in BAND_RANGES) / total_energy
    else:
        weighted_loss = 0.0
    score = 100.0 * (1.0 - weighted_loss)

    return MonoCompatibilityReport(band_loss=band_loss, worst_band=worst_band, score=float(score))

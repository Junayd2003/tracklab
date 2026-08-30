"""Power spectral density estimation via Welch's method, from scratch."""

import numpy as np


def _periodic_hann(n: int) -> np.ndarray:
    """A length-`n` Hann window, periodic rather than symmetric.

    `np.hanning(n)` gives the *symmetric* Hann window, which touches
    exactly zero at both endpoints. That's the wrong variant for
    FFT-based spectral analysis: the FFT implicitly treats a segment as
    one period of an infinitely repeating signal, and a symmetric
    window's duplicated zero endpoint breaks that periodicity slightly.
    The periodic (DFT-even) window below is the same shape but computed
    as if there were one *extra* sample past the end, at whatever point
    would make repeated copies tile smoothly — that extra sample is
    then simply never included in the returned array. Confirmed to
    match `scipy.signal.get_window('hann', n)` (what `scipy.signal.welch`
    uses internally) exactly, not just approximately.
    """
    i = np.arange(n)
    return 0.5 - 0.5 * np.cos(2 * np.pi * i / n)


def _windowed_periodogram(segment: np.ndarray, window: np.ndarray, fs: int) -> np.ndarray:
    """One segment's contribution to a Welch PSD estimate.

    Applies the window, takes the real FFT, and scales the result into
    units of power spectral density (V**2/Hz) using the same convention
    scipy.signal.welch uses, so the two are directly comparable.
    """
    windowed = segment * window
    spectrum = np.fft.rfft(windowed)

    # Normalise by the window's own power, not just its length: a window
    # that tapers samples toward zero at the edges removes energy, and
    # dividing by sum(window**2) compensates for exactly that loss.
    scale = 1.0 / (fs * np.sum(window**2))
    psd = scale * np.abs(spectrum) ** 2

    # rfft only returns non-negative frequencies (real input has a
    # symmetric spectrum), so it's discarding the negative-frequency
    # half of the energy. Double everything except DC and, for an even
    # segment length, the Nyquist bin, which have no negative-frequency
    # counterpart to fold in.
    psd[1:-1] *= 2

    return psd


def welch(
    signal: np.ndarray, fs: int, nperseg: int = 4096, noverlap: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate power spectral density via Welch's method.

    Splits `signal` into overlapping segments, computes a windowed
    periodogram for each (`_windowed_periodogram`), and averages them.
    Averaging independent noisy estimates is the entire benefit over a
    single periodogram taken on the whole signal at once.

    Unlike `scipy.signal.welch`'s default, this does not remove each
    segment's mean first (`detrend`). Audio signals don't carry a
    meaningful DC offset the way arbitrary sensor data might, so
    there's nothing here worth detrending.
    """
    if noverlap is None:
        noverlap = nperseg // 2
    step = nperseg - noverlap
    window = _periodic_hann(nperseg)

    n_segments = (len(signal) - nperseg) // step + 1
    if n_segments < 1:
        raise ValueError(
            f"signal has {len(signal)} samples, shorter than one {nperseg}-sample segment"
        )

    psd_sum = np.zeros(nperseg // 2 + 1)
    for i in range(n_segments):
        start = i * step
        segment = signal[start : start + nperseg]
        psd_sum += _windowed_periodogram(segment, window, fs)

    psd = psd_sum / n_segments
    freqs = np.fft.rfftfreq(nperseg, d=1 / fs)
    return freqs, psd


# Named frequency bands in Hz, per spec.md's Tier 1 mix-translation
# description (sub/bass boundaries are stated there explicitly;
# low-mid/mid/high extend the same vocabulary). Shared here rather than
# defined separately in mono_compat.py and again in Stage 6's
# frequency-balance feature, since both need the same band vocabulary
# to report against.
BAND_RANGES = {
    "sub": (0.0, 60.0),
    "bass": (60.0, 200.0),
    "low_mid": (200.0, 800.0),
    "mid": (800.0, 4000.0),
    "high": (4000.0, float("inf")),
}


def band_energy(freqs: np.ndarray, psd: np.ndarray) -> dict[str, float]:
    """Aggregate a PSD estimate into total power per named band.

    A PSD is power *per Hz* (a density), not power per bin -- so
    getting the actual power within a band means summing the PSD
    across that band's bins and multiplying by the frequency spacing
    between bins, approximating the integral of PSD over that band.
    """
    bin_width = freqs[1] - freqs[0]
    return {
        name: float(np.sum(psd[(freqs >= lo) & (freqs < hi)]) * bin_width)
        for name, (lo, hi) in BAND_RANGES.items()
    }

# tracklab — Code Guide

`CONCEPTS.md` is the theory-first companion — organised by stage,
explains *why* each piece of maths is correct, cites the literature.
This document is its code-first counterpart: the same stages, but
walking through the actual source, function by function, with the real
current code inline. Where `CONCEPTS.md` asks "why is this true," this
document asks "how does the code do it, and where does each piece come
from." The two cross-reference each other rather than repeating each
other — read `CONCEPTS.md` first for the theory behind something, then
this document to see exactly how that theory became code.

Same rule as `CONCEPTS.md`: this grows one stage at a time, once that
stage's code exists. Nothing here is speculative.

---

## Stage 2 — `backend/audio/loader.py`

Theory: [`CONCEPTS.md` § Stage 2](CONCEPTS.md#stage-2--audio-loading-and-format-handling).

### `hash_file()`

```python
def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at `path`.

    Read in fixed-size chunks rather than `path.read_bytes()` so a large
    WAV doesn't have to be pulled into memory all at once just to hash it.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
```

**Algorithm / origin:** SHA-256, specified in NIST FIPS 180-4. Not
implemented here — `hashlib.sha256()` is the standard library's own
implementation. What *is* deliberate here is how it's driven: the
Merkle–Damgård construction SHA-256 is built on processes its input in
512-bit blocks internally regardless of how it's called, so feeding it
1MB chunks via `.update()` is using the algorithm as designed, not
working around a limitation.

**Purpose here:** produces the cache key. Two uploads of byte-identical
audio must produce the identical hash, or the cache (Stage 6 onward)
can never recognise a re-upload.

**Called from:** `load_audio()` (below), and directly by anything that
only needs the hash without decoding the audio — e.g. a future upload
endpoint checking the cache *before* paying the cost of decoding at
all.

**Logic:** `sha256 = hashlib.sha256()` creates an empty running hash
state. The file is opened in binary mode (`"rb"`) inside a `with`
block, so it's guaranteed closed even if an exception fires partway
through. `iter(lambda: f.read(1024 * 1024), b"")` is the two-argument
form of `iter()`: it calls the lambda repeatedly, yielding each result,
until the result equals the sentinel (`b""`, what `f.read()` returns at
end-of-file). Each yielded `chunk` is fed into `sha256.update()`,
folding it into the running state. Once the loop ends, `.hexdigest()`
returns the final state as a 64-character hex string.

---

### `is_lossy()`

```python
def is_lossy(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {suffix}")
    return suffix in LOSSY_FORMATS
```

**Algorithm / origin:** not an algorithm in the mathematical sense —
just a classification lookup against two module-level sets:

```python
LOSSLESS_FORMATS = {".wav", ".flac", ".aiff", ".aif"}
LOSSY_FORMATS = {".mp3", ".m4a", ".aac", ".mp4", ".ogg"}
SUPPORTED_FORMATS = LOSSLESS_FORMATS | LOSSY_FORMATS
```

**Purpose here:** flags files whose high-frequency content was
discarded by a psychoacoustic encoder (see `CONCEPTS.md`'s auditory
masking section) so later frequency-balance analysis doesn't
misinterpret a codec artefact as a mixing decision.

**Called from:** `load_audio()`. Also directly testable in isolation —
it never opens the file, only inspects the extension, which is why
`tests/test_loader.py` can check it against bare `Path` objects that
don't need to exist on disk.

**Logic:** extension comparison is case-insensitive (`.lower()`, so
`TRACK.MP3` and `track.mp3` behave identically). An extension outside
`SUPPORTED_FORMATS` raises rather than silently guessing — a file this
project can't classify shouldn't be analysed at all, since the
mono/frequency-balance numbers downstream depend on knowing this.
`SUPPORTED_FORMATS` is a `|` (set union) of the other two rather than a
third hand-typed set, so there's exactly one place in the source that
lists each extension — see `decisions.md`, 2026-08-21.

---

### `LoadedAudio`

```python
@dataclass
class LoadedAudio:
    mono: np.ndarray  # shape (n_samples,)
    stereo: np.ndarray  # shape (2, n_samples), channel 0 = left, 1 = right
    sample_rate: int
    duration: float
    is_lossy: bool
    file_hash: str
    format: str  # file extension, e.g. ".mp3"
```

**Algorithm / origin:** Python's `@dataclass` decorator (PEP 557) —
generates `__init__`, `__repr__`, `__eq__` from the field list.

**Purpose here:** the single return type every downstream stage
consumes. `mono_compatibility()` (Stage 5) and `integrated_loudness()`
(Stage 4) both take arrays that ultimately came from a `LoadedAudio`
instance's `.mono`/`.stereo` fields.

**Called from:** constructed once, at the end of `load_audio()`.

**Logic:** nothing computational — it's a typed container. The
comments on `mono`/`stereo` document the array shapes, since NumPy
doesn't enforce them at the type level the way the field names alone
might suggest it does.

---

### `load_audio()`

```python
def load_audio(path: Path) -> LoadedAudio:
    path = Path(path)
    lossy = is_lossy(path)  # also validates the format is supported

    y, sr = librosa.load(path, sr=TARGET_SAMPLE_RATE, mono=False)

    if y.ndim == 1:
        # Source file only had one channel. Duplicate it so `stereo` always
        # has a consistent (2, n_samples) shape for downstream code.
        stereo = np.stack([y, y])
        mono = y
    else:
        stereo = y
        mono = stereo.mean(axis=0)

    sr = int(sr)
    duration = stereo.shape[1] / sr

    return LoadedAudio(
        mono=mono,
        stereo=stereo,
        sample_rate=sr,
        duration=duration,
        is_lossy=lossy,
        file_hash=hash_file(path),
        format=path.suffix.lower(),
    )
```

**Algorithm / origin:** resampling itself is `librosa.load`'s job
(delegating to `soxr`, per `CONCEPTS.md`'s Nyquist–Shannon section);
the logic worth calling "ours" is the mono-derivation policy below it.

**Purpose here:** the single entry point every stage after Stage 2
starts from — nothing else in the codebase calls `librosa.load`
directly.

**Called from:** `tests/test_loader.py`; will be called by Stage 6/7's
orchestration pipeline once that exists (not yet — see `STAGES.md`).

**Logic:** `librosa.load(..., mono=False)` decodes once, preserving
channels. If the source only had one channel, librosa returns a 1-D
array (`y.ndim == 1`); that branch duplicates it into a `(2, n)` pair
so `stereo` always has a predictable shape. Otherwise, `mono =
stereo.mean(axis=0)` — the average of the two channels, computed here
rather than by asking librosa to decode the file a second time with
`mono=True`. This isn't just an efficiency choice: Stage 5's
`mono_compatibility()` needs `mono` to be *exactly* the average of
`stereo`'s two channels, since that relationship is what reveals phase
cancellation — a separately-decoded mono copy wouldn't guarantee it.
`hash_file(path)` is called last, against the original file on disk
(not the decoded array), so the hash reflects the exact bytes uploaded.

---

## Stage 3 — `backend/audio/spectral.py`

Theory: [`CONCEPTS.md` § Stage 3](CONCEPTS.md#stage-3--welch-spectral-estimation-from-scratch).

### `_periodic_hann()`

```python
def _periodic_hann(n: int) -> np.ndarray:
    i = np.arange(n)
    return 0.5 - 0.5 * np.cos(2 * np.pi * i / n)
```

**Algorithm / origin:** the periodic (DFT-even) Hann window — confirmed
to match `scipy.signal.get_window('hann', n)` exactly (`CONCEPTS.md`
documents the bug found by *not* using this variant).

**Purpose here:** tapers each Welch segment's edges toward zero before
its FFT, so the segment's artificial boundary doesn't smear energy
across frequency bins that shouldn't have any (spectral leakage).

**Called from:** `welch()`, once per call, to build the window used for
every segment in that call.

**Logic:** `i = np.arange(n)` gives sample indices `0, 1, ..., n-1`.
`0.5 - 0.5*cos(2*pi*i/n)` is the periodic Hann formula — dividing by
`n`, not `n-1`, is the entire difference from `np.hanning(n)`'s
symmetric variant, and it's the one line that mattered for the bug
documented in `CONCEPTS.md`.

---

### `_windowed_periodogram()`

```python
def _windowed_periodogram(segment: np.ndarray, window: np.ndarray, fs: int) -> np.ndarray:
    windowed = segment * window
    spectrum = np.fft.rfft(windowed)

    scale = 1.0 / (fs * np.sum(window**2))
    psd = scale * np.abs(spectrum) ** 2

    psd[1:-1] *= 2

    return psd
```

**Algorithm / origin:** one segment's contribution to a Welch estimate
— the "modified periodogram" from Welch's own 1967 title. The FFT
itself is `np.fft.rfft`; nothing here reimplements the Fourier
transform.

**Purpose here:** every PSD value this project ever produces —
frequency balance, mono-compatibility energy — traces back to a call
to this function.

**Called from:** `welch()`, once per segment.

**Logic:** `segment * window` applies the taper elementwise.
`np.fft.rfft` computes the real FFT — only non-negative frequencies,
since a real-valued signal's full spectrum is symmetric and the
negative half carries no new information. `scale = 1/(fs *
sum(window**2))` does two jobs at once: dividing by `fs` converts raw
squared-magnitude into power *per Hz* (comparable across sample rates
and segment lengths); dividing by the window's own summed squared value
compensates for the energy the window removed by tapering samples
toward zero. `psd[1:-1] *= 2` restores the energy `rfft` discarded by
dropping the negative-frequency half — every bin except DC (index 0)
and Nyquist (the last bin, for an even segment length) gets doubled,
since those two have no negative-frequency counterpart to fold in.

---

### `welch()`

```python
def welch(
    signal: np.ndarray, fs: int, nperseg: int = 4096, noverlap: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
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
```

**Algorithm / origin:** Welch's method (Welch, 1967 — DOI in
`CONCEPTS.md`'s Stage 3 references). Segment, window, periodogram,
average — the four words that are the whole algorithm.

**Purpose here:** the single PSD estimator every other frequency-domain
feature in this project is built on: mono compatibility now (Stage 5),
frequency balance against a reference curve later (Stage 6).

**Called from:** `mono_compat.mono_compatibility()`, three times per
call (left channel, right channel, mono sum); `tests/test_spectral.py`
directly.

**Logic:** `step = nperseg - noverlap` is how far each segment's start
advances — 50% overlap by default (`noverlap = nperseg // 2`) means
each segment shares half its samples with the next. `n_segments =
(len(signal) - nperseg) // step + 1` counts how many full,
non-overrunning segments fit — the standard "how many windows fit"
formula, confirmed in `CONCEPTS.md` to be mathematically identical to
`scipy`'s own internal formula despite looking different. The loop
slices out each segment, scores it via `_windowed_periodogram`, and
accumulates the sum; dividing by `n_segments` at the end is the
"average" in Welch's method, the step that actually reduces variance
relative to a single periodogram over the whole signal.

---

### `BAND_RANGES` and `band_energy()`

```python
BAND_RANGES = {
    "sub": (0.0, 60.0),
    "bass": (60.0, 200.0),
    "low_mid": (200.0, 800.0),
    "mid": (800.0, 4000.0),
    "high": (4000.0, float("inf")),
}


def band_energy(freqs: np.ndarray, psd: np.ndarray) -> dict[str, float]:
    bin_width = freqs[1] - freqs[0]
    return {
        name: float(np.sum(psd[(freqs >= lo) & (freqs < hi)]) * bin_width)
        for name, (lo, hi) in BAND_RANGES.items()
    }
```

**Algorithm / origin:** numerical integration of a PSD via a Riemann
sum — summing PSD values across a band's bins and multiplying by the
(constant) bin spacing approximates `∫ PSD(f) df` over that band, since
a PSD is power *per Hz*, not power per bin.

**Purpose here:** shared band vocabulary — added to `spectral.py`
rather than duplicated in `mono_compat.py`, since Stage 6's
frequency-balance feature needs the identical bands (`decisions.md`,
2026-08-30).

**Called from:** `mono_compat.mono_compatibility()`, three times per
call, on the same three PSDs `welch()` produced.

**Logic:** `bin_width = freqs[1] - freqs[0]` — Welch's output has
uniformly spaced frequency bins, so any adjacent pair's spacing is the
spacing. The dict comprehension builds one entry per named band:
`(freqs >= lo) & (freqs < hi)` is a boolean mask selecting that band's
bins, `np.sum(psd[mask])` sums the PSD values inside it, and
multiplying by `bin_width` converts that sum into an actual power
figure.

---

## Stage 4 — `backend/audio/loudness.py`

Theory: [`CONCEPTS.md` § Stage 4](CONCEPTS.md#stage-4--lufs-loudness-from-scratch-itu-r-bs1770).

### `_high_shelf_coefficients()` and `_high_pass_coefficients()`

```python
def _high_shelf_coefficients(fc: float, gain_db: float, q: float, fs: int):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)
    sqrt_A = np.sqrt(A)

    b = np.array([
        A * ((A + 1) + (A - 1) * cos_w0 + 2 * sqrt_A * alpha),
        -2 * A * ((A - 1) + (A + 1) * cos_w0),
        A * ((A + 1) + (A - 1) * cos_w0 - 2 * sqrt_A * alpha),
    ])
    a = np.array([
        (A + 1) - (A - 1) * cos_w0 + 2 * sqrt_A * alpha,
        2 * ((A - 1) - (A + 1) * cos_w0),
        (A + 1) - (A - 1) * cos_w0 - 2 * sqrt_A * alpha,
    ])
    return b / a[0], a / a[0]


def _high_pass_coefficients(fc: float, q: float, fs: int):
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)

    b = np.array([(1 + cos_w0) / 2, -(1 + cos_w0), (1 + cos_w0) / 2])
    a = np.array([1 + alpha, -2 * cos_w0, 1 - alpha])
    return b / a[0], a / a[0]
```

**Algorithm / origin:** the RBJ "Audio EQ Cookbook" biquad design
equations (Robert Bristow-Johnson — link in `CONCEPTS.md`), the same
public formulas `pyloudnorm`'s default meter uses. Each returns a
`(b, a)` pair: the numerator/denominator coefficients of a
second-order IIR filter's transfer function.

**Purpose here:** together, these two filters *are* K-weighting —
`_high_shelf_coefficients` approximates the loudness boost from head
diffraction at high frequencies, `_high_pass_coefficients` (the "RLB"
stage) approximates reduced sensitivity to very low frequencies.

**Called from:** `_k_weight()`, once each, with tracklab's specific
parameters (`fc=1500, gain_db=4.0, q=1/√2` for the shelf; `fc=38,
q=0.5` for the high-pass) — those specific numbers are K-weighting;
the functions themselves are generic biquad design.

**Logic:** `w0 = 2*pi*fc/fs` is the cutoff frequency normalised to the
sample rate — this is what makes the formulas automatically correct at
any sample rate (44.1kHz here) without needing separately published
coefficients per rate, unlike the ITU standard's own published tables,
which list coefficients only at 48kHz. `alpha` and the shelf gain `A`
are cookbook intermediate terms; the `b`/`a` arrays are the direct
cookbook equations for "high shelf" and "high pass" respectively.
Dividing both by `a[0]` normalises the filter so its own `a[0]`
coefficient becomes 1 — the form `scipy.signal.lfilter` expects.

---

### `_k_weight()`

```python
def _k_weight(channel: np.ndarray, fs: int) -> np.ndarray:
    b_shelf, a_shelf = _high_shelf_coefficients(fc=1500.0, gain_db=4.0, q=1 / np.sqrt(2), fs=fs)
    stage1 = lfilter(b_shelf, a_shelf, channel)

    b_hp, a_hp = _high_pass_coefficients(fc=38.0, q=0.5, fs=fs)
    return lfilter(b_hp, a_hp, stage1)
```

**Algorithm / origin:** ITU-R BS.1770's K-weighting filter chain — two
filters applied in series, not in parallel.

**Purpose here:** every LUFS number this project produces starts by
running the signal through this function first.

**Called from:** `integrated_loudness()`, once per channel.

**Logic:** `lfilter(b, a, channel)` applies a digital filter by
evaluating its difference equation across the whole array — this is
the "execution primitive" role described in the module docstring; the
filter *design* above is the from-scratch work, running it is a
`scipy` call in the same spirit as Stage 3's `np.fft.rfft`. `stage1`
(the output of the high-shelf) is fed straight into the high-pass —
series, not parallel, meaning the high-pass sees an already-shelved
signal, not the original.

---

### `integrated_loudness()`

```python
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
```

**Algorithm / origin:** ITU-R BS.1770's mean-square/loudness formula,
plus the two-stage gating algorithm EBU Tech 3341 developed and BS.1770
later incorporated (`CONCEPTS.md` documents the split origin).

**Purpose here:** the single function that turns K-weighted audio into
one LUFS number — every loudness readout tracklab ever shows a user
comes from this function.

**Called from:** `tests/test_loudness.py`; will be called by Stage
6/7's pipeline once it exists.

**Logic:** `weighted` K-weights every channel first. `n_blocks` counts
400ms blocks at 75% overlap (`step_fraction = 0.25`, i.e. each block
starts 100ms after the last). The main loop computes `z[:, j]` — mean
square power per channel, per block — by slicing `weighted` at each
block's sample bounds and squaring-then-averaging. `block_loudness` is
a local helper (a closure over `channel_gain`) converting a mean-square
value into LUFS via the fixed `_LUFS_OFFSET = -0.691` the standard
defines. The absolute gate (`>= -70.0`) filters `block_loudness_values`
to find which blocks survive; their `z` values are averaged
(`z_avg_absolute`) to compute the relative threshold, `-10.0` LU below
that. The second, stricter mask (`doubly_gated`) requires both gates
simultaneously; its surviving blocks are averaged once more
(`z_avg_final`) and converted to the final LUFS value — the same
`block_loudness` helper, called a third time, on three different
inputs across the function.

---

## Stage 5 — `backend/audio/mono_compat.py`

Theory: [`CONCEPTS.md` § Stage 5](CONCEPTS.md#stage-5--mono-compatibility-from-scratch).

### `MonoCompatibilityReport`

```python
@dataclass
class MonoCompatibilityReport:
    band_loss: dict[str, float]  # band name -> fraction of energy lost on mono sum, in [0, 1]
    worst_band: str  # the band losing the most energy
    score: float  # 0-100, 100 = no phase cancellation detected in any band
```

**Purpose here:** the return type of `mono_compatibility()` — three
numbers a future dashboard reads directly: which bands are affected,
which is worst, and one overall number.

---

### `mono_compatibility()`

```python
def mono_compatibility(stereo: np.ndarray, fs: int) -> MonoCompatibilityReport:
    left, right = stereo[0], stereo[1]
    mono = stereo.mean(axis=0)

    freqs, psd_left = welch(left, fs)
    _, psd_right = welch(right, fs)
    _, psd_mono = welch(mono, fs)

    energy_left = band_energy(freqs, psd_left)
    energy_right = band_energy(freqs, psd_right)
    energy_mono = band_energy(freqs, psd_mono)

    source_energy = {name: (energy_left[name] + energy_right[name]) / 2 for name in BAND_RANGES}
    total_energy = sum(source_energy.values())

    _NEGLIGIBLE_ENERGY_FRACTION = 1e-6

    band_loss = {}
    for name in BAND_RANGES:
        if total_energy <= 0 or source_energy[name] / total_energy < _NEGLIGIBLE_ENERGY_FRACTION:
            band_loss[name] = 0.0
            continue
        loss = 1.0 - (energy_mono[name] / source_energy[name])
        band_loss[name] = float(np.clip(loss, 0.0, 1.0))

    worst_band = max(band_loss, key=band_loss.get)

    if total_energy > 0:
        weighted_loss = sum(band_loss[name] * source_energy[name] for name in BAND_RANGES) / total_energy
    else:
        weighted_loss = 0.0
    score = 100.0 * (1.0 - weighted_loss)

    return MonoCompatibilityReport(band_loss=band_loss, worst_band=worst_band, score=float(score))
```

**Algorithm / origin:** not from a published standard — a first-
principles construction, validated against the `sin²(φ/2)`
energy-loss formula derived in `CONCEPTS.md` rather than against an
external library (there isn't one for this specific measurement).

**Purpose here:** the whole of Stage 5 — every mono-compatibility
number tracklab produces comes from this one function.

**Called from:** `tests/test_mono_compat.py`; will be called by Stage
6/7's pipeline once it exists.

**Logic, in order:**

1. `mono = stereo.mean(axis=0)` — derived here, not accepted as an
   argument, guaranteeing it's always the true average of `left` and
   `right` (see `load_audio()`'s docstring for why this invariant
   matters).
2. Three calls to `welch()` produce PSDs for the left channel, right
   channel, and mono sum.
3. Three calls to `band_energy()` aggregate each PSD into the five
   named bands.
4. `source_energy` averages the left and right channel energy per
   band — the baseline "how much energy exists in the source," before
   anything gets summed.
5. The per-band loop is where the two Stage 5 bug fixes live (both
   documented in full in `CONCEPTS.md`): the `_NEGLIGIBLE_ENERGY_FRACTION`
   check skips bands holding less than one part in a million of the
   total energy, since spectral leakage can otherwise produce a
   spurious loss fraction in a band with no real content; `np.clip(...,
   0.0, 1.0)` keeps the reported fraction sane even if floating-point
   noise pushes a ratio very slightly outside `[0, 1]`.
6. `worst_band = max(band_loss, key=band_loss.get)` finds the band name
   with the highest loss fraction — `key=band_loss.get` tells `max` to
   compare by looking up each candidate key's *value* in the dict,
   not the key strings themselves.
7. `score` weights each band's loss by its own share of `total_energy`
   before averaging — not a plain mean across all five bands — so a
   signal whose real content is entirely in one band and gets fully
   cancelled scores near 0, not diluted by four empty bands each
   contributing a "perfect" score (the second Stage 5 bug fix).

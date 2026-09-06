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

---

## Stage 6 — Track intelligence, frequency balance, and the database layer

Theory: [`CONCEPTS.md` § Stage 6](CONCEPTS.md#stage-6--track-intelligence-frequency-balance-and-the-database-layer).

### `detect_bpm()` and `detect_key()` — `backend/audio/intelligence.py`

```python
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_bpm(mono: np.ndarray, fs: int) -> float:
    tempo, _ = librosa.beat.beat_track(y=mono, sr=fs)
    return float(tempo[0])


def detect_key(mono: np.ndarray, fs: int) -> tuple[str, str]:
    chroma = librosa.feature.chroma_cqt(y=mono, sr=fs)
    chroma_mean = chroma.mean(axis=1)

    best_key, best_mode, best_corr = _PITCH_CLASSES[0], "major", -np.inf
    for i in range(12):
        major_corr = np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, i))[0, 1]
        minor_corr = np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, i))[0, 1]

        if major_corr > best_corr:
            best_corr, best_key, best_mode = major_corr, _PITCH_CLASSES[i], "major"
        if minor_corr > best_corr:
            best_corr, best_key, best_mode = minor_corr, _PITCH_CLASSES[i], "minor"

    return best_key, best_mode
```

**Algorithm / origin:** `detect_bpm` — librosa's own beat tracker
(onset-strength periodicity). `detect_key` — chroma extraction via
librosa, then the Krumhansl-Schmuckler key-finding algorithm on top,
using the published Krumhansl-Kessler (1982) profiles (DOI in
`CONCEPTS.md`).

**Purpose here:** every BPM/key value tracklab reports comes from these
two functions — the only place `librosa`'s beat/chroma APIs are called
directly.

**Called from:** `tests/test_intelligence.py`; will be called by Stage
7's pipeline once it exists.

**Logic:** `detect_bpm` calls `librosa.beat.beat_track`, which returns
`tempo` as a NumPy array (confirmed empirically, not from memory —
`array([161.499...])`, not a plain float), so `float(tempo[0])` extracts
the scalar. `detect_key` computes `chroma_cqt` (a `(12, n_frames)`
array, one row per pitch class, chroma index 0 = C) and averages over
time (`axis=1`) into one 12-vector. The loop tries all 12 possible
tonics: `np.roll(_MAJOR_PROFILE, i)` shifts the profile so that
position `j` holds the fit-rating for pitch class `j` when the tonic is
pitch class `i` — `np.roll(profile, i)[j] == profile[(j - i) % 12]`,
exactly the rating for "j semitones above tonic i, evaluated i
semitones early." `np.corrcoef(a, b)[0, 1]` extracts the correlation
coefficient between the chroma vector and each rotated profile; the
loop keeps whichever (tonic, mode) pair correlates best across all 24
candidates.

---

### `frequency_balance()` — `backend/audio/frequency_balance.py`

```python
def frequency_balance(mono: np.ndarray, fs: int) -> dict[str, float]:
    freqs, psd = welch(mono, fs)
    energy = band_energy(freqs, psd)
    total = sum(energy.values())

    if total <= 0:
        return {name: float("-inf") for name in BAND_RANGES}

    return {
        name: 10.0 * np.log10(e / total) if e > 0 else float("-inf")
        for name, e in energy.items()
    }
```

**Algorithm / origin:** not a published algorithm — a direct
application of Stage 3/5's `welch()`/`band_energy()`, converted to a
dB-relative-to-total scale.

**Purpose here:** the numbers behind tracklab's frequency-balance
chart, and — per the 2026-09-05 decision in `CONCEPTS.md` — the same
function used for both a user's own track and any reference track they
choose to compare against.

**Called from:** `tests/test_frequency_balance.py`,
`tests/test_db.py`'s full-pipeline test; will be called by Stage 7's
pipeline once it exists.

**Logic:** `welch()` and `band_energy()` are exactly Stage 3/5's
functions, unmodified. `total = sum(energy.values())` is the track's
whole-signal energy. Each band's result is `10*log10(e / total)` —
converting a power *ratio* to decibels, which is why every value is
≤0dB (a ratio of a part to the whole is always ≤1, and `log10` of a
value ≤1 is ≤0). The `e > 0` and `total <= 0` guards return `-inf`
explicitly for genuinely silent bands/signals rather than letting
`log10(0)` raise or produce a runtime warning.

---

### `Track` and `Features` — `backend/db/models.py`

```python
class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    format: Mapped[str]
    sample_rate: Mapped[int]
    duration: Mapped[float]
    is_lossy: Mapped[bool]
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    features: Mapped["Features"] = relationship(
        back_populates="track", uselist=False, cascade="all, delete-orphan"
    )


class Features(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), unique=True)

    bpm: Mapped[float]
    key: Mapped[str]
    mode: Mapped[str]

    lufs: Mapped[float]

    mono_score: Mapped[float]
    mono_worst_band: Mapped[str]

    freq_sub_db: Mapped[float]
    freq_bass_db: Mapped[float]
    freq_low_mid_db: Mapped[float]
    freq_mid_db: Mapped[float]
    freq_high_db: Mapped[float]

    track: Mapped["Track"] = relationship(back_populates="features")
```

**Algorithm / origin:** SQLAlchemy 2.0's declarative ORM style —
`Mapped[T]` type hints double as both the Python attribute's type and
the SQL column's inferred type.

**Purpose here:** the only place tracklab's data model is defined —
every stored track and its analysis results are instances of these two
classes.

**Called from:** `tests/test_db.py`; will be called by Stage 7's API
layer once it exists.

**Logic:** `Base` is the declarative base every mapped class inherits
from — SQLAlchemy uses it to collect all table definitions into
`Base.metadata` (what `session.py`'s `init_db()` calls
`create_all()` on). Most fields are just `Mapped[float]`/`Mapped[str]`/
`Mapped[bool]` with no explicit column configuration — SQLAlchemy
infers the SQL type from the Python type. `file_hash` is the exception:
`mapped_column(String(64), unique=True, index=True)` — `unique=True`
enforces at the database level that no two tracks share a hash (the
whole point of hashing for a cache), and `index=True` makes looking up
a track by hash fast rather than a full table scan. `track_id: Mapped[int]
= mapped_column(ForeignKey("tracks.id"), unique=True)` is what makes
`features` a one-to-one relationship rather than one-to-many — a track
can have at most one features row. The two `relationship()` calls on
each side don't create columns; they tell the ORM how to navigate
between already-related rows as Python attributes (`track.features`,
implicitly `features.track` via `back_populates`).

---

### `session.py`

```python
DB_PATH = Path(__file__).parent.parent.parent / "tracklab.db"
engine = create_engine(f"sqlite:///{DB_PATH}")

SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(engine)
```

**Algorithm / origin:** SQLAlchemy's engine/session-factory pattern.

**Purpose here:** the two things every other piece of database code
needs — a way to get a session, and a way to make sure the tables
exist.

**Called from:** `tests/test_db.py` uses its own isolated in-memory
engine instead (see below) rather than this module's real-file
`engine`, so tests never touch actual data.

**Logic:** `create_engine(f"sqlite:///{DB_PATH}")` doesn't open a
connection immediately — it's a factory SQLAlchemy draws real
connections from as needed. `sessionmaker(bind=engine)` is the "session
factory" `STAGES.md` asks for: calling `SessionLocal()` produces a new
`Session` bound to this engine, meant for one unit of work
(`CONCEPTS.md` explains why sessions aren't shared). `init_db()` calls
`Base.metadata.create_all(engine)` — every class that inherited from
`Base` in `models.py` registered its table there at import time, so
this one call creates both `tracks` and `features`, and is a safe
no-op if they already exist.

**A note on tests, since it's the same principle as every stage so
far:** `tests/test_db.py` never imports `engine`/`SessionLocal` from
this module at all — it builds its own `create_engine("sqlite:///:memory:")`
per test, via a `pytest.fixture`. Same reasoning as Stage 2's synthetic
audio fixtures: fully isolated, reproducible for a stranger cloning the
repo, and never at risk of touching or corrupting the real
`tracklab.db` file.

---

## Stage 7 — FastAPI application, background pipeline, access gate

Theory: [`CONCEPTS.md` § Stage 7](CONCEPTS.md#stage-7--fastapi-application-background-pipeline-access-gate).

### `analyse_and_store()` — `backend/pipeline.py`

```python
def analyse_and_store(track_id: int, path: Path, session_factory=SessionLocal) -> None:
    with session_factory() as session:
        track = session.get(Track, track_id)
        track.status = "running"
        session.commit()

        try:
            audio = load_audio(path)

            bpm = detect_bpm(audio.mono, audio.sample_rate)
            key, mode = detect_key(audio.mono, audio.sample_rate)
            lufs = integrated_loudness(audio.stereo, audio.sample_rate)
            mono_report = mono_compatibility(audio.stereo, audio.sample_rate)
            balance = frequency_balance(audio.mono, audio.sample_rate)

            track.sample_rate = audio.sample_rate
            track.duration = audio.duration
            track.features = Features(
                bpm=bpm,
                key=key,
                mode=mode,
                lufs=lufs,
                mono_score=mono_report.score,
                mono_worst_band=mono_report.worst_band,
                freq_sub_db=balance["sub"],
                freq_bass_db=balance["bass"],
                freq_low_mid_db=balance["low_mid"],
                freq_mid_db=balance["mid"],
                freq_high_db=balance["high"],
            )
            track.status = "complete"

        except Exception as exc:
            track.status = "failed"
            track.error_message = str(exc)

        session.commit()
```

**Algorithm / origin:** not DSP — the orchestration function first
sketched in conversation before Stage 6 existed, now real: the one
place every audio module (Stages 2–6) is called together.

**Purpose here:** turns "a file on disk" into "a stored, queryable
analysis" — the entire content of what a background task does.

**Called from:** `main.py`'s `upload_track()`, via
`background_tasks.add_task()`; `tests/test_main.py` indirectly, through
the API.

**Logic:** opens its own session (why: `CONCEPTS.md`, Stage 6 — a
Session is one unit of work, and the request's own session is long
closed by the time this runs). Sets `status = "running"` and commits
immediately, so a client polling `GET /tracks/{id}` mid-analysis sees
that, not a stale `"queued"`. The `try` block runs Stages 2–6 in
sequence — `load_audio` first, since every other function needs its
output — and on success, attaches a new `Features` row and flips
`status` to `"complete"`. The `except Exception` catches *any* failure
(a corrupt file, an unsupported format slipping past validation,
anything) and records it as `status = "failed"` with the exception
message, rather than letting the background task crash silently with
no trace of what happened. `session_factory` defaults to the real
`SessionLocal` but is a parameter, not a hardcoded import use — see
`decisions.md`, 2026-09-06, and `main.py` below.

---

### `main.py` — the FastAPI application

```python
session_factory = SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="tracklab", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_db():
    with session_factory() as session:
        yield session


@app.post("/tracks", response_model=UploadResponse, dependencies=[Depends(require_api_key)])
def upload_track(
    file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> UploadResponse:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_hash = hash_file(dest)

    existing = db.query(Track).filter_by(file_hash=file_hash).first()
    if existing is not None:
        dest.unlink()
        return UploadResponse(id=existing.id, status=existing.status)

    track = Track(
        filename=file.filename,
        file_hash=file_hash,
        format=dest.suffix.lower(),
        is_lossy=is_lossy(dest),
        status="queued",
    )
    db.add(track)
    db.commit()

    background_tasks.add_task(analyse_and_store, track.id, dest, session_factory)

    return UploadResponse(id=track.id, status=track.status)


@app.get("/tracks/{track_id}", response_model=TrackResponse, dependencies=[Depends(require_api_key)])
def get_track(track_id: int, db: Session = Depends(get_db)) -> TrackResponse:
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    features_response = None
    if track.status == "complete" and track.features is not None:
        f = track.features
        features_response = FeaturesResponse(
            bpm=f.bpm,
            key=f.key,
            mode=f.mode,
            lufs=f.lufs,
            mono_score=f.mono_score,
            mono_worst_band=f.mono_worst_band,
            frequency_balance=FrequencyBalanceResponse(
                sub=f.freq_sub_db,
                bass=f.freq_bass_db,
                low_mid=f.freq_low_mid_db,
                mid=f.freq_mid_db,
                high=f.freq_high_db,
            ),
        )

    return TrackResponse(
        id=track.id,
        filename=track.filename,
        status=track.status,
        error=track.error_message,
        features=features_response,
    )
```

**Algorithm / origin:** FastAPI's own patterns throughout — dependency
injection (`Depends`), lifespan context managers, `BackgroundTasks`.

**Purpose here:** the only HTTP-facing code in the whole project —
everything below it (Stages 2–6) is pure Python with no knowledge that
HTTP exists.

**Called from:** run directly by `uvicorn backend.main:app`; exercised
in tests via `TestClient(main.app)`.

**Logic:**

- `session_factory = SessionLocal` — a plain, reassignable name, not
  used directly inline elsewhere, precisely so tests can replace it
  (`decisions.md`, 2026-09-06).
- `lifespan` replaces the older, now-deprecated `@app.on_event("startup")`
  — an `async def` generator function: everything before `yield` runs
  at startup (creating tables, ensuring the upload directory exists),
  everything after would run at shutdown (nothing needed here).
- `require_api_key` — a dependency with no return value, used purely
  for its side effect of raising `HTTPException` when the check fails;
  attached to both routes via `dependencies=[Depends(require_api_key)]`
  rather than as a parameter each handler has to remember to check.
- `get_db` is itself a *generator* (`yield`, not `return`) — FastAPI
  recognises this pattern specifically to guarantee the session's
  `with` block exits (closing it) once the request finishes, success
  or failure, without the handler needing its own `try`/`finally`.
- `upload_track`: writes the upload to disk first (needed before it
  can even be hashed), hashes it, and checks for an existing `Track`
  with that hash *before* doing anything else — the cache-hit path
  deletes the just-written duplicate and returns immediately, doing no
  further work. Only on a genuine new file does it create a `Track`
  row (status `"queued"`, no `sample_rate`/`duration` yet) and queue
  `analyse_and_store` — note the explicit `session_factory` passed as
  its third argument, the same reassignable name `get_db` reads,
  keeping both paths in sync under one override.
- `get_track`: builds the nested `FeaturesResponse`/`FrequencyBalanceResponse`
  only when `status == "complete"` and a `Features` row actually
  exists — every other status returns `features: null`, which the
  response model's `features: FeaturesResponse | None = None` default
  makes valid rather than a validation error.

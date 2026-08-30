# tracklab — Concepts Companion

This document exists for one reason: the project's own ground rule is
that every line of code in this repo must be defensible in an
interview, not just working. `learning.md` in the vault is a terse,
one-line-per-concept log written during sessions. This document is the
opposite of terse — it is the textbook chapter that log is shorthand
for, organised by build stage rather than by session, and it grows one
section at a time as each stage is completed. It does not get written
ahead of the code; Stage 3 gets a section once Stage 3 exists, not
before.

Regenerate the PDF after editing this file with:

```
cd docs
/usr/bin/python3 -m venv .venv        # first time only -- see note below
.venv/bin/pip install -r requirements-docs.txt
.venv/bin/python build_pdf.py
```

**Use `/usr/bin/python3` (Apple's bundled Python), not the Homebrew
one, to create this venv.** Discovered 2026-08-30: the Homebrew
`python@3.13` build on this machine is linked against a `libexpat`
symbol newer than what's actually available at runtime
(`/usr/lib/libexpat.1.dylib`), so anything importing `xml.parsers.expat`
— including `pip`'s own vendored `distlib`, needed for any fresh
install — fails with a `dlopen` symbol error. This is a real,
standalone defect on this machine (reproduces in a plain terminal, not
sandbox-specific), not a bug in this project. The proper fix is
`brew reinstall expat` (or `python@3.13`) to relink correctly; until
then, `/usr/bin/python3` has a working `expat` and works fine as the
base interpreter for this disposable tooling venv.

---

## Stage 1 — Repo skeleton and environment

### What we built

A directory skeleton, a virtual environment at `backend/.venv`, a
pinned `requirements.txt`, and a `.gitignore`. Nothing computational yet
— this stage is entirely about making the rest of the project
reproducible.

### Virtual environments, properly

Every Python installation has one global `site-packages` directory
where `pip install` puts things by default. If two projects on the same
machine need different, incompatible versions of the same library —
say `numpy==1.26` for one and `numpy==2.5` for another — installing
both globally is impossible; whichever was installed last wins, and the
other project silently breaks.

A virtual environment fixes this by giving each project its own
private copy of the parts of Python that matter for package
resolution. `backend/.venv/bin/python` is a distinct executable from
whatever `python3` resolves to on your system `PATH`, and it has its
own `site-packages` directory that only sees what you `pip install`
inside that venv. When you run `backend/.venv/bin/python`, or activate
the venv so plain `python` resolves to it, import resolution
(`sys.path`) is redirected to search that private directory first. Two
projects can now each have their own `numpy`, and neither knows the
other exists.

**Concretely, the mechanism is `sys.path`.** Every Python interpreter
resolves `import numpy` by searching a list of directories in order,
stored in `sys.path`. A venv's interpreter has that list rewritten to
put its own `site-packages` first — nothing more exotic than that.
Compare the two directly:

```
$ /opt/homebrew/opt/python@3.13/bin/python3.13 -c "import sys; print(sys.path[-1])"
/opt/homebrew/lib/python3.13/site-packages          # the plain Homebrew install

$ backend/.venv/bin/python -c "import sys; print(sys.path[-1])"
/Users/junaydsmac/projects/tracklab/backend/.venv/lib/python3.13/site-packages   # this project's own copy
```

(Using the explicit Homebrew path rather than plain `python3` here
deliberately — on this machine, `python3` on `PATH` currently resolves
*into* `backend/.venv` itself, which is exactly the kind of ambiguity
worth being aware of: which interpreter a bare command name resolves
to depends on shell state, not just what's installed.)

This is exactly the mechanism PEP 405 — the actual proposal that added
`venv` to the standard library in Python 3.3 — describes: prior to it,
this isolation existed only via a third-party tool (`virtualenv`)
reimplementing the same `sys.path` trick externally; PEP 405 folded it
into the interpreter itself so every Python installation could do it
natively, "lower[ing] maintenance, rais[ing] reliability" (the PEP's
own stated motivation) compared to relying on an external package.

**Where it appears:** `backend/.venv`, created in Stage 1; every
`backend/.venv/bin/<tool>` invocation since (`pytest`, `pip`, the
interpreter itself).

### Dependency pinning and reproducibility

`requirements.txt` lists an exact version for every installed package,
generated with `pip freeze`, rather than a loose constraint like
`librosa>=0.10`. The difference matters the moment this repo is cloned
onto a different machine, or even the same machine six months later:

- A loose range resolves to *whatever the newest matching version is
  at install time*. If a library ships a breaking API change between
  now and then, `pip install -r requirements.txt` on the loose range
  silently gives you different, possibly incompatible code from what
  you tested against.
- An exact pin (`==`) resolves to the same bytes every time, so
  "works on my machine" becomes "works, full stop" for anyone who
  clones the repo — including future you, revisiting this for an
  interview after months away from it.

**A real example of exactly this happening**, not a hypothetical:
NumPy 2.0 (2024) removed over a hundred names from its top-level
namespace, including `np.NaN` and `np.Inf` — anything using those two
extremely common aliases breaks outright on upgrade, not with a
warning but with an `AttributeError`. NumPy's own migration guide
documents this explicitly, alongside quieter but equally real changes
like floating-point type-promotion rules changing (`np.float32(3) + 3.`
now returns `float32`, where it used to silently upgrade to `float64`)
— a change that alters numerical *results*, not just what breaks
outright. `requirements.txt` pins `numpy==2.5.2` precisely so this
project never silently rides that upgrade unannounced.

**What the version number itself promises** is defined by Semantic
Versioning (`MAJOR.MINOR.PATCH`): increment `MAJOR` for incompatible
API changes, `MINOR` for backward-compatible additions, `PATCH` for
backward-compatible fixes. NumPy's jump from `1.26` to `2.0` is the
`MAJOR` bump signalling exactly the kind of break above — the version
number itself was the advance warning, for anyone unpinned enough to
receive it. Semantic versioning is a convention libraries *choose* to
follow, not something Python enforces, so a pin is the only way to be
certain rather than trusting every maintainer to apply it correctly.

The trade-off is that pinned versions need occasional deliberate
upgrading (a pin never fixes itself), which is a reasonable price for
reproducibility in a project meant to be handed to a stranger (Stage
14's exit criterion).

**Where it appears:** `requirements.txt`.

### Why `.gitignore` is structured the way it is

Four different reasons for exclusion live in that one file, and it's
worth being able to name which is which:

- **Secrets** (`.env`) — must never enter git history, because history
  is permanent even if the file is later deleted from HEAD. Concretely:
  if `.env` were committed once, then removed with `git rm .env` in a
  later commit, the secret is *not* gone — `git show
  <that-earlier-commit>:.env`, or simply `git log -p -- .env`, recovers
  it exactly, forever, for anyone who ever clones the repo. This is
  precisely how real API-key and credential leaks happen in public
  repositories: not from a secret being visible *now*, but from it
  having been committed *once*, at any point in history. `.gitignore`
  only prevents git from staging the file in the first place — it does
  nothing to a secret that's already inside a commit, which is why
  prevention (never committing it) is the only real fix, not cleanup
  after the fact.
- **Machine-specific, regenerable state** (`backend/.venv/`,
  `__pycache__/`, `.pytest_cache/`) — reconstructable from
  `requirements.txt` in seconds; committing it would bloat the repo
  with binary files that are actively wrong on a different OS or Python
  patch version.
- **Large user data that isn't the product** (`data/`, `*.db`) — the
  spec is explicit that audio files are never stored in the database
  and never committed; only the hash and extracted features are meant
  to persist, and those live in SQLite, itself excluded here because a
  database file is regenerated state, not source.
- **Trained artefacts that are outputs, not inputs** (`backend/ml/models/*.pkl`)
  — the model is a function of the training script plus the FMA
  dataset; committing the binary would be committing a build output,
  the same category error as committing a `.pyc` file.

### References

- [`venv` — Python documentation](https://docs.python.org/3/library/venv.html)
- [PEP 405 — Python Virtual Environments](https://peps.python.org/pep-0405/) — the original proposal that added `venv` to the standard library, with its stated motivation
- [pip: Repeatable installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/)
- [Semantic Versioning 2.0.0](https://semver.org/) — what a `MAJOR.MINOR.PATCH` version number is actually promising
- [NumPy 2.0 migration guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html) — a real, documented breaking change (`np.NaN`/`np.Inf` removed, type-promotion rules changed)
- [`gitignore` — Git documentation](https://git-scm.com/docs/gitignore)

---

## Stage 2 — Audio loading and format handling

### What we built

`backend/audio/loader.py`: `hash_file()` for SHA-256 hashing,
`is_lossy()` for extension-based format classification, and
`load_audio()`, which resamples any supported file to 44.1kHz and
returns a `LoadedAudio` dataclass holding mono and stereo arrays,
sample rate, duration, the lossy flag, the hash, and the format.
Covered by 16 pytest tests in `tests/test_loader.py` against
synthetically generated fixtures.

### Cryptographic hashing: SHA-256

A cryptographic hash function takes an input of any length and
produces a fixed-size output (256 bits, for SHA-256) with three
properties that matter here:

1. **Deterministic** — the same input always produces the same output,
   which is the entire reason this project can use a hash as a cache
   key: re-uploading an identical file must produce an identical hash
   to hit the cache.
2. **The avalanche effect** — changing a single byte anywhere in the
   input changes roughly half the output bits, unpredictably. Two
   different recordings of the same track (even a re-export with one
   sample different) hash to completely unrelated values, so there's
   no risk of "close" files being mistaken for the same one.
3. **Practically collision-resistant** — no two different inputs are
   known to produce the same 256-bit output, and finding one by brute
   force would take far longer than the age of the universe with
   current computing power. For a personal catalogue of a few thousand
   tracks, the odds of an accidental collision are not a practical
   concern.

Mechanically, SHA-256 is built on the **Merkle–Damgård construction**:
the message is padded (a `1` bit, then zeros, then a 64-bit field
encoding the original length) until it's a multiple of 512 bits, split
into 512-bit blocks, and processed block by block through a compression
function that folds each block into a running internal state. The
final state, after the last block, is the digest.

This is *why* `hash_file()` reading the file in chunks works cleanly
rather than being a workaround: the algorithm itself is defined to
consume its input one fixed-size block at a time and update a small
running state, so handing it 1MB chunks via `hashlib`'s incremental
`.update()` API is the natural way to use it, not a special
accommodation. The whole file is never needed in memory at once because
the algorithm was never going to look at more than one block at a time
anyway.

**Where it appears:** `backend/audio/loader.py`, `hash_file()`.

### Lossless vs lossy compression

WAV, FLAC, and AIFF are **lossless** — every sample of the original
signal is recoverable exactly (FLAC compresses the file size but not
the information; WAV/AIFF don't even compress). MP3, AAC, and M4A are
**lossy**: the encoder uses a *psychoacoustic model* — an approximation
of what the human ear can and cannot perceive — to decide which parts
of the signal to discard permanently.

The specific effect being exploited is **auditory masking**: a loud
sound raises the threshold at which a nearby, quieter sound becomes
audible at all. The textbook example — a cat scratching a post is
audible alone at around 10dB SPL in a quiet room, but needs to reach
roughly 26dB SPL to be heard at all once a vacuum cleaner is running
nearby, because the vacuum's noise has raised the *masking threshold*
in that frequency region. An MP3 encoder runs this calculation
continuously across the spectrum: anything predicted to fall below the
masking threshold created by louder nearby content gets encoded with
sharply reduced precision, or dropped, since a listener wasn't going to
hear it anyway. Content above roughly 16–20kHz, where masking aside
most listeners' hearing is already weak, gets thrown away by the same
logic. This is a genuine perceptual model, not an arbitrary cutoff —
which is exactly why it can be wrong in edge cases (a transient that a
generic masking model doesn't anticipate can audibly suffer), the
well-known failure mode of lossy codecs at low bitrates.

This is why a lossy file needs to be flagged rather than analysed as
if it were the original: a hard rolloff at 16–20kHz in an MP3's
spectrum is the codec doing its job, not a mixing decision. Reading it
as a frequency-balance problem in the source mix would be a category
error.

**Where it appears:** `backend/audio/loader.py`, `is_lossy()`,
`LOSSLESS_FORMATS` / `LOSSY_FORMATS`.

### The Nyquist–Shannon sampling theorem, and what resampling actually does

This is worth stating precisely, since it's the mathematical bedrock
under every `sr=44100` in the codebase. **A signal sampled at rate
`fs` can be perfectly reconstructed from its samples if and only if it
contains no frequency content at or above `fs / 2`** (the *Nyquist
frequency*) — the theorem is attributed jointly to Harry Nyquist's 1928
analysis of telegraph signalling rate and Claude Shannon's 1949
formalisation of it for general communication, though Wikipedia's
account (cited below) notes it was also derived independently by E.T.
Whittaker in 1915 and Vladimir Kotelnikov in 1933, one of those results
several people reached separately before it had one settled name.
Sample a signal that *does* have higher-frequency content, and those
frequencies don't just vanish — they fold back and appear as false,
lower frequencies in the sampled signal.

**Concretely**: at `fs = 44100`, the Nyquist frequency is `22050Hz`. A
genuine 30kHz tone, sampled at 44.1kHz without first being filtered
out, doesn't disappear — it reappears as a false tone at
`44100 − 30000 = 14100Hz`, sitting well inside the audible range and
indistinguishable from a real 14.1kHz signal in the sampled data. That's
aliasing, and it's not fixable after the fact; the information needed
to tell the alias from a real low frequency is gone the moment both
would produce identical samples.

This is why `load_audio()` resampling to 44.1kHz is not simply
"changing a number that says how many samples per second":

- **Downsampling** (source rate higher than 44.1kHz) requires a
  low-pass filter *before* discarding samples, removing everything at
  or above the new Nyquist frequency (22.05kHz), or the discarded
  detail aliases into the result as audible garbage.
- **Upsampling** (source rate lower than 44.1kHz) requires interpolating
  new sample values between the existing ones — in the ideal case, this
  means reconstructing the original continuous-time bandlimited signal
  via a sinc-function interpolation filter, then re-sampling it at the
  new rate.

`librosa.load(path, sr=44100)` does both of these via an internal
resampler, chosen by the `res_type` parameter. Confirmed against
librosa 0.11.0's own documentation: the default is `soxr_hq` — a
high-quality resampler from the `soxr` library using polyphase
filtering — replacing the older `kaiser_best`/`resampy` default from
earlier versions. One honest gap: this repo pins `librosa==1.0.0`, a
later release than the 0.11.0 documentation I checked. The default is
very unlikely to have changed given `soxr_hq` is the currently
recommended setting, but I did not independently re-confirm it against
1.0.0 specifically — worth saying "recent versions default to
`soxr_hq`" rather than asserting it as directly checked fact about
*this exact* installed version, if asked.

**Where it appears:** `backend/audio/loader.py`, `TARGET_SAMPLE_RATE`,
`load_audio()`.

### Why the MP3 and WAV of the same track don't have identical durations

We measured this directly: `PS Cmin 160.mp3` loaded at 204.07s,
`PS Cmin 160 24.wav` (the lossless mix of the same track) at 204.02s —
a gap of about 50 milliseconds. This is not a bug in the loader; it's a
structural property of how MP3 encoding works.

MPEG-1 Layer III (MP3) encodes audio in fixed-size **frames** of 1152
samples per channel, using the **Modified Discrete Cosine Transform**
(MDCT) — a block-based transform that, to avoid audible artefacts at
block boundaries, overlaps each block with its neighbours (`overlap-add`
reconstruction). That overlap requires the encoder to have samples
*before* the nominal start of the audio and *after* its nominal end —
samples that don't exist in the source, so encoders like LAME insert
silent **priming samples** before the first real frame and **padding
samples** after the last one to complete it. Published figures for LAME
put this at roughly 1105 samples of priming plus up to 1152 samples of
end padding, at whatever the sample rate is. At 44100Hz, that's
`(1105 + 1152) / 44100 ≈ 51ms` — matching what we measured to within a
couple of milliseconds. That agreement is a good sanity check that
what we observed is exactly this known effect, not something else going
wrong in the loader.

**Where it appears:** observed by comparing `load_audio()`'s output for
the two files; not something the code corrects for, since correcting
it is a mastering/export concern, not an analysis one.

### Structuring data: `@dataclass` vs a plain dict

`LoadedAudio` is a `@dataclass` with typed fields (`mono: np.ndarray`,
`sample_rate: int`, and so on) rather than a dict. The decorator
generates `__init__`, `__repr__`, and `__eq__` from the field
declarations, so construction, printing, and comparison all come for
free from a short declarative list rather than boilerplate — exactly
the motivation stated in PEP 557 (the proposal that added `dataclasses`
to the standard library in Python 3.7): a way to write "normal Python
classes" that get boilerplate methods generated from type-annotated
fields, without inheriting from a base class or relying on a metaclass
to do it. The practical benefit over a dict: `audio.mono` is checked by
tooling at development time, so a typo (`audio.mnoo`) is caught before
running the code; `audio['mnoo']` on a dict is a `KeyError` that only
surfaces at runtime, possibly deep into a pipeline.

Worth flagging now, ahead of Stage 6: FastAPI's `Pydantic` models look
similar — typed fields on a class — but go further by *validating*
values at runtime (rejecting a string where an int was declared, for
instance). A plain `@dataclass` does not validate anything; the type
hints are documentation and tooling support only, not enforcement. The
distinction is worth being precise about, since conflating the two is
an easy mistake to make out loud in an interview.

**Where it appears:** `backend/audio/loader.py`, `LoadedAudio`.

### Testing methodology: fixtures, parametrization, synthetic data

`tests/test_loader.py` uses three pytest features worth naming
explicitly:

- **Fixtures** — a function decorated with `@pytest.fixture` that
  builds something a test needs and hands it over as an argument;
  pytest matches fixtures to tests by parameter name, not by explicit
  wiring. `tmp_path` is a built-in fixture giving each test its own
  throwaway directory, cleaned up automatically after the test runs.
- **Parametrization** — `@pytest.mark.parametrize` runs the same test
  body once per row of a table of inputs and expected outputs
  (`test_is_lossy_by_extension`), rather than writing near-identical
  test functions by hand for each extension.
- **Synthetic, generated fixtures over real files** — `stereo_wav` and
  `mono_wav` generate sine waves at test time with `numpy` and
  `soundfile`, rather than depending on personal audio in
  `data/samples/`. This keeps the suite deterministic and reproducible
  for anyone who clones the repo without that personal data — directly
  serving Stage 14's exit criterion that a stranger can run the test
  suite. The `stereo_wav` fixture deliberately uses two *different*
  tones per channel (440Hz and 880Hz); if both channels held the same
  tone, a broken mono-downmix implementation could still pass the test
  by accident.

One honest limitation: only WAV is exercised by the automated suite.
Real lossy-codec decoding (actual MP3/M4A quirks, like the encoder
padding just discussed) is checked manually against `data/samples/`,
not automatically — generating synthetic MP3s at test time would need
an embedded encoder, which wasn't judged worth the added complexity for
this stage.

**Where it appears:** `tests/test_loader.py`.

### References

- [`hashlib` — Python documentation](https://docs.python.org/3/library/hashlib.html) — incremental `update()`, the API behind streamed hashing
- [FIPS 180-4: Secure Hash Standard](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf) — the specification defining SHA-256 and the Merkle–Damgård construction
- [Auditory masking — Wikipedia](https://en.wikipedia.org/wiki/Auditory_masking) — the perceptual effect lossy codecs exploit, with the cat/vacuum-cleaner masking-threshold example
- [Nyquist–Shannon sampling theorem — Wikipedia](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem)
- [`librosa.load` documentation (0.11.0)](https://librosa.org/doc/0.11.0/generated/librosa.load.html) — confirms `res_type='soxr_hq'` as the default resampler
- [`python-soxr`](https://github.com/dofuuz/python-soxr) — the resampling library librosa's default delegates to
- [LAME Technical FAQ](https://lame.sourceforge.io/tech-FAQ.txt) — encoder/decoder delay and padding, the mechanism behind the MP3/WAV duration mismatch
- [PEP 557 — Data Classes](https://peps.python.org/pep-0557/) — the proposal behind `@dataclass`, and its stated motivation
- [`dataclasses` — Python documentation](https://docs.python.org/3/library/dataclasses.html)
- [Pydantic documentation](https://docs.pydantic.dev/latest/) — the validating counterpart to a plain dataclass, relevant from Stage 6 onward
- [pytest: How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [pytest: Temporary directories and files (`tmp_path`)](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [pytest: `parametrize`](https://docs.pytest.org/en/stable/how-to/parametrize.html)

---

## Stage 3 — Welch spectral estimation, from scratch

**Note (2026-08-22):** the stage numbering changed after a project
rescope — genre/mood classification and the Claude feedback layer were
cut from Tier 1, and the remaining work was renumbered from fourteen
stages to eight. See `docs/STAGES.md` and the vault's `decisions.md`
for the reasoning. The Stage 1/2 sections above are unaffected.

### What we built

`backend/audio/spectral.py`: `_periodic_hann()` for window generation,
`_windowed_periodogram()` for one segment's contribution, and `welch()`
tying them together — segmenting, windowing, and averaging. Covered by
9 pytest tests in `tests/test_spectral.py`, validating against
`scipy.signal.welch` on synthetic sine waves and white noise to
`rtol=1e-9` — effectively floating-point-limit agreement, not merely
"close."

### Why a single periodogram isn't good enough

A periodogram — the squared magnitude of a signal's FFT — is an
estimate of its power spectral density, but a statistically poor one:
its variance doesn't shrink as you feed it more data of the same kind.
A periodogram computed over 10 seconds of noise looks just as jagged
and unreliable as one computed over 1 second — longer input buys finer
frequency resolution, not a less noisy estimate. Welch's method exists
specifically to fix this.

### Welch's method: segment, window, average

Split the signal into (usually overlapping) segments, compute a
periodogram for each, and average them. Averaging several independent
noisy estimates reduces variance — the same principle behind averaging
repeated measurements in any experimental science. The cost is
resolution: each segment is shorter than the full signal, and frequency
bin spacing is `fs / segment_length`, so shorter segments mean coarser
frequency detail. That trade-off — variance down, resolution down — is
tuned entirely by the choice of segment length.

This is precisely the method Peter Welch introduced in his 1967 paper,
*"The Use of Fast Fourier Transform for the Estimation of Power
Spectra: A Method Based on Time Averaging Over Short, Modified
Periodograms"* (cited below) — the title states the whole idea in one
sentence, decades before it became a one-line `scipy` call. Welch's own
motivation, per the paper's abstract, was as much practical as
statistical: sectioning a long record into short segments needs far
less computer memory than one huge FFT over the whole thing, which
mattered enormously on 1960s hardware and still shapes why the method
looks the way it does — segment, transform, average, discard, repeat —
rather than one large transform with a smoothing step applied
afterward.

### Windowing and spectral leakage

A segment is a snippet chopped out of a longer signal, not a naturally
periodic waveform. The FFT implicitly treats whatever it's given as one
period of an infinitely repeating signal; if a segment's two raw ends
don't meet up smoothly — they essentially never do — that discontinuity
smears energy across frequency bins that shouldn't have any, an effect
called spectral leakage. A window function tapers each segment's edges
toward zero before the FFT, hiding the mismatched endpoints, at the
cost of slightly widening every frequency bin. No window eliminates
leakage; each just trades one kind of inaccuracy for another.

### The bug: symmetric vs periodic windows

Worth documenting in full, since this was a real bug caught by testing,
not a hypothetical one. `np.hanning(N)` generates the *symmetric* Hann
window — it touches exactly zero at both its first and last sample,
the natural definition if you picture the window as a standalone shape.
For FFT-based spectral analysis specifically, the *periodic* (DFT-even)
variant is the correct one instead: computed as if there were one extra
sample past the end, at whatever point would make repeated copies of
the window tile together smoothly, with that extra sample then
discarded. The two differ by a genuinely tiny amount — `sum(window**2)`
differs by about 0.02% for a 4096-sample window — which is exactly the
kind of thing that shows up as a normalisation-scale error, not a
shape error, in a PSD estimate.

That's precisely what happened: the first full comparison between the
from-scratch `welch()` and `scipy.signal.welch()` showed a consistent
`~2×10⁻⁴` relative error — small, but far above the `~10⁻⁷`
floating-point noise already established as the honest baseline from
Stage 2's single-segment check. A *consistent* discrepancy of a
specific, small size — the same at every frequency, not random — is
the fingerprint of a scale or normalisation mismatch, not a logic
error, and worth recognising as such before ever opening the code to
look for a bug. Confirming `np.hanning()` against
`scipy.signal.get_window('hann', N)` directly showed they were
different windows; replacing it with the periodic formula
(`0.5 - 0.5*cos(2*pi*n/N)` — note dividing by `N`, not `N-1`) brought
agreement to `~10⁻¹⁵`, true machine precision.

### PSD scaling and the one-sided spectrum

Two further deliberate scaling choices inside `_windowed_periodogram`:

- Dividing by `fs * sum(window**2)`: dividing by `fs` converts "power
  per sample" into "power per Hz" — a density, comparable across
  different sample rates or segment lengths. Dividing by the window's
  own summed squared value corrects for the energy the window itself
  removed by tapering samples toward zero.
- Doubling every bin except DC and Nyquist: `np.fft.rfft` returns only
  the non-negative-frequency half of a real signal's (necessarily
  symmetric) spectrum, discarding the other half's energy. Doubling
  restores it, since a real signal's total power splits evenly between
  the redundant negative and positive frequency halves.

### Why `welch()` doesn't detrend

`scipy.signal.welch`'s default subtracts each segment's mean before
computing its periodogram (`detrend='constant'`) — sensible for
arbitrary sensor data that might carry a DC offset, irrelevant for
audio, which doesn't. The validation tests pass `detrend=False` to
scipy explicitly, so the comparison honestly checks the same algorithm
on both sides rather than comparing two deliberately different things
and reporting the gap as a bug.

### References

- Welch, P.D. (1967). [The Use of Fast Fourier Transform for the Estimation of Power Spectra: A Method Based on Time Averaging Over Short, Modified Periodograms](https://doi.org/10.1109/TAU.1967.1161901). *IEEE Transactions on Audio and Electroacoustics*, 15(2), 70–73. — the original paper introducing the method this stage implements; DOI resolves to IEEE Xplore
- [`scipy.signal.welch` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html) — confirms the periodic Hann default and `detrend='constant'` default
- [`scipy.signal.get_window` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.get_window.html) — the `fftbins` parameter and periodic vs symmetric windows
- [Spectral leakage — Wikipedia](https://en.wikipedia.org/wiki/Spectral_leakage)
- [Window function — Wikipedia](https://en.wikipedia.org/wiki/Window_function) — covers the symmetric vs DFT-even Hann variants directly

---

## Stage 4 — LUFS loudness, from scratch (ITU-R BS.1770)

### What we built

`backend/audio/loudness.py`: `_high_shelf_coefficients()` and
`_high_pass_coefficients()` generate the two K-weighting biquad
filters; `_k_weight()` chains them; `integrated_loudness()` implements
the block-based mean-square measurement and two-stage gating. Covered
by 7 pytest tests in `tests/test_loudness.py`, validating against
`pyloudnorm` (and, where ffmpeg is available, ffmpeg's `ebur128`
filter) to within 0.1 LU on sine waves, white noise, and three named
edge cases: near-silence, heavy limiting, and a quiet passage.
Real-track agreement was also checked manually against both references
on `data/samples/` — exact match against `pyloudnorm`, within ffmpeg's
displayed precision against `ebur128` — recorded in `BUILD_LOG.md`
rather than the automated suite, for the same reproducibility reason as
Stage 2 and Stage 3.

### Why loudness isn't RMS or peak

Peak level tells you the single loudest sample, nothing about how loud
a track *sounds* over time — a track that's mostly quiet with one brief
spike has a high peak but doesn't feel loud. RMS (root-mean-square)
averages energy over time, closer to perceived loudness, but treats all
frequencies as equally important, which human hearing doesn't: two
tracks with identical RMS can sound very differently loud if their
energy sits in different parts of the spectrum. LUFS starts from RMS's
idea of a time-averaged measurement, but applies frequency weighting
first (K-weighting) and adds gating to exclude the fact that a
"typical" measurement of an inconsistent signal.

### K-weighting: two biquad filters, RBJ cookbook formulas

K-weighting applies two IIR filters in series, both generated from the
public "RBJ Audio EQ Cookbook" formulas (the same reference
`pyloudnorm` itself uses by default — see `decisions.md`,
2026-08-28):

- **A high-shelf filter** (+4dB above ~1500Hz) approximating the boost
  in perceived level from head diffraction at high frequencies — sound
  above roughly 1.5kHz reaches the eardrum somewhat amplified by the
  head and ear's own shape, and K-weighting compensates by weighting
  those frequencies up before measuring.
- **A high-pass filter** (the "RLB" stage, cutting below ~38Hz)
  approximating reduced human sensitivity to very low frequencies —
  sub-bass content contributes less to perceived loudness than its raw
  energy would suggest, so it's weighted down.

Deriving the filter *coefficients* from these formulas, and building
the two-stage gating algorithm around them, is the from-scratch work.
Applying an already-derived biquad via `scipy.signal.lfilter` is an
execution primitive — the same role `np.fft.rfft` played in Stage 3's
Welch implementation, not "the algorithm" itself.

### The two-stage gating, and why each stage exists

Worth being precise about where each piece of this algorithm actually
comes from, since it's a composite of two related but distinct
standards bodies' work: ITU-R BS.1770 defines the K-weighting filter
chain and the basic loudness formula, but the *two-stage gating*
specifically was developed and refined by the EBU (European
Broadcasting Union) in Tech 3341 — the broadcast-industry specification
behind "EBU R128" loudness normalisation — and only folded back into
later revisions of BS.1770 itself. This implementation follows the
gating algorithm as commonly described and as `pyloudnorm` implements
it, which traces to that EBU refinement rather than being original to
BS.1770's first version.

After K-weighting, the signal is split into 400ms blocks with 75%
overlap, and the mean-square power of each block is measured. Two
gates are then applied before averaging:

- **Absolute gate, −70 LUFS**: drops any block quieter than this fixed
  threshold outright — near-silence (a gap between songs, a quiet
  intro) shouldn't count toward "how loud does this track sound,"
  since a listener doesn't perceive silence as part of a track's
  loudness at all.
- **Relative gate, −10 LU below the absolute-gated mean**: drops blocks
  that are quiet *relative to the track's own average*, computed
  fresh after the first gate. A loud track with one deliberately sparse
  breakdown shouldn't measure as quieter overall just because of that
  one section — this gate protects the measurement from being pulled
  down by material that's quiet by artistic choice, not by being
  literally silent.

The final loudness is the mean-square power of only the blocks that
survive both gates, converted to LUFS via a fixed calibration constant
(`−0.691`) that the ITU-R standard specifies directly as part of what
"LUFS" is defined to mean — not something derived from first
principles inside this codebase.

### Checking the exit criteria were achievable before writing any code

Before implementing anything, `pyloudnorm` and ffmpeg's `ebur128` were
run against the same real track to check they actually agreed with
each other to within 0.1 LU — if they hadn't, the stated exit criteria
("agree with both to within 0.1 LU") would have been unsatisfiable
regardless of implementation quality, no matter how correct the code
was. They agreed closely (−14.4192 vs −14.4 LUFS), which confirmed 0.1
LU was a real, achievable target rather than an arbitrary number
written down in advance of doing the work.

### A test that failed for the right reason

`test_absolute_gate_ignores_leading_silence` initially compared a
"10s near-silence + 5s tone" signal's measured loudness against a
"5s tone alone" measurement, expecting them to match within 0.1 LU.
They didn't — off by about 0.13 LU. Rather than loosen the tolerance,
the first check was whether `pyloudnorm` agreed with *my*
implementation on the exact same edge-case signal: it did, exactly. The
test's assumption was the bug, not the code — one block straddles the
silence/tone boundary and isn't cleanly gated out, and the filter has a
brief transient right at that discontinuity, both correct properties
of the algorithm on an artificial instant-silence-to-full-volume jump
that real audio never actually does. The fix was rewriting the test to
compare against the reference on the *same* signal, not against an
unrelated one. The general lesson, same shape as Stage 3's window bug:
when an automated check disagrees with an independent reference, check
which one is wrong before assuming it's the implementation.

### References

- [RBJ Audio EQ Cookbook](http://shepazu.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) — the public biquad filter formulas used for both K-weighting stages
- [ITU-R BS.1770 recommendation page](https://www.itu.int/rec/R-REC-BS.1770) — current published version is BS.1770-5 (2023); this implementation targets what's commonly described as BS.1770-4's algorithm, matching `pyloudnorm`'s own stated target — the difference between the two hasn't been checked
- [EBU Tech 3341](https://tech.ebu.ch/docs/tech/tech3341.pdf) — the EBU specification (behind "EBU R128" loudness normalisation) that developed the two-stage gating algorithm, later folded back into later BS.1770 revisions
- [`pyloudnorm` on PyPI](https://pypi.org/project/pyloudnorm/)
- [ffmpeg `ebur128` filter documentation](https://ffmpeg.org/ffmpeg-filters.html#ebur128)

---

## Stage 5 — Mono compatibility, from scratch

### What we built

`backend/audio/mono_compat.py`: `mono_compatibility(stereo, fs)`,
comparing each frequency band's energy in the source stereo channels
against its energy after summing to mono, using Stage 3's `welch()`
and a small addition to `spectral.py` — `BAND_RANGES` (the named
sub/bass/low-mid/mid/high bands `spec.md` already defines) and
`band_energy()`, which integrates a PSD estimate into total power per
band. Added to `spectral.py` rather than duplicated here, since Stage
6's frequency-balance feature will need the exact same band vocabulary.
Covered by 8 pytest tests in `tests/test_mono_compat.py`, validated
against a formula derived from first principles (below), not an
external library — there isn't one for this specific question.

### What phase cancellation actually is

Two identical waveforms, summed, reinforce each other — this is
**constructive interference**. Two perfectly inverted waveforms
(one is the exact negative of the other), summed, cancel completely —
**destructive interference**. Real stereo mixes sit somewhere between
these extremes: a stereo widener, a chorus effect, or just two
different microphones on the same source will leave left and right
partially, not perfectly, correlated at any given frequency.

This is not a niche concern. As a 2023 sonible engineering article on
exactly this problem (cited below) points out, mono playback is common
well beyond old club systems: wireless speakers like the Amazon Echo
and Sonos, restaurant and retail sound systems, and any phone's own
single speaker all reproduce in mono. When two partially-correlated
channels get summed down, the result is audibly described as
**comb-filtering** — a "metallic and hollow" quality, named for the
shape of the resulting frequency response, which cancels heavily at
some frequencies and reinforces at others, evenly spaced like the teeth
of a comb. The same source goes from full and wide in stereo to
noticeably thinner the moment it's heard on any of those mono devices.
A related, practical diagnostic tool worth knowing exists even though
it's outside this stage's scope: a **correlation meter**, standard in
most DAWs, reports a single number from −1 to +1 summarising how
in-phase two channels are across the whole spectrum at once — this
project's `mono_compatibility()` goes further by breaking that same
underlying question down per frequency band, rather than collapsing it
to one number.

### The exact relationship: energy loss as a function of phase difference

For two equal-amplitude sine waves at frequency `f` with phase
difference `φ` between them, a standard trigonometric identity
(sum-to-product) gives:

```
sin(θ) + sin(θ + φ) = 2·cos(φ/2)·sin(θ + φ/2)
```

Averaging (not just summing) the two channels — the same convention
`load_audio()` uses for `mono` — divides this by 2, giving a combined
amplitude of `cos(φ/2)` times the original amplitude. Since energy is
proportional to amplitude squared, the **fraction of energy retained**
after mono-summing is `cos²(φ/2)`, and the **fraction lost** is
`sin²(φ/2)`. Three checkpoints worth having memorised:

- `φ = 0` (in phase): `sin²(0) = 0` — nothing lost, perfect
  reinforcement.
- `φ = π/2` (quadrature, 90° out of phase): `sin²(π/4) = 0.5` — exactly
  half the energy lost.
- `φ = π` (fully inverted): `sin²(π/2) = 1` — complete cancellation.

This is exactly what `mono_compatibility()` is built to detect, and
exactly what its validation test checks: inject a known `φ` at a known
frequency, and confirm the measured energy loss in the corresponding
band matches `sin²(φ/2)` — constructed ground truth, in the absence of
an external reference implementation for this specific measurement.

### Scope: energy loss per band, not a full phase measurement

Worth being precise about what this stage does and doesn't measure.
`welch()` computes a PSD via `|FFT|²` — the squared magnitude of the
spectrum — which discards phase information entirely as part of the
computation. Comparing `welch(mono)` against the channels' own PSDs
therefore measures *how much energy was lost* summing to mono, not the
actual phase difference between L and R at each frequency (which would
need something like cross-correlation or a Hilbert transform on the
raw waveforms, a meaningfully bigger undertaking). This narrower scope
was a deliberate choice, confirmed before writing any code: it's
exactly what `spec.md` and `STAGES.md`'s exit criteria ask for
("per-band energy comparison... identifying where and how severely"),
and energy loss is the thing that's actually audible — a
producer doesn't hear "these channels are 73° out of phase," they hear
"the bass disappeared on my phone speaker."

### A bug from spectral leakage, and the fix

Worth documenting properly, same as Stage 3's window bug. The first
version compared each band's *loss fraction* directly, treating any
band with zero source energy as trivially "no loss." Testing a single
1kHz tone (which belongs entirely to the "mid" band, 800–4000Hz)
revealed the reported `worst_band` was consistently **"sub"** —
wrong, and wrong in a way worth understanding rather than just fixing.

The cause: Stage 3's Hann windowing reduces spectral leakage but
doesn't eliminate it — a pure tone still contributes a tiny, non-zero
amount of energy to every frequency bin, just many orders of magnitude
smaller than its true peak (measured here: ~`10⁻¹⁴` in the "sub" band
against ~`0.5` in "mid", a fourteen-orders-of-magnitude gap). That
leaked energy isn't random noise — it's a scaled echo of the real
tone, carrying the *same* phase relationship between channels as the
tone itself. So a fully-inverted tone's leakage into "sub" shows the
same ~100% loss fraction as the real cancellation in "mid," even
though "sub" contains no meaningful signal at all. The fix: a band's
loss fraction is only reported if that band holds a meaningful share
of the signal's *total* energy (`>10⁻⁶` of it); below that, it's
treated as noise, not a finding. The general lesson: a measurement
computed from negligible data is not a small version of the truth, it
can be an arbitrary, misleading number that happens to look plausible.

### Why the score is energy-weighted, not a plain average

A related design correction, caught by the same test: initially, the
overall `score` averaged the loss fraction across all five bands
equally. For a signal that's a single fully-inverted 1kHz tone — 100%
of its actual energy destroyed on mono-summing — this gave a score of
80/100, since four bands with zero real content each contributed a
"perfect" 0%-loss score that diluted the one band that mattered. The
fix weights each band's contribution to the score by its actual share
of total energy, so a track that's entirely mid-range and loses all of
it scores near 0, and a mixed-content signal (confirmed in testing:
equal energy in an unaffected bass tone and a fully-cancelled mid tone)
scores proportionally — 50, not an unweighted 60 (only two of five
bands affected) or 100 (if the empty bands wrongly dominated). A score
is only as meaningful as what it's actually averaging over.

### References

- [Wave interference — Wikipedia](https://en.wikipedia.org/wiki/Wave_interference) — constructive/destructive interference and the `cos(φ/2)` combined-amplitude result for two phase-shifted sinusoids
- [Avoiding the Collapse: From Stereo to Mono (Compatibility) — sonible](https://www.sonible.com/blog/stereo-to-mono/) — the practical mixing-engineering context: which real devices play in mono, comb-filtering, and correlation meters as the standard (coarser) diagnostic tool

---

## What's next

Stage 6 (librosa-based BPM/key detection, frequency balance against a
genre reference curve using this same `band_energy()` utility, and the
database layer) will get its own section here once it exists. Not
written yet, on purpose — this document tracks the code, it doesn't
get ahead of it.

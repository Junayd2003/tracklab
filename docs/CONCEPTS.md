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
python3 -m venv .venv        # first time only
.venv/bin/pip install -r requirements-docs.txt
.venv/bin/python build_pdf.py
```

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

The trade-off is that pinned versions need occasional deliberate
upgrading (a pin never fixes itself), which is a reasonable price for
reproducibility in a project meant to be handed to a stranger (Stage
14's exit criterion).

**Where it appears:** `requirements.txt`.

### Why `.gitignore` is structured the way it is

Four different reasons for exclusion live in that one file, and it's
worth being able to name which is which:

- **Secrets** (`.env`) — must never enter git history, because history
  is permanent even if the file is later deleted from HEAD.
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
- [pip: Repeatable installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/)
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
of the signal to discard permanently. Frequencies masked by louder
nearby frequencies, or above roughly 16–20kHz where perception is
already weak in most listeners, get thrown away to shrink the file.

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
frequency*). Sample a signal that *does* have higher-frequency content,
and those frequencies don't just vanish — they fold back and appear as
false, lower frequencies in the sampled signal. That's aliasing, and
it's not fixable after the fact; the information needed to tell the
alias from a real low frequency is gone.

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
free from a short declarative list rather than boilerplate. The
practical benefit over a dict: `audio.mono` is checked by tooling at
development time, so a typo (`audio.mnoo`) is caught before running the
code; `audio['mnoo']` on a dict is a `KeyError` that only surfaces at
runtime, possibly deep into a pipeline.

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
- [Nyquist–Shannon sampling theorem — Wikipedia](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem)
- [`librosa.load` documentation (0.11.0)](https://librosa.org/doc/0.11.0/generated/librosa.load.html) — confirms `res_type='soxr_hq'` as the default resampler
- [`python-soxr`](https://github.com/dofuuz/python-soxr) — the resampling library librosa's default delegates to
- [LAME Technical FAQ](https://lame.sourceforge.io/tech-FAQ.txt) — encoder/decoder delay and padding, the mechanism behind the MP3/WAV duration mismatch
- [`dataclasses` — Python documentation](https://docs.python.org/3/library/dataclasses.html)
- [Pydantic documentation](https://docs.pydantic.dev/latest/) — the validating counterpart to a plain dataclass, relevant from Stage 6 onward
- [pytest: How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [pytest: Temporary directories and files (`tmp_path`)](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [pytest: `parametrize`](https://docs.pytest.org/en/stable/how-to/parametrize.html)

---

## What's next

**Note (2026-08-22):** the stage numbering above changed after a
project rescope — genre/mood classification and the Claude feedback
layer were cut from Tier 1, and the remaining work was renumbered from
fourteen stages to eight. See `docs/STAGES.md` and the vault's
`decisions.md` for the reasoning. The Stage 2 section above is
unaffected; everything from here on refers to the new numbering.

Stage 3 (Welch power spectral density estimation, from scratch) will
get its own section here once it exists: what a periodogram is and why
it's a noisy PSD estimate on its own, what windowing and segment
overlap are doing, and why averaging periodograms trades resolution for
reduced variance. Stage 4 (LUFS loudness, from scratch, ITU-R BS.1770)
follows: the K-weighting filter chain, the two-stage gating, and why
integrated loudness rather than RMS or peak. Stage 5 (mono/phase
compatibility, from scratch) after that. Not written yet, on purpose —
this document tracks the code, it doesn't get ahead of it.

# BUILD_LOG.md

The running record of what has been built. Claude Code reads the last
entry at the start of every session to know where to resume, and
appends a new entry at the end of every session.

**Newest entry at the bottom.** Append, never overwrite.

---

## Entry format

Copy this shape exactly for each new entry.

```
## Session N — YYYY-MM-DD — Stage X: <stage name>

**Done**
- <what was actually completed and works>

**Files touched**
- `path/to/file.py` — <one line on what it does>

**Decisions**
- <choice made, alternatives rejected, why> (also logged to vault
  decisions.md)

**Concepts explained**
- <concept> (also logged to vault learning.md)

**In progress / not finished**
- <anything half-built, and precisely where it stopped>

**Open questions**
- <anything needing my decision before work continues>

**Exit criteria met?**
- Yes / No / Partially — <if not, what is missing>

**Next session starts with**
- <one concrete sentence>
```

---

## Session 0 — 2026-08-18 — Planning

**Done**
- Project scoped: `tracklab`, local-first audio analysis dashboard
- Feature tiers agreed, Tier 1 is the deliverable
- Stack chosen: FastAPI, SQLAlchemy, SQLite, librosa, scikit-learn,
  React with Vite, Claude API
- Fourteen stages defined in `docs/STAGES.md`
- `CLAUDE.md` written, vault structure set up

**Decisions**
- FMA over GTZAN for the genre classifier: GTZAN's ten genres contain
  no electronic subgenres, and I produce electronic music, so GTZAN
  labels would be useless to me
- Local-first, no cloud deployment: avoids hosting and storage costs
  entirely, and the architecture is what interviewers care about, not
  the hosting
- Libraries used freely here, unlike `pyode`: this is a product, not a
  study of numerical methods
- Real-time DAW monitoring via a virtual audio device rather than a VST
  plugin: a VST needs JUCE and C++, which is months of work outside
  this timeline. A virtual audio device gets the same result in Python.

**Open questions**
- None. Ready to start Stage 1.

**Exit criteria met?**
- Yes, planning complete.

**Next session starts with**
- Stage 1: repo skeleton, virtual environment, dependencies, first
  commit, verify ffmpeg.

---

## Session 1 — 2026-08-21 — Stage 1: Repo skeleton and environment

**Done**
- Directory structure created at `~/projects/tracklab`: `backend/`
  with `audio/`, `db/`, `ml/`, `ai/` subpackages, `docs/`, `tests/`
- `.gitignore`, `README.md` stub written
- `CLAUDE.md`, `STAGES.md`, `BUILD_LOG.md` copied from the vault into
  the repo so they travel with the code, per the layout in `CLAUDE.md`
- `backend/.venv` created and dependencies installed: fastapi,
  uvicorn, sqlalchemy, librosa, soundfile, numpy, scipy, scikit-learn,
  anthropic, python-multipart, python-dotenv
- `requirements.txt` pinned via `pip freeze`
- `git init`, two commits made
- ffmpeg verified present (7.1.1)

**Files touched**
- `.gitignore` — excludes venv, `.env`, databases, audio data, trained
  model binaries, frontend build output, OS/editor noise
- `README.md` — one-paragraph stub, points to `docs/` for real detail
- `requirements.txt` — pinned dependency list
- `CLAUDE.md` — Python version corrected from 3.12 to 3.13

**Decisions**
- Python 3.13 instead of the originally planned 3.12, since that is
  what was actually on the machine and `numba` already supports it
  (also logged to vault `decisions.md`)

**Concepts explained**
- Virtual environments (also logged to vault `learning.md`)
- Why dependency versions are pinned (also logged to vault
  `learning.md`)

**In progress / not finished**
- Nothing mid-built. Stage 1 is complete.

**Open questions**
- Resolved same session: global git identity set to
  `Junayd Ismail <junayd.i@hotmail.com>`, existing commits rewritten
  via `git rebase --root --exec`, branch renamed `master` → `main`.

**Exit criteria met?**
- Yes. `python -c "import librosa, fastapi, sqlalchemy"` runs clean in
  the venv; `ffmpeg -version` returns a version.

**Next session starts with**
- Stage 2: `backend/audio/loader.py` — format loading, resampling to
  44.1kHz, lossy-format flagging, SHA-256 hashing.

---

## Session 2 — 2026-08-21 — Stage 2: Audio loading and format handling

**Done**
- `backend/audio/loader.py` built: SHA-256 hashing (streamed in 1MB
  chunks), extension-based format detection with lossy/lossless
  classification, `load_audio()` resampling any supported file to
  44.1kHz and returning mono + stereo arrays via a `LoadedAudio`
  dataclass
- Test tracks copied into `data/samples/` (gitignored): two personal
  MP3s plus one WAV that is the same track as one of the MP3s, found by
  scanning the FL Studio Projects folder by file content (`file`
  command), not just by extension, after I asked to check for
  mislabeled WAVs
- `tests/test_loader.py` written: 16 pytest tests against synthetic
  sine-wave fixtures generated at test time (not personal audio), all
  passing
- `pytest` installed and pinned in `requirements.txt`
- `.gitignore` updated to exclude `.pytest_cache/`
- Manually verified against real tracks: `PS Cmin 160.mp3` and
  `PS Cmin 160 24.wav` (same track) both load at sample_rate 44100,
  durations 204.07s vs 204.02s (consistent to ~50ms), hash is
  deterministic across repeated calls on the same file
- `CLAUDE.md` corrected: vault path was `~/OneDrive/SecondBrain/...`,
  which doesn't exist on this machine — actual mount is
  `~/Library/CloudStorage/OneDrive-Personal/SecondBrain/...`
- `CLAUDE.md` session protocol extended with understanding checkpoints
  (retrieval practice at session start, "why" questions after each
  chunk, my own concept attempt logged alongside the polished one) —
  see `CLAUDE.md` for the reasoning

**Files touched**
- `backend/audio/loader.py` — hashing, format detection, resampling,
  mono/stereo loading
- `tests/test_loader.py` — pytest suite on synthetic fixtures
- `requirements.txt` — added `pytest==9.1.1`
- `.gitignore` — added `.pytest_cache/`
- `CLAUDE.md` — vault path corrected, session protocol extended
- `data/samples/` — three personal test tracks (gitignored, not
  committed): two MP3s, one WAV

**Decisions**
- Lossy/lossless format mapping as module-level constants in
  `loader.py`, not a separate config file (also logged to vault
  `decisions.md`)
- `LoadedAudio` as a `@dataclass`, not a dict (also logged to vault
  `decisions.md`)
- Decode audio once as stereo, derive mono by averaging channels rather
  than decoding twice — ties `mono` to being the literal channel sum
  Stage 4's phase-cancellation analysis needs (also logged to vault
  `decisions.md`)
- Test fixtures are synthetic sine waves generated at test time, not
  personal audio referenced by path or committed as binary fixtures
  (also logged to vault `decisions.md`)

**Concepts explained**
- Streaming SHA-256 hashing vs loading a whole file into memory (also
  logged to vault `learning.md`)
- Resampling as interpolation plus anti-aliasing filtering, not just
  relabeling — flagged for me to verify which resampler librosa
  actually uses myself, not covered in full (also logged to vault
  `learning.md`)
- MP3 encoder priming/padding (LAME) as the cause of the ~50ms duration
  mismatch between the MP3 and WAV of the same track (also logged to
  vault `learning.md`)
- `@dataclass` vs a plain dict for structured return values (also
  logged to vault `learning.md`)
- pytest fixtures, `tmp_path`, `parametrize`, and why synthetic test
  data over personal files (also logged to vault `learning.md`)

**In progress / not finished**
- M4A untested: no M4A files found in the FL Studio Projects folder.
  WAV and MP3 both verified against real tracks; M4A verification
  deferred until a file is available
- Nothing staged or committed to git yet this session

**Open questions**
- The vault's own `BUILD_LOG.md` (a leftover copy from before Session
  1) has not been updated since Session 0 and is now stale, since
  `BUILD_LOG.md` per `CLAUDE.md`'s "Where things live" belongs only in
  the repo. Delete it, or leave it as a historical snapshot?
- Ready to commit Stage 2's work, or hold until M4A is verified?

**Exit criteria met?**
- Partially — WAV and MP3 consistency verified on real tracks; M4A
  untested

**Next session starts with**
- Either verify an M4A file once available, or move to Stage 3 core
  feature extraction with M4A verification logged as a known gap.

---

## Session 3 — 2026-08-22 — Project re-scope: Tier 1 narrowed to 8 stages

**Done**
- Received and evaluated an external critique of the project's scope
  and positioning: the ML component judged weak and expensive relative
  to what it would cost; the mathematics judged undersold by the
  original "libraries used freely, this is a product not a study of
  numerical methods" framing; the 28 September target flagged as
  colliding directly with final year and a stacked postgraduate
  application pipeline
- Rescoped Tier 1: cut genre/mood classification and the Claude
  feedback layer, both moved to Tier 2, built only after a hard freeze
  on 2026-09-28 (tag `v1.0`)
- Fourteen stages collapsed to eight (`docs/STAGES.md` rewritten):
  repo + CI, loading, Welch-from-scratch, LUFS-from-scratch,
  mono/phase-from-scratch, librosa features + database, FastAPI +
  integration tests, minimal dashboard + README + freeze
- Adopted ground-truth-validatability as the explicit criterion for
  what gets implemented from scratch versus called via a library:
  Welch, LUFS, and mono/phase have independently checkable ground
  truth (`scipy.signal.welch`; `pyloudnorm` + ffmpeg's `ebur128` to
  within 0.1 LU; synthetic signals with a known injected phase
  inversion); BPM and key detection do not, and stay as `librosa`
  calls
- `CLAUDE.md` updated: intro rewritten to match the narrower Tier 1,
  new "What gets implemented from scratch" table added, "Scope
  discipline" rewritten with 28 September framed as a hard stop rather
  than a soft target, with explicit guidance to protect Stage 4's
  validation rigour over Stage 8's dashboard polish if the calendar
  tightens
- Vault `spec.md` updated: Tier 1/Tier 2 feature lists rewritten to
  match, data model annotated to show which tables are Tier 1 versus
  deferred to Tier 2
- Vault `decisions.md`: three entries logging the rescoping reasoning
  in full
- `docs/CONCEPTS.md`'s forward-looking note updated to reference the
  new Stage 3–5 content (Welch, LUFS, mono/phase) instead of the old,
  now-superseded "core feature extraction" framing

**Files touched**
- `docs/STAGES.md` — rewritten: 8 stages replacing 14
- `CLAUDE.md` — intro, technical constraints, new from-scratch table,
  scope discipline rewritten
- `docs/CONCEPTS.md` — "What's next" section updated
- (vault) `spec.md` — Tier 1/2 rewritten, data model annotated
- (vault) `decisions.md` — three new entries, 2026-08-22

**Decisions**
- See vault `decisions.md`, three entries dated 2026-08-22: Tier 1
  rescoped and narrowed to 8 stages; ground-truth-validatability
  adopted as the from-scratch criterion; CI pulled forward to Stage 1

**Concepts explained**
- None new this session — a planning/re-scope session, not a build
  session

**In progress / not finished**
- No GitHub remote exists yet for tracklab; Stage 1's revised exit
  criteria (CI green on push) can't be met until one is created — a
  deliberate separate step, not done as part of this session
- The from-scratch DSP itself (Stages 3–5) not started

**Open questions**
- None blocking. Ready to either set up the GitHub remote and get CI
  green (closing the gap in Stage 1's revised exit criteria), or move
  straight to Stage 3 and treat CI as a fast-follow

**Exit criteria met?**
- N/A — planning session, no stage exit criteria targeted

**Next session starts with**
- Either: create the GitHub remote and get CI green (closing the gap
  in Stage 1's revised exit criteria), or start Stage 3: Welch
  spectral estimation from scratch, validated against
  `scipy.signal.welch`.

**Addendum, 2026-08-23** — a day after this session, a small addition
was made on top of the rescope above, before it was committed: Stage 7
gained a shared-secret API key gate (`.env`, checked on every route,
required from the frontend and CLI). Reasoning: the app binds to
`0.0.0.0` so it's reachable from my phone over wifi, which also means
anyone else on that network can reach it — a proportionate gate for a
single-user, LAN-exposed tool, not full multi-user auth. `STAGES.md`
(Stage 7) and `CLAUDE.md` (technical constraints) both reflect this;
vault `spec.md`/`decisions.md` were updated the same day. A Docker
suggestion and an SMTP-based abuse-alerting idea were also raised and
deliberately not adopted in the same window — Docker because the
project runs on one machine with no deployment target, so venv+CI
already covers the reproducibility need; SMTP alerting because it's a
heavier feature than the shared-secret gate warrants before there's
even a published app to abuse. Also decided in this window, then
reversed: a request to sync the repo itself via OneDrive for
cross-device (Mac + Windows) access — rejected, since OneDrive's
continuous file-sync is a known corruption risk against git's `.git`
directory, and the venvs contain macOS-specific compiled binaries that
wouldn't run on Windows regardless. The correct mechanism (a GitHub
remote, already needed for CI) was proposed but the user chose to
leave it for now rather than set it up immediately.

---

## Session 4 — 2026-08-28 — Stage 3: Welch spectral estimation, from scratch

**Done**
- Committed the Session 3 rescope and the CONCEPTS.md/PDF tooling,
  previously uncommitted, as two separate commits with accurate
  messages (double-checked against the actual diff first, since
  `BUILD_LOG.md`'s Session 3 entry hadn't mentioned the 2026-08-23
  shared-secret addition that was already in the same working tree)
- `backend/audio/spectral.py` built: `_periodic_hann()`,
  `_windowed_periodogram()`, `welch()` — Hann window, 4096-sample
  segments, 50% overlap, implemented directly rather than calling
  `scipy.signal.welch`
- `tests/test_spectral.py`: 9 pytest tests, all passing, validating
  against `scipy.signal.welch` on synthetic sine waves and white noise
  to `rtol=1e-9`
- Full test suite (25 tests total) passes with no regressions

**Files touched**
- `backend/audio/spectral.py` — Welch's method, from scratch
- `tests/test_spectral.py` — validation suite against scipy
- `docs/STAGES.md` — Stage 3 marked done
- `docs/CONCEPTS.md` — Stage 3 section added (periodogram, windowing,
  the symmetric-vs-periodic Hann bug, references)

**Decisions**
- Hann window, 4096-sample segments, 50% overlap, with the same
  explicit parameters passed to both implementations in the validation
  test rather than relying on either's defaults (logged to vault
  `decisions.md`, 2026-08-28, before any code was written)
- `welch()` deliberately does not detrend each segment (remove the
  mean) the way `scipy.signal.welch`'s default does — audio doesn't
  carry a meaningful DC offset, so there's nothing to correct for. The
  validation test passes `detrend=False` to scipy to compare the same
  thing on both sides, not silently compare two different algorithms.

**Concepts explained**
- What a periodogram is and why Welch's method (segment, window,
  average) reduces its variance (also logged to vault `learning.md`)
- Symmetric vs periodic Hann windows, and why FFT-based spectral
  analysis needs the periodic variant — found as a real bug, not a
  hypothetical: the first full `welch()` vs `scipy.signal.welch`
  comparison showed a consistent `~2×10⁻⁴` relative error, traced to
  `np.hanning()` (symmetric) vs `scipy`'s internal `get_window('hann',
  N)` (periodic) producing very slightly different windows. Fixed by
  writing the periodic Hann formula directly; agreement then tightened
  to `~10⁻¹⁵`, floating-point limit (also logged to vault
  `learning.md`)

**In progress / not finished**
- Nothing mid-built. Stage 3 is complete.

**Open questions**
- None blocking.

**Exit criteria met?**
- Yes. `rtol=1e-9` agreement with `scipy.signal.welch` on sine waves
  and white noise — see `docs/STAGES.md`, Stage 3.

**Next session starts with**
- Stage 4: LUFS loudness from scratch (ITU-R BS.1770), validated
  against `pyloudnorm` and ffmpeg's `ebur128` to within 0.1 LU. Flagged
  in `STAGES.md` as the load-bearing stage — may take two sessions.

---

## Session 5 — 2026-08-28 — Stage 4: LUFS loudness, from scratch

**Done**
- Before writing any code, checked whether `pyloudnorm` and ffmpeg's
  `ebur128` already agreed with each other on a real track — they did
  (−14.4192 vs −14.4 LUFS), confirming the stated 0.1 LU exit criterion
  was achievable rather than an arbitrary number
- `backend/audio/loudness.py` built: K-weighting via two biquad filters
  (RBJ cookbook formulas — high-shelf, high-pass), 400ms block-based
  mean-square measurement with 75% overlap, two-stage gating (absolute
  −70 LUFS, relative −10 LU), `integrated_loudness()`
- `tests/test_loudness.py`: 7 pytest tests, all passing — sine, white
  noise, ffmpeg cross-check, and all three named edge cases
  (near-silence, heavy limiting, a quiet passage)
- Manually verified against real tracks in `data/samples/`: exact
  match against `pyloudnorm` on all three test tracks; within ffmpeg's
  displayed precision (1 decimal place) against `ebur128`
- `pyloudnorm` installed and pinned in `requirements.txt`
- Full test suite (31 tests total) passes with no regressions
- Stage 3's still-uncommitted code (`spectral.py`,
  `tests/test_spectral.py`) and this session's Stage 4 work both sit
  ready to commit — held, same as usual, pending confirmation

**Files touched**
- `backend/audio/loudness.py` — K-weighting, gating, integrated
  loudness, from scratch
- `tests/test_loudness.py` — validation suite against pyloudnorm and
  ffmpeg
- `requirements.txt` — added `pyloudnorm==0.2.0`
- `docs/STAGES.md` — Stage 4 marked done, BS.1770-4 vs -5 gap noted
- `docs/CONCEPTS.md` — Stage 4 section added

**Decisions**
- RBJ cookbook biquad formulas over `pyloudnorm`'s alternative
  "DeMan" (bit-exact ITU coefficient) filters — the 0.1 LU target
  didn't need bit-exact reproduction, and checking achievability first
  confirmed the simpler approach was sufficient (logged to vault
  `decisions.md`, 2026-08-28)

**Concepts explained**
- Why LUFS differs from RMS and peak (also logged to vault
  `learning.md`, pending my own attempt first)
- K-weighting: what the high-shelf and high-pass stages each
  approximate about human hearing (also logged to vault `learning.md`,
  pending my own attempt first)
- The two-stage gating and why each gate exists separately (also
  logged to vault `learning.md`, pending my own attempt first)
- A test failure diagnosed correctly: `pyloudnorm` agreeing exactly
  with my implementation on the same edge-case signal proved the test's
  *assumption* was wrong, not the code — same shape as Stage 3's window
  bug, opposite conclusion

**In progress / not finished**
- Nothing mid-built. Stage 4 is complete.
- One open, explicitly-flagged gap: implemented against what's
  commonly described as BS.1770-**4**'s algorithm; the current
  published standard is BS.1770-**5** (2023) — the difference between
  them hasn't been checked

**Open questions**
- None blocking.

**Exit criteria met?**
- Yes. 0.1 LU agreement with both `pyloudnorm` and ffmpeg's `ebur128`
  — see `docs/STAGES.md`, Stage 4, for the full detail including the
  BS.1770-4/-5 caveat.

**Next session starts with**
- Stage 5: mono/phase compatibility, from scratch, built on Stage 3's
  Welch estimator. User has asked to pause here to catch up on theory
  and comprehension before continuing — this is a deliberate stop, not
  a blocker.

---

## Session 6 — 2026-08-29 — Post-freeze planning: Tier 2 cadence and feature list

**Done**
- Planning-only session, no code: agreed a realistic post-freeze
  cadence for Tier 2 — roughly six fortnightly sessions, two to three
  hours each, across October to December 2026. Realistic because the
  backend and dashboard scaffolding from Tier 1 will already exist by
  then, so Tier 2 sessions are additive, not foundational
- Tier 2 formally laid out for the first time since the 2026-08-22
  rescope (it had only existed as terse one-line bullets until now):
  genre-aware reference curves, track library with search/filters,
  progress-over-time charts, mastering readiness score, section
  detection — ordered roughly least to most effort, section detection
  flagged as the most expensive of the five
  - Noted the connection between genre-aware reference curves and the
    deferred genre classifier: the curves work off a manual genre tag
    either way, but become more useful automatically if a (even
    simple) classifier gets added during Tier 2
- Recommended a mid-October planning session (after term starts, after
  the freeze lands) to scope the Tier 2 API additions, rather than
  starting Tier 2 with a build session directly
- Logged to Claude Code's own memory system (`tracklab_timeline.md`,
  project-type), separate from the vault, so the cadence and freeze
  date are available without needing to re-read the full vault

**Files touched**
- (vault) `spec.md` — Tier 2 section rewritten with the full feature
  list, effort ordering, and the genre-curve/classifier connection
- `CLAUDE.md` — short pointer added to "Scope discipline": Tier 2 is
  paced for after the freeze, full detail lives in `spec.md`
- Claude Code memory: `tracklab_timeline.md` (new), `MEMORY.md` (new)

**Decisions**
- None requiring `decisions.md` — this is a scheduling/capacity plan,
  not an architectural choice with alternatives rejected

**Concepts explained**
- None — planning session

**In progress / not finished**
- Stage 5 (mono/phase compatibility) still not started — this session
  was entirely about Tier 2, not Tier 1 build work

**Open questions**
- None blocking.

**Exit criteria met?**
- N/A — planning session, no stage exit criteria targeted

**Next session starts with**
- Stage 5: mono/phase compatibility, from scratch, built on Stage 3's
  Welch estimator, whenever the user is done catching up on theory.

---

## Session 7 — 2026-08-30 — Stage 5: Mono compatibility, from scratch

**Done**
- Confirmed the right scope before writing code: energy-loss-per-band
  (matching `STAGES.md`'s exit criteria), not a full phase-difference
  measurement via cross-correlation/Hilbert transform
- `backend/audio/spectral.py` gained `BAND_RANGES` and `band_energy()`
  — shared band vocabulary, added there rather than duplicated in
  `mono_compat.py`, since Stage 6's frequency-balance feature needs
  the same bands
- `backend/audio/mono_compat.py` built: `mono_compatibility(stereo, fs)`,
  deriving `mono` internally as `stereo.mean(axis=0)` (same invariant
  as `load_audio()`, not accepted as a separate argument)
- Validated against a first-principles formula, not a library: for two
  equal-amplitude sinusoids at phase difference φ, energy loss on
  mono-summing should equal `sin²(φ/2)`. Measured to within 1% across
  φ = 0, π/2, π
- Two real bugs caught and fixed by testing before being called done:
  spectral leakage causing a spurious "worst band" on a single test
  tone (fixed with an energy-materiality threshold), and an unweighted
  score diluting a fully-cancelled signal's severity (fixed by
  weighting by each band's actual energy share)
- `tests/test_mono_compat.py`: 8 pytest tests, all passing
- Full test suite (40 tests total) passes with no regressions
- `docs/CONCEPTS.md` Stage 5 section written: phase cancellation
  physics, the `sin²(φ/2)` derivation, both bugs documented in full,
  regenerated to PDF

**Files touched**
- `backend/audio/mono_compat.py` — mono compatibility, from scratch
- `backend/audio/spectral.py` — added `BAND_RANGES`, `band_energy()`
- `tests/test_mono_compat.py` — validation suite against theory
- `docs/STAGES.md` — Stage 5 marked done
- `docs/CONCEPTS.md` — Stage 5 section added

**Decisions**
- Energy-loss-per-band scope, not full phase measurement (logged to
  vault `decisions.md`, 2026-08-30)
- Shared band vocabulary in `spectral.py` (logged to vault
  `decisions.md`, 2026-08-30)
- Energy-materiality threshold and energy-weighted scoring — both bug
  fixes, logged to vault `decisions.md`, 2026-08-30

**Concepts explained**
- Phase cancellation as destructive interference, and the `sin²(φ/2)`
  energy-loss formula derived from the sum-to-product identity (also
  logged to vault `learning.md`, pending my own attempt first)
- Why a measurement computed from negligible-energy data isn't a small
  version of the truth — it can be an arbitrary, misleading number
  (also logged to vault `learning.md`, pending my own attempt first)

**In progress / not finished**
- Stage 5's actual code and tests are complete. `docs/CONCEPTS.pdf` is
  now one stage behind `CONCEPTS.md`'s source (missing the Stage 5
  section) — regenerating it hit a real, unrelated environment bug:
  pip 26.2.1's vendored `truststore` module crashes at import time
  because `platform.mac_ver()` returns empty inside this sandboxed
  tool environment (it can't read the system version plist), and this
  now blocks *any* fresh `pip install`, confirmed in both `docs/.venv`
  and `backend/.venv`, not just the docs tooling. A `sitecustomize.py`
  shim worked around the immediate crash, but a further dependency
  (`cffi`, pulled in transitively by `xhtml2pdf` → `pyHanko`, a PDF
  *signing* library we don't use) needed a source build that failed
  for follow-on, unrelated reasons (build isolation not inheriting the
  shim; no `setuptools` when isolation was disabled). Stopped digging
  once it was clear this was a genuine infrastructure issue, not
  something in the project's own code.

**Open questions**
- The pip/`mac_ver` issue above will need resolving before any new
  dependency can be installed in this sandboxed environment — worth
  checking whether it reproduces outside the sandbox (a plain
  terminal) before Stage 7 needs new packages.

**Exit criteria met?**
- Yes, for Stage 5 itself. Energy loss matches `sin²(φ/2)` to within
  1% across three tested phase differences; `worst_band` correctly
  identifies the affected band in every case. `CONCEPTS.pdf`
  regeneration is the one open item, blocked by the environment issue
  above, not by anything in Stage 5's own work.

**Next session starts with**
- Stage 6: `librosa`-based BPM/key detection, frequency balance
  against a genre reference curve (using this session's
  `band_energy()`), and the database layer (`tracks`, `features`
  tables only — see `spec.md`).

---

## Session 8 — 2026-08-30 — CONCEPTS.md literature pass, PDF pipeline fixed

**Done**
- Thorough revision pass across all five existing `CONCEPTS.md`
  sections (Stages 1–5), not just new content: wove in primary-source
  citations directly into explanations rather than leaving them as
  end-of-section links only, and added concrete worked examples
  throughout. Specifics: a live `sys.path` comparison for venvs (PEP
  405 cited), a real NumPy 2.0 breaking change (`np.NaN`/`np.Inf`
  removed) for dependency pinning (Semantic Versioning cited), a
  concrete "recovering a deleted secret from git history" example, the
  auditory masking mechanism behind lossy compression (with the
  textbook cat/vacuum-cleaner example), a worked aliasing example
  (30kHz → false 14.1kHz at 44.1kHz) for Nyquist–Shannon, PEP 557 for
  dataclasses, Welch's original 1967 paper (DOI, IEEE) for Stage 3,
  EBU Tech 3341 as the actual origin of LUFS's two-stage gating
  (distinct from ITU-R BS.1770 itself), and a real audio-engineering
  source (sonible) for Stage 5's mono-compatibility context, including
  comb-filtering terminology and correlation meters as the standard
  (coarser) alternative diagnostic. Every new citation was verified to
  actually load before being added — none guessed
- Found and properly fixed the `CONCEPTS.pdf` regeneration blocker from
  Session 7. The real root cause was more fundamental than the
  sandbox's `platform.mac_ver()` issue found then: Homebrew's
  `python@3.13` build on this machine (now 3.13.15, patched since
  Session 1) is linked against a `libexpat` symbol newer than what's
  actually available at runtime, so anything importing
  `xml.parsers.expat` — including `pip`'s own vendored `distlib` —
  fails with a `dlopen` symbol error. Confirmed with a plain
  `python3 -c "import xml.parsers.expat"`, no sandbox or pip involved,
  proving this reproduces identically outside Claude Code, in this
  user's own terminal, right now. Traced through three compounding pip
  26.2.1 issues along the way (a `truststore` SSL-context crash, a
  wheel-platform-tag mismatch, and a new `_prevent_import_hook` audit
  feature misfiring on `--target` installs) before finding the
  underlying expat problem. Fix: `/usr/bin/python3` (Apple's bundled
  Python, unaffected) works fine as the docs-tooling venv's base
  interpreter; `CONCEPTS.md`'s regeneration instructions updated to use
  it explicitly, with the diagnosis written inline so this doesn't need
  rediscovering
- `CONCEPTS.pdf` regenerated successfully: 14 pages, 32 verified link
  annotations (up from 8 pages / 18 links)
- `docs/requirements-docs.txt` re-pinned against the working
  Python 3.9-based environment (the previous pins were Python
  3.13-specific and don't all resolve on 3.9)
- Sanity-checked `CLAUDE.md` and `docs/STAGES.md` for staleness —
  confirmed both current from Session 7's consolidation, no changes
  needed there this session

**Files touched**
- `docs/CONCEPTS.md` — literature/examples pass across Stages 1–5, plus
  updated regeneration instructions
- `docs/requirements-docs.txt` — re-pinned for Python 3.9 compatibility

**Decisions**
- None requiring `decisions.md` — this was a documentation-depth and
  tooling-fix session, not a design choice with alternatives rejected

**Concepts explained**
- None new for the project itself — this session deepened existing
  explanations rather than introducing new ones

**In progress / not finished**
- The underlying Homebrew `python@3.13`/`libexpat` mismatch on this
  machine is still unfixed at the system level (only worked around for
  docs tooling via `/usr/bin/python3`). Worth running
  `brew reinstall expat` (or `python@3.13`) outside any sandboxed tool,
  in a normal terminal, since it could affect other fresh `pip install`
  operations on `backend/.venv` too, not just docs tooling

**Open questions**
- None blocking.

**Exit criteria met?**
- N/A — documentation and tooling session, no stage exit criteria
  targeted.

**Next session starts with**
- Stage 6: `librosa`-based BPM/key detection, frequency balance
  against a genre reference curve, and the database layer.

---

## Session 9 — 2026-09-02 — New document: CODE_GUIDE.md

**Done**
- Created `docs/CODE_GUIDE.md`: a code-first companion to
  `CONCEPTS.md`, same stage structure, walking through the real current
  source of `loader.py`, `spectral.py`, `loudness.py`, and
  `mono_compat.py` function by function — each with its actual code
  inline, algorithm/origin, purpose within tracklab, call sites, and a
  logic walkthrough. Source pulled fresh from disk immediately before
  writing, so every snippet matches the real files exactly
- Cross-linked the two documents: `CONCEPTS.md`'s intro now explains
  the theory/code split, and each of its four stage sections links to
  `CODE_GUIDE.md`'s corresponding section
- Generalised `docs/build_pdf.py` to render both documents (was
  hardcoded to `CONCEPTS.md` only); `CODE_GUIDE.pdf` now regenerates
  alongside `CONCEPTS.pdf` from one command
- `CODE_GUIDE.pdf` generated: 9 pages
- **Follow-up same session:** code blocks in the PDF weren't rendering
  like a real editor — flat, uncoloured text. Added proper Pygments
  syntax highlighting (keywords, strings, comments, decorators all
  coloured, matching what VS Code or GitHub would show) plus inline
  line numbers, generated via `markdown`'s `codehilite` extension.
  Hit two real tooling snags along the way: `codehilite`'s
  `extension_configs` path coerces every value through a strict bool
  parser that rejects the string `'inline'` even though Pygments'
  own formatter accepts it (worked around by constructing the
  extension instance directly and setting its config dict, bypassing
  the validator); and `xhtml2pdf`'s CSS parser doesn't support the
  `:not()` selector (removed it — normal CSS cascade/specificity
  already achieved the same effect without it). Also replaced the one
  snippet that wasn't a faithful full copy of the source
  (`integrated_loudness()` had elided the `np.errstate` blocks with a
  footnote) with the complete, exact function body — verified
  indentation is preserved correctly in the rendered PDF by extracting
  its text and checking the whitespace matches the source exactly.
  `CODE_GUIDE.pdf` is now 10 pages
- Fixed two long-standing gaps in `CLAUDE.md`'s "Where things live"
  tree: neither `CONCEPTS.md` nor the (now newly added) `CODE_GUIDE.md`
  were ever listed there, noticed while adding the new file
- `.gitignore` updated for `docs/CODE_GUIDE.pdf` (same regenerated-
  build-output treatment as `CONCEPTS.pdf`)

**Files touched**
- `docs/CODE_GUIDE.md` — new
- `docs/CONCEPTS.md` — intro and four stage sections updated with
  cross-links
- `docs/build_pdf.py` — generalised to a list of (source, output) pairs
- `CLAUDE.md` — "Where things live" tree corrected
- `.gitignore` — added `docs/CODE_GUIDE.pdf`

**Decisions**
- Two documents (theory vs code), not one merged document (logged to
  vault `decisions.md`, 2026-09-02)

**Concepts explained**
- None new — this session organised and cross-referenced existing
  understanding rather than introducing new concepts

**In progress / not finished**
- Nothing mid-built. Both documents are current with all code through
  Stage 5.

**Open questions**
- None blocking.

**Exit criteria met?**
- N/A — documentation session, no stage exit criteria targeted.

**Next session starts with**
- Stage 6: `librosa`-based BPM/key detection, frequency balance
  against a genre reference curve, and the database layer. `CODE_GUIDE.md`
  gets a Stage 6 section once that code exists, same rule as `CONCEPTS.md`.

---

## Session 10 — 2026-09-05 — Stage 6: Track intelligence, frequency balance, database layer

**Pacing note:** agreed with the user to skip live understanding
checkpoints (retrieval questions, "why" pauses) for Stages 6-8, given
23 days remained before the freeze at session start. Documentation
(this file, `CONCEPTS.md`, `CODE_GUIDE.md`, `decisions.md`) is still
kept fully current — the deferral is teaching pace, not documentation.
A dedicated post-freeze session will properly cover theory, syntax,
code logic, and system design across everything built during this
faster stretch. Logged to `CLAUDE.md`'s session protocol and to Claude
Code's own memory (`tracklab_pacing_agreement.md`) so this isn't lost
if a future session starts fresh.

**Done**
- Descoped "frequency balance against a genre reference curve" before
  writing any code: no hardcoded genre data (researched and found no
  rigorous citable source for genre-specific spectral targets — a
  mastering-education source explicitly recommends reference-track
  comparison over fixed targets instead). `frequency_balance()` is a
  generic per-band function; a "reference curve" is that same function
  called on a user-chosen reference track, a dashboard concern (Stage
  8), not backend data
- `backend/audio/intelligence.py`: `detect_bpm()` and `detect_key()`
  via `librosa`. Verified `librosa.beat.beat_track`'s actual return
  types empirically (tempo comes back as a NumPy array, not a plain
  float) before writing code around it. Key detection uses the
  Krumhansl-Schmuckler algorithm with the published Krumhansl-Kessler
  (1982) profiles, verified against independent sources before
  hardcoding
- Tested against real tracks: correctly detected F# minor on one
  track; on `PS Cmin 160.mp3` detected 161.5 BPM (close to the claimed
  160) but G minor rather than C minor (the dominant, a well-known
  tonic/dominant confusion in chroma-based key detection) and 74.9 BPM
  on the other track (exactly half of its claimed 150 -- the classic
  beat-tracking octave error). Both left as observed, not "fixed" --
  per the existing decision not to invest correctness effort into
  BPM/key detection
- `backend/audio/frequency_balance.py`: `frequency_balance()`, per-band
  dB relative to the track's own total energy -- normalises for
  loudness, and gives sub-vs-bass balance for free as a subtraction
- `backend/db/models.py` and `session.py`: SQLAlchemy `Track`/`Features`
  models (2.0-style declarative), engine, session factory, `init_db()`.
  Field names updated from the original pre-rescope plan to match what
  the codebase actually produces (no `dynamic_range`/`spectral_centroid`,
  five frequency bands not four)
- Stage 6's actual exit criterion met and tested end-to-end: a real
  track run through Stages 3-6, written to the database, read back,
  values identical (`tests/test_db.py::test_full_pipeline_round_trip_on_a_real_track`)
- 14 new tests across three new test files (`test_intelligence.py`: 5,
  `test_frequency_balance.py`: 6, `test_db.py`: 3). Full suite: 54
  passing, no regressions
- `docs/CONCEPTS.md` and `docs/CODE_GUIDE.md` Stage 6 sections written;
  PDFs regenerated

**Files touched**
- `backend/audio/intelligence.py` — new
- `backend/audio/frequency_balance.py` — new
- `backend/db/models.py` — new
- `backend/db/session.py` — new
- `tests/test_intelligence.py`, `tests/test_frequency_balance.py`,
  `tests/test_db.py` — new
- `docs/STAGES.md` — Stage 6 marked done
- `docs/CONCEPTS.md`, `docs/CODE_GUIDE.md` — Stage 6 sections added
- `CLAUDE.md` — pacing adjustment noted in session protocol
- (vault) `spec.md` — data model corrected to match real fields
- (vault) `decisions.md` — four new entries, 2026-09-05

**Decisions**
- No hardcoded genre reference-curve data (vault `decisions.md`)
- Frequency balance relative to total energy, not absolute (vault
  `decisions.md`)
- Krumhansl-Schmuckler for key detection, not skipping key detection
  entirely (vault `decisions.md`)
- Skip live teaching checkpoints for Stages 6-8, catch up post-freeze
  (this file, `CLAUDE.md`, Claude Code memory)

**Concepts explained**
- Octave error in beat tracking; tonic/dominant confusion in
  chroma-based key detection; the Krumhansl-Schmuckler algorithm; ORM
  mapping and SQLAlchemy Session scoping (all in `CONCEPTS.md` -- not
  quizzed live this session, per the pacing note above)

**In progress / not finished**
- Nothing mid-built. Stage 6 is complete.

**Open questions**
- None blocking.

**Exit criteria met?**
- Yes. Full pipeline (Stages 3-6) round-trips through the database
  with identical values on a real track.

**Next session starts with**
- Stage 7: FastAPI application, background job pipeline, and the
  shared-secret access gate. First new subsystem of this stretch
  (HTTP, background tasks) -- still moving at the faster Stage 6-8
  pace agreed this session.

---

## Session 11 — 2026-09-06 — Stage 7: FastAPI, background pipeline, access gate

**Done**
- `backend/pipeline.py`: `analyse_and_store()`, the orchestration
  function tying Stages 2-6 together, run as a FastAPI background task
- `backend/main.py`: `POST /tracks` (upload, hash, cache check, queue
  analysis), `GET /tracks/{id}` (status/result), a shared-secret
  dependency on both, CORS for the Vite dev server, lifespan-based
  startup (not the deprecated `@app.on_event`)
- `backend/schemas.py`: Pydantic response models
- `backend/db/models.py`: added `status`/`error_message` to `Track`;
  made `sample_rate`/`duration` nullable, since populating them
  requires the decode work Stage 7 explicitly keeps out of the request
  cycle -- only extension-based `format`/`is_lossy` are known at
  upload time
- Empirically verified (not assumed) that `TestClient` runs
  `BackgroundTasks` synchronously within the request call, via a
  `time.sleep()`-based probe, before designing the test suite around it
- Real end-to-end smoke test via actual `uvicorn` + `curl`: server
  started and shut down cleanly per its own logs, but `curl` couldn't
  connect (status `000`) -- a sandbox network restriction on this tool,
  not an application bug. `TestClient`'s 61 (now 78) passing tests,
  including full integration flows, already validate real behaviour
  via FastAPI's own standard, idiomatic testing approach
- Two real bugs found while writing the integration tests, both fixed:
  a required `Header(...)` returning 422 for a missing API key instead
  of 401 (inconsistent with a wrong key, which correctly gave 401);
  `librosa.beat.beat_track`'s `tempo` return type not being consistent
  (array on rhythmic audio, plain scalar float on a pure sustained
  tone with no onset structure) -- `tempo[0]` crashed on the scalar
  case, found by a synthetic edge-case test fixture, same pattern as
  Stage 3 and 5's bugs
- One real SQLite/SQLAlchemy gotcha found and fixed: a bare
  `sqlite:///:memory:` engine gives each thread its own, separately
  empty, database, and `TestClient` dispatches through a different
  thread than the one that creates the tables. Fixed with
  `StaticPool` + `check_same_thread=False`, per SQLAlchemy's own
  documented recommendation for exactly this situation
- 17 new integration tests (`tests/test_main.py`). Full suite: 61
  passing, no regressions
- `docs/CONCEPTS.md` and `docs/CODE_GUIDE.md` Stage 7 sections written;
  PDFs regenerated

**Files touched**
- `backend/main.py`, `backend/pipeline.py`, `backend/schemas.py` — new
- `backend/db/models.py` — `status`/`error_message` added,
  `sample_rate`/`duration` made nullable
- `backend/audio/intelligence.py` — `detect_bpm` fixed for
  inconsistent `tempo` return type
- `tests/test_main.py` — new
- `.env` (real secret, gitignored), `.env.example` — new
- `docs/STAGES.md` — Stage 7 marked done
- `docs/CONCEPTS.md`, `docs/CODE_GUIDE.md` — Stage 7 sections added
- (vault) `decisions.md` — four new entries, 2026-09-06

**Decisions**
- Decode work deferred to the background task, not done at upload time
  (vault `decisions.md`)
- Overridable `session_factory` module attribute, since
  `app.dependency_overrides` alone doesn't reach a background task
  called outside FastAPI's dependency injection (vault `decisions.md`)
- Two bug fixes (API key status code, BPM return type) logged together
  (vault `decisions.md`)

**Concepts explained**
- Why background tasks exist and how `TestClient` vs a real server
  differ in when they run; what Pydantic validates that a dataclass
  doesn't; CORS and the same-origin policy; the SQLite in-memory
  connection-scoping gotcha (all in `CONCEPTS.md` -- not quizzed live,
  per the Stage 6-8 pacing note)

**In progress / not finished**
- Nothing mid-built. Stage 7 is complete.

**Open questions**
- The real-server `curl` connectivity issue (sandbox network
  restriction, not an app bug) means a genuinely manual end-to-end
  check (running `uvicorn` and hitting it from outside this sandboxed
  tool) hasn't happened yet -- worth doing once, in a normal terminal,
  before Stage 8 builds a frontend against this API.

**Exit criteria met?**
- Yes. Three tracks uploaded in quick succession all complete, status
  visible throughout. Missing/wrong API key both correctly rejected
  (401). CI itself remains deferred (Stage 1's open item), so "passes
  in CI" is met as "passes locally," not literally in a CI pipeline.

**Next session starts with**
- Stage 8: minimal dashboard (Vite React), README rewritten as a
  technical report, test suite runnable in one command, freeze and
  tag `v1.0`. Last stage before the 28 September deadline.

---

## Session 12 — 2026-09-06 — Stage 8: Dashboard, README, v1.0 freeze

**Done**
- Scaffolded `frontend/` (Vite + React 19, `recharts` for the
  frequency-balance chart). Removed the default demo scaffold content
  (marketing CSS, unused assets)
- `frontend/src/api.js`: a small `fetch` wrapper attaching the
  shared-secret key to every request. `frontend/src/App.jsx`: upload,
  poll (`setInterval` inside `useEffect`, with cleanup to prevent
  orphaned intervals), metric cards, a `recharts` frequency-balance bar
  chart, a colour-coded mono-compatibility indicator
- Dark-by-default theme, monospace numeric readouts, single-column
  under 640px -- per `spec.md`'s stated frontend requirements
- Confirmed the frontend's shared-secret key can safely be embedded in
  the built JS bundle (Vite's `VITE_` prefix convention), explicitly
  distinguishing this from the Claude API key, which must never reach
  frontend code under any circumstance -- same `.env` mechanism,
  opposite treatment, because the two keys protect against different
  threats
- Verified real client-server behaviour directly, not just via
  `TestClient`: ran an actual `uvicorn` process and hit it with `curl`
  carrying a real `Origin` header, confirming the CORS configuration
  works against genuine HTTP, not only Starlette's in-process test
  transport. Needed the sandbox restriction lifted for this one check
  (network access, not filesystem) -- kept fully local, nothing
  destructive or external
- `README.md` rewritten as a technical report: the problem, an
  architecture diagram (Mermaid, renders natively on GitHub), the
  mathematics behind Welch/LUFS/mono-phase with their actual validation
  figures (cross-checked against `CONCEPTS.md` before writing, not
  approximated from memory -- caught and fixed one invented number in
  the process), setup instructions, honest known limitations
- `docs/STAGES.md`: corrected the stale `dynamic_range` mention in
  Stage 8's own "Produces" list (never implemented, same 2026-08-22
  rescope correction as `spec.md`'s data model) while marking it done
- `docs/CONCEPTS.md` and `docs/CODE_GUIDE.md` Stage 8 sections written;
  PDFs regenerated

**Files touched**
- `frontend/` — new (Vite React app)
- `.env.example`, `frontend/.env.example` — env var shapes for a
  stranger to follow
- `README.md` — fully rewritten
- `docs/STAGES.md` — Stage 8 marked done, stale mention corrected
- `docs/CONCEPTS.md`, `docs/CODE_GUIDE.md` — Stage 8 sections added
- (vault) `decisions.md` — one new entry, 2026-09-06

**Decisions**
- Shared-secret key deliberately embedded in the frontend bundle,
  explicitly distinguished from the Claude key's permanent ban from
  frontend code (vault `decisions.md`)

**Concepts explained**
- Why polling needs `useEffect` cleanup to avoid orphaned intervals;
  the `VITE_` prefix convention and why one key gets embedded while
  another never will (both in `CONCEPTS.md` -- not quizzed live, per
  the Stage 6-8 pacing note, which has now run its course)

**In progress / not finished**
- Nothing mid-built. Stage 8 is complete. Tier 1 is functionally done;
  the `v1.0` tag itself is the one remaining action, confirmed with the
  user before creating it (a genuine milestone, not a routine commit)

**Open questions**
- None blocking.

**Exit criteria met?**
- Yes, with one honest exception: "CI green" was never achieved
  literally, since no GitHub remote exists for this repo (deferred
  since Stage 1, by explicit choice each time it came up). Met as "the
  test suite passes locally, in one command," not "in a CI pipeline."
  Everything else: a stranger can clone, install, run, and read a
  README explaining not just what the tool does but why each
  measurement is correct, with real figures shown.

**Next session starts with**
- Nothing, until the user chooses to resume. Per the pacing agreement
  (2026-09-05), a dedicated post-freeze session should properly cover
  theory, syntax, code logic, and system design across everything
  built during the Stage 6-8 stretch, before Tier 2 planning begins in
  mid-October.

---

## Session 13 — 2026-09-06 — Frontend polish; LaTeX notation in CONCEPTS.md

**Done**
- Frontend visual polish pass (custom file picker, icon-badged metric
  cards, a colour-coded pill for the mono score, a spinner for the
  loading state, fixed chart Y-axis headroom) — verified visually via
  the Playwright driver against the live dev servers, committed
  separately before the documentation work below
- Actually ran and drove the full application for the first time:
  built a one-off Playwright driver (`chromium-cli` wasn't available)
  pointed at the system Chrome install, launched both servers, and
  drove a real upload through to completion in a real browser. Numbers
  matched exactly what direct testing produced on the same file weeks
  earlier — a genuine end-to-end consistency check across the whole
  chain, not just each piece in isolation
- Added real LaTeX notation to `CONCEPTS.md`: the continuous and
  discrete Fourier transform (a new subsection -- previously discussed
  the FFT constantly without ever writing the transform down), the
  Nyquist sampling condition and aliasing formula, the periodic Hann
  window and full windowed-periodogram/Welch-averaging formulas, the
  general biquad transfer function, the LUFS formula, the sum-to-product
  identity and energy-loss formula for mono compatibility, and the
  Pearson correlation coefficient behind Krumhansl-Schmuckler key
  detection. Kept deliberately shallow per the ask ("do not delve too
  deep") -- one or two equations per concept, with citations for
  anyone wanting the full derivation (new references: Fourier
  transform, DFT, and Cooley-Tukey FFT algorithm on Wikipedia; Pearson
  correlation coefficient)
- Solved the real problem this created: `xhtml2pdf` has no LaTeX
  rendering at all. `build_pdf.py` now preprocesses `$$...$$` blocks,
  rendering each to a PNG via matplotlib's `mathtext` engine (no full
  LaTeX install available or needed) and embedding it as a base64 data
  URI, while leaving the `.md` source's real LaTeX untouched for
  GitHub/editor rendering
- Installed `poppler` (`brew install poppler`) to actually render PDF
  pages for visual inspection, rather than only extracting text --
  this immediately surfaced a real, previously-undetected bug: several
  pre-existing Unicode superscript characters (`10⁻⁴`, `10⁻⁷`, `10⁻¹⁵`,
  etc.) rendered as missing-glyph boxes in the PDF's font, while plain
  `²` did not. Fixed by switching those to `<sup>` HTML tags, which
  use ordinary digit glyphs. Also fixed a `mathtext`-specific
  positioning bug in the PSD formula (`\left|...\right|^2` mis-places
  the trailing exponent) by restructuring it as one full fraction
  instead
- Full suite still 61/61 (no backend code touched this session)

**Files touched**
- `frontend/src/App.css`, `App.jsx`, `index.css` — visual polish
- `docs/CONCEPTS.md` — LaTeX equations added throughout, two rendering
  bugs fixed, references added
- `docs/build_pdf.py` — LaTeX-to-image preprocessing step
- `docs/requirements-docs.txt` — added `matplotlib`
- (vault) `decisions.md` — two new entries, 2026-09-06

**Decisions**
- Shared-secret key deliberately embedded in the frontend bundle
  (vault `decisions.md`, logged same day as the polish work)
- LaTeX in the `.md` source, rendered to images for the PDF via
  matplotlib's `mathtext`, not a full LaTeX toolchain (vault
  `decisions.md`)

**Concepts explained**
- None new for the project's own theory -- this session added
  notation and fixed rendering, it didn't introduce new DSP concepts

**In progress / not finished**
- Nothing mid-built.

**Open questions**
- None blocking.

**Exit criteria met?**
- N/A -- post-freeze polish and documentation session, no stage exit
  criteria targeted (Tier 1 already frozen at `v1.0`).

**Next session starts with**
- Nothing scheduled. The post-freeze catch-up session (theory, syntax,
  code logic, system design) remains the recommended next step
  whenever the user wants it, before Tier 2 planning in mid-October.

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

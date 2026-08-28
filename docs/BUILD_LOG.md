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

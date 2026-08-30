# STAGES.md — tracklab build plan

Eight stages, roughly two to four hours each. Some stages will take two
sessions — Stage 4 especially, see the note there — and that is fine
and expected.

Do not begin a stage until the previous stage's exit criteria are met.
The exit criteria exist so that we never build on top of something
broken.

**This plan was narrowed from an original fourteen stages on
2026-08-22.** Genre/mood classification and the Claude feedback layer
were cut from Tier 1 and moved to Tier 2, built only after Tier 1 is
frozen. See `CLAUDE.md`'s "What gets implemented from scratch" section
and the vault's `decisions.md` for the full reasoning. The throughline:
implement a DSP component from scratch where there is ground truth to
validate it against (Welch spectral estimation, LUFS loudness,
mono/phase compatibility); call a library where there isn't (BPM, key).

Each stage lists: what it produces, what I need to understand before
moving on, and how we know it works.

---

### Stage 1 — Repo, environment, and CI

**Produces**
- Directory structure, `.gitignore`, `README.md` stub *(done)*
- `backend/.venv` with dependencies installed, `requirements.txt`
  pinned *(done)*
- `git init` and first commits, ffmpeg verified *(done)*
- `pytest` installed and in use *(done, in practice landed during
  Stage 2's work rather than here — the two are close enough in
  spirit that it doesn't need re-doing)*
- GitHub Actions workflow running the test suite on every push, with a
  status badge in `README.md` *(not yet done — needs a GitHub remote
  for tracklab, which doesn't exist yet)*

**I must understand**
- What a virtual environment actually isolates and why it matters
- Why we pin versions in `requirements.txt`
- What is in `.gitignore` and why each entry is there
- What CI actually does: runs the test suite in a clean container on
  every push, catching a regression before it reaches `main` rather
  than after. For the audience this project now targets (RSE, academic
  CDTs), a green CI badge is evidence of discipline independent of
  feature count — worth having before any of the validated DSP stages
  below, not after.

**Exit criteria**
`python -c "import librosa, fastapi, sqlalchemy"` runs clean inside the
venv. `ffmpeg -version` returns a version. A push to the GitHub remote
triggers a CI run and it passes.

---

### Stage 2 — Audio loading and format handling

**Produces**
- `backend/audio/loader.py`: loads any supported format, resamples to
  44.1kHz, returns mono and stereo arrays plus metadata via a
  `LoadedAudio` dataclass
- Format detection, lossy-format flagging
- SHA-256 file hashing for the cache
- `tests/test_loader.py`: pytest suite against synthetic fixtures,
  manually cross-checked against real WAV/MP3 tracks

**I must understand**
- Why we normalise sample rate on load, and what the Nyquist–Shannon
  sampling theorem actually says about why that's not just relabeling
- What `librosa.load` returns and what `sr` and `mono` do
- Why analysing an MP3 for frequency balance is misleading, and what
  the lossy flag is protecting me from
- Why streaming SHA-256 hashing works block-by-block rather than
  needing the whole file in memory (Merkle–Damgård construction)

**Exit criteria**
*(Done, 2026-08-21.)* Load one of my own tracks in WAV and MP3 and get
consistent duration, sample rate, and hash behaviour. M4A untested — no
M4A files were available; logged as a known gap, not blocking.

---

### Stage 3 — Welch spectral estimation, from scratch

This is the first of the three from-scratch components. It's also the
foundation the frequency-balance and mono/phase-compatibility analyses
in later stages are built on, so it comes first.

**Produces**
- `backend/audio/spectral.py`: Welch's method for power spectral
  density estimation, implemented directly — windowing (Hann), segment
  overlap, periodogram averaging — not `scipy.signal.welch`
- A validation test: run the implementation against synthetic signals
  of known spectral content (pure sinusoids, white noise) and compare
  against `scipy.signal.welch` on the same input

**I must understand**
- What a periodogram is, and why a single one is a high-variance,
  unreliable PSD estimate
- Why segmenting the signal, windowing each segment, and averaging
  their periodograms (Welch's method) trades frequency resolution for
  reduced variance
- What a window function (Hann) is doing, and why windowing prevents
  spectral leakage
- Why segments overlap (commonly 50%), and what that buys versus
  non-overlapping segments

**Exit criteria**
*(Done, 2026-08-28.)* Own implementation's PSD estimate agrees with
`scipy.signal.welch`'s output on synthetic sine waves and white noise,
to within `rtol=1e-9` — effectively floating-point-limit agreement, not
just "close." Hann window, 4096-sample segments, 50% overlap.

---

### Stage 4 — LUFS loudness, from scratch (ITU-R BS.1770)

**The load-bearing stage.** ITU-R BS.1770 is a published standard: a
K-weighting filter chain (two cascaded biquad filters), mean-square
power, an absolute gate at −70 LUFS, and a relative gate at −10 LU
below the absolute-gated mean. Implementing it and proving numerical
agreement with independent reference implementations is a genuinely
strong claim — stronger than most of what an undergraduate portfolio
can show. If the calendar tightens, protect this stage's rigour before
cutting into Stage 8's dashboard polish. This may reasonably take two
sessions.

**Produces**
- `backend/audio/loudness.py`: the K-weighting filter chain, mean-square
  calculation, two-stage gating, integrated loudness — all from the
  specification, not a library call
- A validation test: compare integrated loudness against `pyloudnorm`
  and ffmpeg's `ebur128` filter, on both real tracks and synthetic
  signals (including edge cases: near-silence, heavy limiting, a quiet
  ambient passage)

**I must understand**
- What "loudness" means perceptually, and why it differs from RMS and
  peak
- What K-weighting approximates about human frequency sensitivity, and
  what each of the two biquad stages in the ITU-R chain is
  compensating for
- Why gating exists: without it, silence and very quiet passages would
  drag down a track's measured "typical" loudness
- Why streaming platforms standardised on integrated LUFS rather than
  peak or RMS for loudness normalisation

**Exit criteria**
*(Done, 2026-08-28.)* Own implementation agrees with both `pyloudnorm`
and ffmpeg's `ebur128` to within 0.1 LU — exactly, on real tracks
against `pyloudnorm`; within displayed precision against ffmpeg; and
across all three named synthetic edge cases (near-silence, heavy
limiting, a quiet passage). One open gap: implemented against what's
commonly described as BS.1770-**4**'s algorithm (matching
`pyloudnorm`'s own stated target); the current published standard is
BS.1770-**5** (2023), and what changed between them hasn't been
checked.

---

### Stage 5 — Mono compatibility and phase, from scratch

Built directly on Stage 3's Welch PSD estimator: mono compatibility is
measured by comparing per-band energy in the stereo signal against
per-band energy after summing to mono.

**Produces**
- `backend/audio/mono_compat.py`: per-band energy comparison between
  stereo and mono-summed signal, identifying where and how severely
  phase cancellation is occurring
- A validation test: construct a synthetic stereo signal with a known
  phase-inverted component at a known frequency and magnitude, and
  assert the analysis detects it at the correct frequency and severity

**I must understand**
- What phase cancellation is physically: two waveforms inverted or
  delayed relative to each other partially or fully cancel when summed
- Why comparing per-band stereo energy against per-band mono-summed
  energy, using the Stage 3 PSD estimator, reveals exactly where
  cancellation is happening
- The relationship between phase difference (0° to 180°) and the
  resulting energy loss on summing

**Exit criteria**
*(Done, 2026-08-30.)* Given synthetic stereo signals with known
phase-inverted components (0, π/2, and π radians tested), the analysis
correctly identifies the affected frequency band and measures energy
loss matching the theoretical `sin²(φ/2)` prediction to within 1%.

---

### Stage 6 — Track intelligence (librosa) and the database layer

BPM/beat tracking and key/mode detection stay as `librosa` calls —
deliberately, not by default. Beat tracking has no firm ground truth
even for a human listener on syncopated or tempo-varying material, so
the validation bar Stages 3–5 hold themselves to doesn't apply, and
reimplementing it would cost a stage for a claim I couldn't honestly
make.

**Produces**
- BPM and beat grid, key and mode, via `librosa`
- Frequency balance against a genre reference curve, built on Stage 3's
  Welch estimator; low-end (sub vs bass) balance
- `backend/db/models.py`: SQLAlchemy models for `tracks` and `features`
  only (see the vault's `spec.md` — `classifications`, `feedback`, and
  `sections` are Tier 2 tables, not created here)
- `backend/db/session.py`: engine, session factory
- Store and retrieve a full analysis round trip

**I must understand**
- Why BPM and key are library calls when the PSD/loudness/phase
  components next door are not — the ground-truth criterion, stated
  precisely, not just "some DSP is hand-rolled and some isn't"
- What an ORM is doing between Python objects and SQL rows
- What a session is, when it commits, and why sessions are scoped
- Why the audio file itself is not in the database, and why features
  live in a separate table from tracks

**Exit criteria**
Analyse a track using Stages 3–6 together, write it to the database,
read it back, and get identical values.

---

### Stage 7 — FastAPI application and background pipeline

**Produces**
- `backend/main.py`, app factory, CORS for the Vite dev server
- `POST /tracks` — accepts a file, hashes it, returns a job id
  immediately; returns the cached analysis if the hash is known
- `GET /tracks/{id}` — returns analysis or job status
- Background analysis via FastAPI `BackgroundTasks`, job status
  tracking (queued, running, complete, failed)
- A shared-secret access gate: an API key in `.env`, checked via a
  FastAPI dependency on every route, required from both the frontend
  and any CLI/`curl` access
- Integration tests covering the full upload → analyse → retrieve flow,
  running in CI

**I must understand**
- What Pydantic models are validating and why the API defines its
  response shapes explicitly
- What CORS is and why the frontend needs it
- Why upload returns immediately rather than waiting for analysis, and
  why a 30-second analysis can't live inside the request cycle
- Why a single shared secret is the right amount of access control
  here, not full user accounts: the app binds to `0.0.0.0` specifically
  so my phone can reach it over wifi (see `spec.md`, "Devices"), which
  also means anyone else on the same network can reach it. A shared key
  closes that off. It is not multi-user authentication, and shouldn't
  be over-built as if it needed to be — there is one user.

**Exit criteria**
Upload three tracks in quick succession via `/docs`. All three
complete, status transitions are visible throughout, and the
integration test suite passes in CI. A request without the correct API
key is rejected; one with it succeeds.

---

### Stage 8 — Minimal dashboard, README, freeze

**Produces**
- Vite React app: metric cards (BPM, key, LUFS, dynamic range, mono
  score), frequency balance chart, mono compatibility indicator — no
  polish beyond what's needed to show the numbers clearly
- `README.md` rewritten as a short technical report: the problem,
  architecture, and — specifically — the mathematics behind Welch,
  LUFS, and mono/phase, with their validation results shown, not just
  what the tool does
- `.env.example`, setup instructions a stranger could actually follow
- Test suite runnable in one command, CI green
- Git tag `v1.0`

**Exit criteria**
A stranger can clone the repo, run the test suite, run the app, and
read a README that explains not just what the tool measures but why
each measurement is correct. Tag `v1.0` and freeze the repository —
**28 September is a hard stop**, regardless of what remains unbuilt.

---

## Tier 2 and Tier 3 — after Tier 1 is frozen

Not scheduled, and not started before `v1.0` is tagged. In priority
order:

- Genre classification (FMA, scikit-learn) — cut from Tier 1 on
  2026-08-22: a well-trodden exercise with typically mediocre results,
  disproportionate to what it would have cost against a five-week
  deadline. Still worth building for its own sake, just not before the
  freeze.
- Claude-generated production feedback, with focus modes (mix, low
  end, loudness, arrangement) — cut from Tier 1 on 2026-08-22. A good
  feature, reads better as a considered addition to a working, validated
  system than as a headline feature competing with an LLM-integration
  trend everyone is already riding.
- Mood as valence/arousal — cut from Tier 1 on 2026-08-22, and worth
  reconsidering rather than just delaying: it has no ground truth to
  validate against, which is exactly the property that rules out
  hand-rolling it, and equally undermines it as a bolted-on library
  call. Revisit whether it belongs in the project at all before
  building it.
- Section detection: intro, drop, verse, chorus, outro
- Mastering readiness score
- Track library with search and filters
- Progress-over-time charts across the catalogue
- Genre-aware reference curves selected automatically from the
  classification
- Reference track upload and comparison
- EP and project consistency view
- Real-time monitoring from the DAW via a virtual audio device
- Optional stem upload for deeper breakdown

# STAGES.md — tracklab build plan

Fourteen stages. One stage per session, roughly two to four hours each.
Some stages will take two sessions; that is fine and expected.

Do not begin a stage until the previous stage's exit criteria are met.
The exit criteria exist so that we never build on top of something
broken.

Each stage lists: what it produces, what I need to understand before
moving on, and how we know it works.

---

## Phase A — Backend foundation (Stages 1–5)

### Stage 1 — Repo skeleton and environment

**Produces**
- Directory structure, `.gitignore`, `README.md` stub
- `backend/.venv` with dependencies installed
- `requirements.txt` pinned
- `git init` and first commit
- ffmpeg verified present on the system

**I must understand**
- What a virtual environment actually isolates and why it matters
- Why we pin versions in `requirements.txt`
- What is in `.gitignore` and why each entry is there

**Exit criteria**
`python -c "import librosa, fastapi, sqlalchemy"` runs clean inside the
venv. `ffmpeg -version` returns a version.

---

### Stage 2 — Audio loading and format handling

**Produces**
- `backend/audio/loader.py`: loads any supported format, resamples to
  44.1kHz mono and stereo variants, returns a structured object
- Format detection, lossy-format flagging
- SHA-256 file hashing for the cache
- Tests against a WAV, an MP3 and an M4A

**I must understand**
- Why we normalise sample rate on load
- What `librosa.load` returns and what `sr` and `mono` do
- Why analysing an MP3 for frequency balance is misleading, and what
  the lossy flag is protecting me from

**Exit criteria**
Load one of my own tracks in three formats and get consistent duration,
sample rate and hash behaviour.

---

### Stage 3 — Core feature extraction

**Produces**
- `backend/audio/features.py` with one function per feature group:
  - Temporal: BPM, beat grid, onset positions
  - Spectral: centroid, rolloff, bandwidth, band energies
    (sub <60Hz, bass 60–200, low-mid 200–800, mid 800–4k, high >4k)
  - Perceptual: RMS, dynamic range, LUFS
  - Harmonic: chroma, key and mode detection
- Each returns plain Python or NumPy types, ready to serialise

**I must understand**
- What an MFCC actually is and why it is the standard audio fingerprint
- What the spectral centroid measures perceptually
- How LUFS differs from RMS and peak, and why streaming platforms use it
- How key detection from chroma works and where it fails

**Exit criteria**
Run on five of my tracks. BPM and key match what I know to be correct.
Numbers are plausible, not obviously broken.

---

### Stage 4 — Mix translation analysis

This is the stage that solves my actual problem. It is the heart of the
project.

**Produces**
- `backend/audio/translation.py`:
  - Mono compatibility: sum to mono, measure energy loss per band,
    return a 0–100 score and the bands where phase cancellation is worst
  - Low-end analysis: sub versus bass balance, flag imbalance
  - Frequency balance versus a genre reference curve, returning
    deviation in dB per band
  - Loudness targets: measured LUFS against Spotify (−14), Apple (−16)
    and club (−8) references, with the gain adjustment each implies
  - Dynamic range assessment and over-compression flag
- Reference curves stored as data, not hardcoded in logic

**I must understand**
- Why summing to mono reveals phase problems, and what phase
  cancellation is doing physically
- Why sub versus bass balance is the most common translation failure
- What loudness normalisation does to my track on streaming services

**Exit criteria**
Run on a track I know translates badly and a track I know translates
well. The scores should separate them. If they do not, the analysis is
wrong and we fix it before moving on.

---

### Stage 5 — Database layer

**Produces**
- `backend/db/models.py`: SQLAlchemy models for `tracks`, `features`,
  `classifications`, `feedback`
- `backend/db/session.py`: engine, session factory
- Migration or table creation on startup
- Store and retrieve a full analysis round trip

**I must understand**
- What an ORM is doing between my Python objects and SQL rows
- What a session is, when it commits, and why sessions are scoped
- Why the audio file itself is not in the database
- Why features live in a separate table from tracks

**Exit criteria**
Analyse a track, write it to the database, read it back, and get
identical values.

---

## Phase B — API and intelligence (Stages 6–9)

### Stage 6 — FastAPI application and upload endpoint

**Produces**
- `backend/main.py`, app factory, CORS for the Vite dev server
- `POST /tracks` — accepts a file, hashes it, returns a job id
  immediately; returns the cached analysis if the hash is known
- `GET /tracks/{id}` — returns analysis or job status
- Pydantic response models
- Auto-generated docs working at `/docs`

**I must understand**
- What Pydantic models are validating and why the API defines its
  response shapes explicitly
- What CORS is and why the frontend needs it
- Why upload returns immediately rather than waiting for analysis

**Exit criteria**
Upload a track via `/docs`, get a job id, poll it, get an analysis back.

---

### Stage 7 — Background task pipeline

**Produces**
- Background analysis via FastAPI `BackgroundTasks`
- Job status tracking: queued, running, complete, failed
- Progress reporting per stage of the pipeline
- Error handling that records the failure rather than silently dying

**I must understand**
- Why a 30-second analysis cannot live inside an HTTP request
- What happens to a background task if the server restarts, and what
  that means for reliability

**Exit criteria**
Upload three tracks in quick succession. All three complete. Status
transitions are visible throughout.

---

### Stage 8 — Genre and mood classification

**Produces**
- FMA dataset acquisition and preprocessing script
- Feature matrix build from MFCCs plus spectral and rhythmic features
- Genre classifier trained, evaluated, and serialised to disk
- Mood model: valence and arousal regression
- `backend/ml/predict.py` loading the saved models for inference
- Honest accuracy reporting in the README, including confusion matrix

**I must understand**
- Why we output a probability distribution over genres rather than one
  label
- What the confusion matrix tells me about which genres the model
  cannot separate
- Why training accuracy and held-out accuracy differ

**Exit criteria**
Classify ten of my own tracks. The predictions are defensible, and
where the model is wrong I understand why from the confusion matrix.

---

### Stage 9 — Claude feedback layer

**Produces**
- `backend/ai/feedback.py`: builds a structured prompt from the real
  extracted numbers and calls the Claude API
- Prompt template versioned in the repo so I can see it evolve
- Focus modes: mix, low end, loudness, arrangement
- Response stored against the track
- Graceful degradation when the API is unreachable

**I must understand**
- Why grounding the prompt in measured numbers produces specific
  feedback rather than generic advice
- Where the API key lives and why it never reaches the frontend

**Exit criteria**
Feedback on a track says something specific and true that I could act
on. If it reads like generic production advice, the prompt is wrong and
we iterate before moving on.

---

## Phase C — Frontend (Stages 10–13)

### Stage 10 — Frontend scaffold and API client

**Produces**
- Vite React app in `frontend/`
- Dark theme, monospace numerics, responsive breakpoints at 640 and
  1024px
- Typed API client, loading and error states
- Routing: upload, track view, library

**I must understand**
- What Vite is doing in development versus build
- How React state drives what renders

**Exit criteria**
App runs, talks to the backend, shows a track's raw JSON on screen.

---

### Stage 11 — Analysis view

**Produces**
- Waveform display from precomputed peaks
- Spectrogram
- Metric cards: BPM, key, LUFS, dynamic range, mono score
- Frequency balance chart against the genre reference
- Energy map across the timeline
- Green/amber/red status colouring driven by actual thresholds

**I must understand**
- Why we precompute waveform peaks rather than sending raw audio
- How the threshold colouring is defined, so I trust it

**Exit criteria**
Analysis view for one of my tracks tells me something about the mix I
did not already know.

---

### Stage 12 — Library and mood plot

**Produces**
- Track grid with filters: BPM range, key, genre, date, lossy flag
- Sorting by loudness, energy, dynamic range
- Valence–arousal scatter plot of the whole catalogue
- Genre distribution across everything analysed

**Exit criteria**
Twenty of my tracks loaded. Filtering and sorting behave correctly.

---

### Stage 13 — Feedback panel and polish

**Produces**
- Claude feedback rendered alongside the relevant charts
- Regenerate with a different focus area
- Mobile layout verified on my phone over the local network
- Empty states, error states, loading skeletons

**Exit criteria**
Full flow works on desktop and on my phone: upload, wait, read, act.

---

## Phase D — Delivery (Stage 14)

### Stage 14 — Documentation and portfolio readiness

**Produces**
- `README.md` written as a short technical report: problem, approach,
  architecture diagram, methods, model accuracy with confusion matrix,
  screenshots, limitations, what I would do differently
- Setup instructions someone else could actually follow
- `.env.example`
- Test suite runnable in one command
- Clean commit history

**Exit criteria**
I can hand the repo to a stranger and they can run it. I can talk
through every architectural decision unprompted.

---

## Tier 2 and Tier 3 — after Tier 1 is complete

Not scheduled. Do not start these until Stage 14 is done.

- Section detection: intro, drop, verse, chorus, outro
- Mastering readiness score
- Progress-over-time charts across the catalogue
- Reference track comparison
- EP consistency view
- Real-time monitor via BlackHole virtual audio device and websockets
  (this is the macOS equivalent of VB-Cable)

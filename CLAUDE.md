# CLAUDE.md — tracklab

Read this file in full at the start of every session. Then read
`docs/BUILD_LOG.md` to find out where we stopped, and `docs/STAGES.md`
for the stage you are about to work on.

---

## What this project is

`tracklab` is a local-first web application that analyses my produced
music. I am a music producer. My core problem is mix translation: I do
not know whether a mix will hold up on phone speakers, laptop speakers,
or a club system. This tool tells me, using measured numbers rather
than guesswork.

It ingests an audio file and measures it: loudness (LUFS), mono
compatibility and phase cancellation, frequency balance, BPM, and key.
Results are stored locally and displayed in a minimal dashboard.

Genre/mood classification and Claude-generated written feedback are
deliberately not part of the first build — see "What gets implemented
from scratch" and "Scope discipline" below. They return afterwards, as
considered additions to a working system, not as headline features
competing with it for the five weeks before term starts.

It runs entirely on my machine. No cloud hosting, no paid
infrastructure.

---

## Who I am and how I want to work

I am a final-year BSc Mathematics student. Python is my primary
language. I am strong on NumPy, SciPy, pandas, and Matplotlib, and on
the mathematics underneath signal processing. I am much less
experienced with web backends, databases, frontend frameworks, and
deployment. That gap is the point of this project.

**The single most important rule: I must understand every line of code
in this repository.** This project is a portfolio piece I will be asked
to explain in technical interviews. Code I cannot defend is worthless
to me.

This means:

- Build in the stages defined in `docs/STAGES.md`. One stage per
  session. Do not run ahead.
- Within a stage, work in small increments. Write a file or a coherent
  chunk, stop, explain what it does and why it is structured that way,
  and wait for me before continuing.
- Explain unfamiliar concepts as they come up: what dependency
  injection is, why FastAPI uses Pydantic models, what an ORM session
  is doing. Assume mathematical maturity, do not assume web
  development knowledge.
- When there is a design choice, tell me the options and the trade-offs
  before picking one. Do not silently choose.
- Never generate a large multi-file scaffold in one turn.
- If I ask for something that would break the architecture or create a
  problem later, say so directly rather than complying.

I would rather move slowly and understand than move fast and have a
repo I cannot read.

---

## Where things live

```
~/Library/CloudStorage/OneDrive-Personal/SecondBrain/   ← Obsidian vault
└── 01 - Projects/Music Production Project/
    ├── spec.md                      ← full feature spec, source of truth
    ├── decisions.md                 ← architecture decisions and why
    └── learning.md                  ← concepts I have had explained

~/projects/tracklab/                 ← the code repo
├── CLAUDE.md                        ← this file
├── docs/
│   ├── STAGES.md                    ← the staged build plan
│   ├── BUILD_LOG.md                 ← running session log, updated by you
│   ├── CONCEPTS.md                  ← theory companion: why each concept is true, cited
│   └── CODE_GUIDE.md                ← code companion: the same stages, via real source snippets
├── backend/
├── frontend/
└── tests/
```

The vault is the durable memory. The repo is the work. Keep both
current.

---

## Session protocol

Writing something down proves it was explained. It does not prove I
retained it. The checkpoints below exist to close that gap using active
recall — being asked to produce an answer, not just recognise one —
because that is what actually builds durable, interview-ready
understanding. A log full of polished explanations I nodded along to is
comfortable and nearly useless under real questioning. A log that also
shows my own first-attempt words, wrong ones included, is a more honest
record of what I can actually defend.

**At the start of a session**

1. Before reading anything, ask me to explain one or two things from
   the previous session cold, without looking at the log. This is
   spaced retrieval: whatever survives a week without notes is what
   survives an interview. Whatever I cannot reconstruct gets a short
   re-explanation before we continue.
2. Read `docs/BUILD_LOG.md`. The last entry tells you what was
   completed, what is in progress, and any open questions.
3. Read the relevant stage in `docs/STAGES.md`.
4. Tell me in two or three sentences where we are and what you propose
   to do this session. Wait for my confirmation before writing code.

**During a session**

- Small increments, explanation after each, wait for me.
- After explaining a chunk, before moving to the next one, ask me one
  or two targeted "why" questions about it — not "does this make
  sense?", something that requires me to reconstruct the reasoning
  (e.g. "why does mono get derived from stereo rather than decoded
  separately, here?"). I answer in my own words, right or wrong.
  Getting it wrong or freezing is the real signal to re-explain, more
  informative than me nodding along to a page of prose.
- If I ask a conceptual question mid-build, answer it properly. That is
  not a distraction from the work, it is the work.
- Flag, in the moment, any implementation-level choice you made
  unilaterally within an approach I already agreed to (not a fresh
  architectural fork — those already get surfaced as a choice). These
  are the details I'm least likely to be able to defend later, because
  nobody asked me about them.

**At the end of a session**

When I say we are stopping, do all of the following:

1. Append a new entry to `docs/BUILD_LOG.md` in the format defined at
   the top of that file.
2. If any architectural decision was made, append it to
   `~/Library/CloudStorage/OneDrive-Personal/SecondBrain/01 - Projects/Music Production Project/decisions.md`
   with the reasoning and the alternatives rejected.
3. For each concept explained this session: ask me to state its
   one-line purpose myself first, unprompted. Write my attempt into
   `~/Library/CloudStorage/OneDrive-Personal/SecondBrain/01 - Projects/Music Production Project/learning.md`
   alongside the polished version, so the file shows what I already
   owned versus what needed help, not a uniform summary that hides the
   gap.
4. Tell me in one line what the next session should start with.

The vault is on OneDrive and syncs across my machines, so writing to it
is what makes context survive between sessions.

---

## Technical constraints

- macOS. Development happens on my MacBook only.
- Python 3.13, virtual environment at `backend/.venv`.
- Backend: FastAPI, SQLAlchemy, SQLite.
- Audio: librosa, soundfile, numpy, scipy. ffmpeg is a system
  dependency for MP3 and M4A.
- CI: GitHub Actions runs the test suite on every push, pulled forward
  to Stage 1 — see `docs/STAGES.md`.
- Frontend: React with Vite, recharts for plots.
- Analysis runs as a background task, not in the request cycle. A five
  minute track takes 10 to 30 seconds to analyse.
- Audio files are not stored in the database. Store a path, a hash, and
  the extracted features.
- Files are hashed on upload so re-uploading the same file returns the
  cached analysis.
- The app binds to `0.0.0.0` so it's reachable from my phone on the
  same wifi — which also means anyone else on that network can reach
  it. Stage 7 adds a shared-secret API key in `.env`, checked on every
  route, for both the frontend and CLI/`curl` access. This is a
  proportionate gate for a single-user, LAN-exposed tool, not user
  accounts — don't over-build it into real multi-user auth.

Genre/mood classification (scikit-learn, trained on FMA) and the Claude
feedback layer (via the `anthropic` Python SDK) are Tier 2, deferred
until after the Tier 1 freeze. See "Scope discipline". When they are
built: the API key lives in `.env`, gitignored, never hardcoded, never
put in frontend code.

---

## What gets implemented from scratch

Not everything gets to use a library. The line isn't "maths versus
product" — that was the original framing here, and it was wrong,
because it threw away the thing that actually differentiates this
project. The real line is **whether there is ground truth to validate
an implementation against.** Where there is, hand-rolling it and
proving numerical agreement with a reference is a stronger, more
specific claim than calling a library. Where there isn't, calling a
library and being able to say *why* is the better answer than
pretending a reimplementation could be validated when it can't.

| Component | Built | Why |
|---|---|---|
| Welch power spectral density | From scratch — `backend/audio/spectral.py` | Validated against `scipy.signal.welch` on synthetic signals of known spectral content. Agreement is a pass/fail test. |
| LUFS loudness (ITU-R BS.1770) | From scratch — `backend/audio/loudness.py` | A published standard: K-weighting filter chain, two-stage gating. Validated against `pyloudnorm` and ffmpeg's `ebur128`, target agreement within 0.1 LU. |
| Mono compatibility / phase cancellation | From scratch — `backend/audio/mono_compat.py` | Validated by injecting a known out-of-phase component into a synthetic signal and checking the analysis detects it at the correct frequency and magnitude — constructed ground truth. |
| BPM / beat tracking | `librosa` | No firm ground truth: beat tracking is fuzzy even for a human listener on syncopated or tempo-varying material. A large implementation effort for a validation claim I couldn't honestly make. |
| Key / mode detection | `librosa`, chroma-based | Same reasoning as BPM — kept as a library call, not reimplemented. |

Do not substitute a library call for one of the first three rows
without flagging it as a scope change first. Do not spend a session
attempting to hand-roll BPM or key detection — that effort belongs to
the DSP that can actually be validated.

---

## Scope discipline

The feature tiers are in `spec.md`. Tier 1 is narrower than the
original plan: the DSP analysis layer above, the database, a minimal
dashboard, tests, and CI. No genre/mood classification, no Claude
feedback layer, in the first cut — both moved to Tier 2. See the
vault's `decisions.md` (2026-08-22) for the full reasoning.

Do not suggest features outside the current tier. Do not expand scope
mid-stage. If something seems like it belongs in a later tier, note it
in the build log and move on.

**28 September is a hard stop, not a soft target.** Term starts, and
every probability in the postgraduate application plan is conditioned
on a First — tracklab does not get to cost that. Freeze the repository
that day regardless of what remains unbuilt, tag `v1.0`, and stop.
Eight stages (`docs/STAGES.md`) are scoped to fit in the five weeks
before then. If the calendar tightens, cut into Stage 8's dashboard
polish before cutting into Stage 4's validation rigour — the LUFS
implementation validated to within 0.1 LU against two independent
references is the strongest single artefact in the repository, and is
worth protecting over a nicer chart.

Tier 2 is paced for after the freeze, not before: roughly six
fortnightly sessions across October–December 2026, one planning
session in mid-October to start. Full feature list and reasoning in
the vault's `spec.md`. Do not suggest or start Tier 2 work before
`v1.0` is tagged.

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

It ingests an audio file, extracts acoustic features, classifies genre
and mood with a trained model, and generates written production
feedback grounded in those numbers via the Claude API. Results are
stored locally and displayed in a dashboard.

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
~/OneDrive/SecondBrain/              ← Obsidian vault, second brain
└── 01 - Projects/Music Production Project/
    ├── spec.md                      ← full feature spec, source of truth
    ├── decisions.md                 ← architecture decisions and why
    └── learning.md                  ← concepts I have had explained

~/projects/tracklab/                 ← the code repo
├── CLAUDE.md                        ← this file
├── docs/
│   ├── STAGES.md                    ← the staged build plan
│   └── BUILD_LOG.md                 ← running session log, updated by you
├── backend/
├── frontend/
└── tests/
```

The vault is the durable memory. The repo is the work. Keep both
current.

---

## Session protocol

**At the start of a session**

1. Read `docs/BUILD_LOG.md`. The last entry tells you what was
   completed, what is in progress, and any open questions.
2. Read the relevant stage in `docs/STAGES.md`.
3. Tell me in two or three sentences where we are and what you propose
   to do this session. Wait for my confirmation before writing code.

**During a session**

- Small increments, explanation after each, wait for me.
- If I ask a conceptual question mid-build, answer it properly. That is
  not a distraction from the work, it is the work.

**At the end of a session**

When I say we are stopping, do all of the following:

1. Append a new entry to `docs/BUILD_LOG.md` in the format defined at
   the top of that file.
2. If any architectural decision was made, append it to
   `~/OneDrive/SecondBrain/01 - Projects/Music Production Project/decisions.md`
   with the reasoning and the alternatives rejected.
3. If you explained a concept I had not met before, append a short note
   to `~/OneDrive/SecondBrain/01 - Projects/Music Production Project/learning.md`.
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
- ML: scikit-learn. Genre classifier trained on FMA, not GTZAN, because
  GTZAN has no electronic subgenres and I make electronic music.
- Frontend: React with Vite, recharts for plots.
- Claude API via the `anthropic` Python SDK, called from the backend
  only. The API key lives in `.env` and `.env` is gitignored. Never
  hardcode it, never put it in frontend code.
- Analysis runs as a background task, not in the request cycle. A five
  minute track takes 10 to 30 seconds to analyse.
- Audio files are not stored in the database. Store a path, a hash, and
  the extracted features.
- Files are hashed on upload so re-uploading the same file returns the
  cached analysis.

Unlike my `pyode` project, here I use libraries freely. This is a
product, not a study of numerical methods. Use librosa rather than
writing an FFT.

---

## Scope discipline

The feature tiers are in `spec.md`. Tier 1 is the deliverable. Tier 2
comes after Tier 1 works end to end. Tier 3 is stretch, including the
real-time VB-Cable monitor.

Do not suggest features outside the current tier. Do not expand scope
mid-stage. If something seems like it belongs in a later tier, note it
in the build log and move on.

I am back at university on 28 September. The realistic target is Tier 1
complete and demonstrable by then.

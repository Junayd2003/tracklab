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
- Git has no global `user.name`/`user.email` configured, so commits
  are attributed to an auto-generated `junaydsmac@Mac.lan` identity.
  Worth setting explicitly before this goes any further.
- Default branch is `master`, not `main`. Harmless, but easier to
  rename now than later.

**Exit criteria met?**
- Yes. `python -c "import librosa, fastapi, sqlalchemy"` runs clean in
  the venv; `ffmpeg -version` returns a version.

**Next session starts with**
- Stage 2: `backend/audio/loader.py` — format loading, resampling to
  44.1kHz, lossy-format flagging, SHA-256 hashing.

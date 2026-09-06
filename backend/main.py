"""FastAPI application: upload, background analysis, retrieval.

Bound to 0.0.0.0 (see CLAUDE.md) so it's reachable from a phone on the
same wifi -- which is also why every route requires the shared-secret
API key below. Not multi-user auth; a proportionate gate for a
single-user, LAN-exposed tool (decisions.md, 2026-08-23).
"""

import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.audio.loader import hash_file, is_lossy
from backend.db.models import Track
from backend.db.session import SessionLocal, init_db
from backend.pipeline import analyse_and_store
from backend.schemas import FeaturesResponse, FrequencyBalanceResponse, TrackResponse, UploadResponse

load_dotenv()
API_KEY = os.environ["API_KEY"]

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"

# Overridable module attribute, not a hardcoded reference -- both
# get_db() (via FastAPI's dependency injection) and the background
# task (called directly, outside that injection) read this at call
# time, so tests can swap in an isolated in-memory factory for both by
# reassigning this one name (see tests/test_main.py).
session_factory = SessionLocal

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="tracklab", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # Header(default=None), not Header(...): a genuinely missing header
    # with a *required* Header() fails FastAPI's own request validation
    # first, returning 422 before this function ever runs. Making it
    # optional here and checking None explicitly means both "missing"
    # and "wrong" key consistently return 401, the correct status for
    # an authentication failure either way.
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_db():
    with session_factory() as session:
        yield session


@app.post("/tracks", response_model=UploadResponse, dependencies=[Depends(require_api_key)])
def upload_track(
    file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> UploadResponse:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_hash = hash_file(dest)

    # Cache hit: same file already uploaded (any status). Discard the
    # duplicate copy just written to disk and return the existing
    # record rather than re-queuing analysis.
    existing = db.query(Track).filter_by(file_hash=file_hash).first()
    if existing is not None:
        dest.unlink()
        return UploadResponse(id=existing.id, status=existing.status)

    # Only cheap, non-decoding metadata here -- format and is_lossy
    # come from the extension alone. sample_rate/duration need
    # librosa.load(), which is exactly the work Stage 7 keeps out of
    # the request cycle; the background task fills those in.
    track = Track(
        filename=file.filename,
        file_hash=file_hash,
        format=dest.suffix.lower(),
        is_lossy=is_lossy(dest),
        status="queued",
    )
    db.add(track)
    db.commit()

    background_tasks.add_task(analyse_and_store, track.id, dest, session_factory)

    return UploadResponse(id=track.id, status=track.status)


@app.get("/tracks/{track_id}", response_model=TrackResponse, dependencies=[Depends(require_api_key)])
def get_track(track_id: int, db: Session = Depends(get_db)) -> TrackResponse:
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    features_response = None
    if track.status == "complete" and track.features is not None:
        f = track.features
        features_response = FeaturesResponse(
            bpm=f.bpm,
            key=f.key,
            mode=f.mode,
            lufs=f.lufs,
            mono_score=f.mono_score,
            mono_worst_band=f.mono_worst_band,
            frequency_balance=FrequencyBalanceResponse(
                sub=f.freq_sub_db,
                bass=f.freq_bass_db,
                low_mid=f.freq_low_mid_db,
                mid=f.freq_mid_db,
                high=f.freq_high_db,
            ),
        )

    return TrackResponse(
        id=track.id,
        filename=track.filename,
        status=track.status,
        error=track.error_message,
        features=features_response,
    )

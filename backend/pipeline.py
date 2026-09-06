"""Ties Stages 3-6 together into one analysis run, and runs as a
FastAPI background task (Stage 7) -- not inside the request cycle,
since a full decode-and-analyse pass is exactly the kind of work that
can't live inside an HTTP response (see CONCEPTS.md, Stage 7).
"""

from pathlib import Path

from backend.audio.frequency_balance import frequency_balance
from backend.audio.intelligence import detect_bpm, detect_key
from backend.audio.loader import load_audio
from backend.audio.loudness import integrated_loudness
from backend.audio.mono_compat import mono_compatibility
from backend.db.models import Features, Track
from backend.db.session import SessionLocal


def analyse_and_store(track_id: int, path: Path, session_factory=SessionLocal) -> None:
    """Run the full Stage 3-6 analysis pipeline and store the result.

    Opens its own session rather than reusing the one that handled the
    HTTP request: that session is closed by the time this function
    runs (the request has already returned), and a Session is meant
    for one unit of work at a time, not shared across a request and a
    background task running after it (CONCEPTS.md, Stage 6).

    `session_factory` defaults to the real, production `SessionLocal`,
    but is a plain parameter (not hardcoded) so tests can pass an
    isolated in-memory factory instead -- this function is called
    directly by `main.py`'s background task, not through FastAPI's
    dependency injection, so `app.dependency_overrides` alone can't
    reach it the way it reaches the request-handling endpoints.
    """
    with session_factory() as session:
        track = session.get(Track, track_id)
        track.status = "running"
        session.commit()

        try:
            audio = load_audio(path)

            bpm = detect_bpm(audio.mono, audio.sample_rate)
            key, mode = detect_key(audio.mono, audio.sample_rate)
            lufs = integrated_loudness(audio.stereo, audio.sample_rate)
            mono_report = mono_compatibility(audio.stereo, audio.sample_rate)
            balance = frequency_balance(audio.mono, audio.sample_rate)

            track.sample_rate = audio.sample_rate
            track.duration = audio.duration
            track.features = Features(
                bpm=bpm,
                key=key,
                mode=mode,
                lufs=lufs,
                mono_score=mono_report.score,
                mono_worst_band=mono_report.worst_band,
                freq_sub_db=balance["sub"],
                freq_bass_db=balance["bass"],
                freq_low_mid_db=balance["low_mid"],
                freq_mid_db=balance["mid"],
                freq_high_db=balance["high"],
            )
            track.status = "complete"

        except Exception as exc:
            track.status = "failed"
            track.error_message = str(exc)

        session.commit()

"""Tests for backend.db.models / session.

Uses a fresh in-memory SQLite engine per test, not the real
tracklab.db file -- fully isolated, no cleanup needed, and never at
risk of touching real data.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.audio.frequency_balance import frequency_balance
from backend.audio.intelligence import detect_bpm, detect_key
from backend.audio.loader import load_audio
from backend.audio.loudness import integrated_loudness
from backend.audio.mono_compat import mono_compatibility
from backend.db.models import Base, Features, Track

SAMPLE_TRACK = Path("data/samples/PS Cmin 160 24.wav")


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_track_and_features_round_trip(session_factory):
    with session_factory() as session:
        track = Track(
            filename="example.wav",
            file_hash="a" * 64,
            format=".wav",
            sample_rate=44100,
            duration=123.4,
            is_lossy=False,
        )
        track.features = Features(
            bpm=128.0,
            key="C",
            mode="major",
            lufs=-14.2,
            mono_score=92.5,
            mono_worst_band="bass",
            freq_sub_db=-40.0,
            freq_bass_db=-10.0,
            freq_low_mid_db=-2.0,
            freq_mid_db=-1.0,
            freq_high_db=-15.0,
        )
        session.add(track)
        session.commit()
        track_id = track.id

    # Fresh session -- forces an actual read from the database, not
    # just returning the same in-memory Python object.
    with session_factory() as session:
        fetched = session.get(Track, track_id)
        assert fetched is not None
        assert fetched.filename == "example.wav"
        assert fetched.file_hash == "a" * 64
        assert fetched.is_lossy is False
        assert fetched.features.bpm == 128.0
        assert fetched.features.key == "C"
        assert fetched.features.mono_worst_band == "bass"
        assert fetched.features.freq_sub_db == -40.0


def test_file_hash_must_be_unique(session_factory):
    with session_factory() as session:
        session.add(
            Track(
                filename="a.wav", file_hash="dup", format=".wav",
                sample_rate=44100, duration=1.0, is_lossy=False,
            )
        )
        session.commit()

        session.add(
            Track(
                filename="b.wav", file_hash="dup", format=".wav",
                sample_rate=44100, duration=1.0, is_lossy=False,
            )
        )
        with pytest.raises(Exception):  # sqlalchemy.exc.IntegrityError
            session.commit()


@pytest.mark.skipif(not SAMPLE_TRACK.exists(), reason="personal sample track not present")
def test_full_pipeline_round_trip_on_a_real_track(session_factory):
    """Stage 6's actual exit criterion: analyse a track using Stages
    3-6 together, write it to the database, read it back, and get
    identical values."""
    audio = load_audio(SAMPLE_TRACK)

    bpm = detect_bpm(audio.mono, audio.sample_rate)
    key, mode = detect_key(audio.mono, audio.sample_rate)
    lufs = integrated_loudness(audio.stereo, audio.sample_rate)
    mono_report = mono_compatibility(audio.stereo, audio.sample_rate)
    balance = frequency_balance(audio.mono, audio.sample_rate)

    with session_factory() as session:
        track = Track(
            filename=SAMPLE_TRACK.name,
            file_hash=audio.file_hash,
            format=audio.format,
            sample_rate=audio.sample_rate,
            duration=audio.duration,
            is_lossy=audio.is_lossy,
        )
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
        session.add(track)
        session.commit()
        track_id = track.id

    with session_factory() as session:
        fetched = session.get(Track, track_id)
        assert fetched.file_hash == audio.file_hash
        assert fetched.duration == audio.duration
        assert fetched.features.bpm == bpm
        assert fetched.features.key == key
        assert fetched.features.mode == mode
        assert fetched.features.lufs == lufs
        assert fetched.features.mono_score == mono_report.score
        assert fetched.features.freq_mid_db == balance["mid"]

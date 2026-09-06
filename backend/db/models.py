"""SQLAlchemy models: tracks and features -- Tier 1 only.

`classifications`, `feedback`, and `sections` are Tier 2 tables
(genre/mood, Claude feedback, section detection) and aren't created
here -- see the vault's spec.md.

Field names below match what backend/audio actually produces, not the
original pre-rescope plan: no `dynamic_range` or `spectral_centroid`
(never implemented, cut in the 2026-08-22 rescope), and frequency
balance has five bands (sub/bass/low_mid/mid/high, see spectral.py's
BAND_RANGES), not the original four.
"""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    format: Mapped[str]
    is_lossy: Mapped[bool]
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Only known once the file is actually decoded -- format and
    # is_lossy come free from the filename/extension, but sample_rate
    # and duration need librosa.load() to run, which is exactly the
    # decode work Stage 7 keeps out of the request cycle (see main.py).
    # Set by the background task once analysis completes.
    sample_rate: Mapped[int | None] = mapped_column(default=None)
    duration: Mapped[float | None] = mapped_column(default=None)

    # Stage 7: a Track row is created immediately on upload, before
    # analysis runs -- "queued" | "running" | "complete" | "failed".
    # error_message is set only when status == "failed".
    status: Mapped[str] = mapped_column(default="queued")
    error_message: Mapped[str | None] = mapped_column(default=None)

    # No related Features row until analysis completes, hence Optional
    # -- uselist=False already makes this a single object (or None),
    # not a list; the type hint just makes the "or None" explicit.
    features: Mapped["Features | None"] = relationship(
        back_populates="track", uselist=False, cascade="all, delete-orphan"
    )


class Features(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), unique=True)

    # Track intelligence (backend/audio/intelligence.py)
    bpm: Mapped[float]
    key: Mapped[str]
    mode: Mapped[str]

    # Loudness (backend/audio/loudness.py)
    lufs: Mapped[float]

    # Mono compatibility (backend/audio/mono_compat.py)
    mono_score: Mapped[float]
    mono_worst_band: Mapped[str]

    # Frequency balance, dB relative to total energy per band
    # (backend/audio/frequency_balance.py)
    freq_sub_db: Mapped[float]
    freq_bass_db: Mapped[float]
    freq_low_mid_db: Mapped[float]
    freq_mid_db: Mapped[float]
    freq_high_db: Mapped[float]

    track: Mapped["Track"] = relationship(back_populates="features")

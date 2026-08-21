"""Audio file loading: format detection, hashing, resampling."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

TARGET_SAMPLE_RATE = 44_100

# Formats we can decode natively via libsndfile (through soundfile/librosa),
# with no lossy compression in the pipeline before we ever see the samples.
LOSSLESS_FORMATS = {".wav", ".flac", ".aiff", ".aif"}

# Formats decoded via ffmpeg, which have already thrown away information
# (typically high-frequency content) during their original encoding.
LOSSY_FORMATS = {".mp3", ".m4a", ".aac", ".mp4", ".ogg"}

SUPPORTED_FORMATS = LOSSLESS_FORMATS | LOSSY_FORMATS


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at `path`.

    Read in fixed-size chunks rather than `path.read_bytes()` so a large
    WAV doesn't have to be pulled into memory all at once just to hash it.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_lossy(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported audio format: {suffix}")
    return suffix in LOSSY_FORMATS


@dataclass
class LoadedAudio:
    mono: np.ndarray  # shape (n_samples,)
    stereo: np.ndarray  # shape (2, n_samples), channel 0 = left, 1 = right
    sample_rate: int
    duration: float
    is_lossy: bool
    file_hash: str
    format: str  # file extension, e.g. ".mp3"


def load_audio(path: Path) -> LoadedAudio:
    """Load an audio file, resampled to 44.1kHz, as mono and stereo arrays.

    Decodes the file once as stereo and derives the mono downmix ourselves
    by averaging the two channels, rather than asking librosa to decode
    twice with `mono=True` and `mono=False` separately. This matters beyond
    just avoiding double decode work: Stage 4's mono-compatibility analysis
    needs to know that `mono` is exactly the sum of `stereo`'s two channels,
    since that sum is what reveals phase cancellation.
    """
    path = Path(path)
    lossy = is_lossy(path)  # also validates the format is supported

    y, sr = librosa.load(path, sr=TARGET_SAMPLE_RATE, mono=False)

    if y.ndim == 1:
        # Source file only had one channel. Duplicate it so `stereo` always
        # has a consistent (2, n_samples) shape for downstream code.
        stereo = np.stack([y, y])
        mono = y
    else:
        stereo = y
        mono = stereo.mean(axis=0)

    sr = int(sr)
    duration = stereo.shape[1] / sr

    return LoadedAudio(
        mono=mono,
        stereo=stereo,
        sample_rate=sr,
        duration=duration,
        is_lossy=lossy,
        file_hash=hash_file(path),
        format=path.suffix.lower(),
    )

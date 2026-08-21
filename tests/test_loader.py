"""Tests for backend.audio.loader.

Uses synthetically generated sine waves rather than real tracks, so the
suite is fully reproducible for anyone who clones the repo without our
personal audio in data/samples/.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.audio.loader import TARGET_SAMPLE_RATE, hash_file, is_lossy, load_audio

SOURCE_SAMPLE_RATE = 22_050  # deliberately not 44100, to exercise resampling
DURATION_SECONDS = 2.0


def _sine(freq_hz: float, n_samples: int, sr: int) -> np.ndarray:
    t = np.arange(n_samples) / sr
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


@pytest.fixture
def stereo_wav(tmp_path: Path) -> Path:
    """A 2-second stereo WAV with different tones per channel, at 22.05kHz."""
    n = int(SOURCE_SAMPLE_RATE * DURATION_SECONDS)
    left = _sine(440.0, n, SOURCE_SAMPLE_RATE)
    right = _sine(880.0, n, SOURCE_SAMPLE_RATE)
    path = tmp_path / "stereo.wav"
    sf.write(path, np.stack([left, right], axis=1), SOURCE_SAMPLE_RATE)
    return path


@pytest.fixture
def mono_wav(tmp_path: Path) -> Path:
    """A 2-second mono WAV at 22.05kHz."""
    n = int(SOURCE_SAMPLE_RATE * DURATION_SECONDS)
    path = tmp_path / "mono.wav"
    sf.write(path, _sine(440.0, n, SOURCE_SAMPLE_RATE), SOURCE_SAMPLE_RATE)
    return path


def test_hash_file_is_deterministic(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"some fixed content")
    assert hash_file(path) == hash_file(path)


def test_hash_file_differs_for_different_content(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"content one")
    b.write_bytes(b"content two")
    assert hash_file(a) != hash_file(b)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("track.wav", False),
        ("track.flac", False),
        ("track.aiff", False),
        ("track.mp3", True),
        ("track.m4a", True),
        ("TRACK.MP3", True),  # extension check is case-insensitive
    ],
)
def test_is_lossy_by_extension(filename, expected):
    assert is_lossy(Path(filename)) is expected


def test_is_lossy_rejects_unsupported_format():
    with pytest.raises(ValueError):
        is_lossy(Path("track.xyz"))


def test_load_audio_resamples_to_target_rate(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert audio.sample_rate == TARGET_SAMPLE_RATE


def test_load_audio_duration_is_preserved_after_resampling(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert audio.duration == pytest.approx(DURATION_SECONDS, abs=0.01)


def test_load_audio_stereo_shape(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert audio.stereo.shape[0] == 2
    assert audio.mono.shape[0] == audio.stereo.shape[1]


def test_load_audio_mono_is_average_of_channels(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert np.allclose(audio.mono, audio.stereo.mean(axis=0))


def test_load_audio_mono_source_gets_duplicated_stereo(mono_wav: Path):
    audio = load_audio(mono_wav)
    assert audio.stereo.shape[0] == 2
    assert np.array_equal(audio.stereo[0], audio.stereo[1])
    assert np.array_equal(audio.mono, audio.stereo[0])


def test_load_audio_lossless_wav_is_not_flagged_lossy(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert audio.is_lossy is False


def test_load_audio_hash_matches_standalone_hash_file(stereo_wav: Path):
    audio = load_audio(stereo_wav)
    assert audio.file_hash == hash_file(stereo_wav)

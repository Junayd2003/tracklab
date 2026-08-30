"""Validate the from-scratch LUFS implementation against pyloudnorm and
ffmpeg's ebur128 filter.

Uses synthetic signals only, for the same reason test_spectral.py does:
a test suite depending on personal audio in data/samples/ wouldn't run
for a stranger cloning the repo. Real-track agreement (against both
references, on data/samples/) was checked manually and is recorded in
BUILD_LOG.md rather than the automated suite.
"""

import shutil
import subprocess

import numpy as np
import pyloudnorm as pyln
import pytest
import soundfile as sf

from backend.audio.loudness import integrated_loudness

FS = 44_100

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _sine_stereo(freq_hz: float, duration_s: float, amplitude: float = 0.5, fs: int = FS) -> np.ndarray:
    t = np.arange(int(fs * duration_s)) / fs
    mono = amplitude * np.sin(2 * np.pi * freq_hz * t)
    return np.stack([mono, mono])


def _pyloudnorm_reference(stereo: np.ndarray, fs: int) -> float:
    meter = pyln.Meter(fs)
    return meter.integrated_loudness(stereo.T)  # pyloudnorm wants (samples, channels)


def _ffmpeg_ebur128_reference(stereo: np.ndarray, fs: int, tmp_path) -> float:
    wav_path = tmp_path / "signal.wav"
    sf.write(wav_path, stereo.T, fs)

    result = subprocess.run(
        ["ffmpeg", "-i", str(wav_path), "-filter_complex", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in result.stderr.splitlines():
        if line.strip().startswith("I:"):
            return float(line.split()[1])
    raise RuntimeError("could not find integrated loudness in ffmpeg output")


def test_matches_pyloudnorm_on_sine():
    signal = _sine_stereo(1000.0, duration_s=3.0)
    mine = integrated_loudness(signal, FS)
    reference = _pyloudnorm_reference(signal, FS)
    assert mine == pytest.approx(reference, abs=0.1)


def test_matches_pyloudnorm_on_white_noise():
    rng = np.random.default_rng(42)
    mono = 0.3 * rng.standard_normal(FS * 3)
    signal = np.stack([mono, mono])

    mine = integrated_loudness(signal, FS)
    reference = _pyloudnorm_reference(signal, FS)
    assert mine == pytest.approx(reference, abs=0.1)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not found on PATH")
def test_matches_ffmpeg_ebur128_on_sine(tmp_path):
    signal = _sine_stereo(1000.0, duration_s=3.0)
    mine = integrated_loudness(signal, FS)
    reference = _ffmpeg_ebur128_reference(signal, FS, tmp_path)
    assert mine == pytest.approx(reference, abs=0.1)


def test_absolute_gate_matches_pyloudnorm_with_leading_silence():
    # Ten seconds of near-silence followed by five seconds of a tone.
    # Comparing against a separately-computed "tone alone" measurement
    # turned out to be the wrong check: one block straddles the
    # silence/tone boundary and isn't cleanly gated out, and the filter
    # has a brief transient right at that discontinuity -- both real,
    # correct behaviour (confirmed to match pyloudnorm exactly on this
    # same signal), not something a from-scratch bug introduced. Real
    # audio doesn't jump from near-zero to full amplitude instantly, so
    # this edge case is about the gate's logic being right, checked
    # against the reference on the same signal -- not about matching an
    # unrelated comparison signal.
    silence = 1e-6 * np.ones(FS * 10)
    tone = _sine_stereo(1000.0, duration_s=5.0)[0]
    mono = np.concatenate([silence, tone])
    signal = np.stack([mono, mono])

    mine = integrated_loudness(signal, FS)
    reference = _pyloudnorm_reference(signal, FS)
    assert mine == pytest.approx(reference, abs=0.1)


def test_relative_gate_ignores_quiet_passage():
    # A loud section followed by a much quieter one. The relative gate
    # should exclude the quiet passage, so the measured loudness stays
    # close to the loud section's own level -- not pulled down by
    # material a listener wouldn't judge the track's "loudness" by.
    loud = _sine_stereo(1000.0, duration_s=8.0, amplitude=0.5)[0]
    quiet = _sine_stereo(1000.0, duration_s=8.0, amplitude=0.02)[0]
    mono = np.concatenate([loud, quiet])
    signal = np.stack([mono, mono])

    mine = integrated_loudness(signal, FS)
    loud_only = integrated_loudness(_sine_stereo(1000.0, duration_s=8.0, amplitude=0.5), FS)
    assert mine == pytest.approx(loud_only, abs=0.5)


def test_matches_pyloudnorm_on_heavily_limited_signal():
    # A hard-clipped sine -- close to a square wave, the kind of low
    # crest factor a heavily limited/over-compressed master produces.
    # Nothing in the gating logic assumes a comfortable crest factor,
    # but worth checking explicitly since it's named in STAGES.md's
    # exit criteria, not just inferred to be fine.
    raw = _sine_stereo(1000.0, duration_s=3.0, amplitude=2.0)
    clipped = np.clip(raw, -1.0, 1.0)

    mine = integrated_loudness(clipped, FS)
    reference = _pyloudnorm_reference(clipped, FS)
    assert mine == pytest.approx(reference, abs=0.1)


def test_raises_on_signal_shorter_than_one_block():
    too_short = np.zeros((2, int(FS * 0.1)))  # 100ms, block is 400ms
    with pytest.raises(ValueError):
        integrated_loudness(too_short, FS)

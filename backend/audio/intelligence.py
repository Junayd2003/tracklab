"""BPM and key/mode detection via librosa.

Kept as library calls, not implemented and validated from scratch like
Stages 3-5: beat tracking and key detection have no firm ground truth
even for a human listener on syncopated or ambiguous material, so the
same rigour bar doesn't apply here (see decisions.md, 2026-08-22).
"""

import librosa
import numpy as np

# Krumhansl-Kessler (1982) key profiles: mean listener ratings of how
# well each of the 12 chromatic pitch classes fits a given tonic,
# gathered from probe-tone perceptual experiments.
# DOI: 10.1037/0033-295X.89.4.334
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_bpm(mono: np.ndarray, fs: int) -> float:
    """Estimate tempo in BPM via librosa's beat tracker."""
    tempo, _ = librosa.beat.beat_track(y=mono, sr=fs)
    return float(tempo[0])


def detect_key(mono: np.ndarray, fs: int) -> tuple[str, str]:
    """Estimate musical key and mode via the Krumhansl-Schmuckler algorithm.

    Averages a chroma representation over the whole track into one
    12-dimensional vector (chroma[0] = C, per librosa's default
    convention), then correlates it against all 24 rotations of the
    major/minor Krumhansl-Kessler profiles -- one rotation per possible
    tonic. `np.roll(profile, i)` shifts the profile so index j holds
    the fit rating for the pitch class i semitones below it, which is
    exactly the rating for pitch class j when the tonic is pitch class
    i. The best-correlating (tonic, mode) pair is the detected key.
    """
    chroma = librosa.feature.chroma_cqt(y=mono, sr=fs)
    chroma_mean = chroma.mean(axis=1)

    best_key, best_mode, best_corr = _PITCH_CLASSES[0], "major", -np.inf
    for i in range(12):
        major_corr = np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, i))[0, 1]
        minor_corr = np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, i))[0, 1]

        if major_corr > best_corr:
            best_corr, best_key, best_mode = major_corr, _PITCH_CLASSES[i], "major"
        if minor_corr > best_corr:
            best_corr, best_key, best_mode = minor_corr, _PITCH_CLASSES[i], "minor"

    return best_key, best_mode

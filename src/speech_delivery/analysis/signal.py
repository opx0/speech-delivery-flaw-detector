"""The signal stage: transcript timing followed by speaker-normalised acoustics."""

from ..audio import Audio
from .align import align
from .features import extract_features
from .recording import Recording


def analyze_signal(audio: Audio, transcript: str) -> Recording:
    alignment = align(audio, transcript)
    return Recording(alignment=alignment, features=extract_features(audio, alignment))

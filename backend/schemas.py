"""Pydantic response models: the API's response shapes, validated at
serialisation time -- not just documentation, unlike a plain dict."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: int
    status: str


class FrequencyBalanceResponse(BaseModel):
    sub: float
    bass: float
    low_mid: float
    mid: float
    high: float


class FeaturesResponse(BaseModel):
    bpm: float
    key: str
    mode: str
    lufs: float
    mono_score: float
    mono_worst_band: str
    frequency_balance: FrequencyBalanceResponse


class TrackResponse(BaseModel):
    id: int
    filename: str
    status: str
    error: str | None = None
    features: FeaturesResponse | None = None

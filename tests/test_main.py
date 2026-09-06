"""Integration tests for the FastAPI app: upload, background analysis,
retrieval, and the shared-secret gate.

Uses an isolated in-memory database (StaticPool + check_same_thread=False,
since TestClient dispatches through a different thread than the one
that creates the tables -- a plain ":memory:" engine would otherwise
give each thread its own, separately empty, database) and synthetic
audio fixtures, for the same reproducibility reasons as every other
stage's tests.
"""

import shutil

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.main as main
from backend.db.models import Base

FS = 44_100


def _write_wav(path, freq_hz: float, duration_s: float = 3.0):
    t = np.arange(int(FS * duration_s)) / FS
    left = np.sin(2 * np.pi * freq_hz * t)
    right = np.sin(2 * np.pi * freq_hz * t)
    sf.write(path, np.stack([left, right], axis=1), FS)


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(main, "session_factory", sessionmaker(bind=test_engine))
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path / "uploads")

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": main.API_KEY}


@pytest.fixture
def sample_wav(tmp_path):
    path = tmp_path / "sample.wav"
    _write_wav(path, 440.0)
    return path


def _upload(client, headers, path, filename=None):
    with open(path, "rb") as f:
        return client.post(
            "/tracks", files={"file": (filename or path.name, f, "audio/wav")}, headers=headers
        )


def test_upload_without_api_key_is_rejected(client, sample_wav):
    r = _upload(client, {}, sample_wav)
    assert r.status_code == 401


def test_upload_with_wrong_api_key_is_rejected(client, sample_wav):
    r = _upload(client, {"X-API-Key": "wrong"}, sample_wav)
    assert r.status_code == 401


def test_get_without_api_key_is_rejected(client):
    r = client.get("/tracks/1")
    assert r.status_code == 401


def test_get_nonexistent_track_is_404(client, auth_headers):
    r = client.get("/tracks/999", headers=auth_headers)
    assert r.status_code == 404


def test_upload_completes_and_is_retrievable(client, auth_headers, sample_wav):
    r = _upload(client, auth_headers, sample_wav)
    assert r.status_code == 200
    track_id = r.json()["id"]

    # TestClient runs BackgroundTasks synchronously within the request
    # call (verified directly before writing this suite) -- by the
    # time _upload() returns, analysis has already finished, so no
    # polling loop is needed here the way a real client would need one.
    r2 = client.get(f"/tracks/{track_id}", headers=auth_headers)
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "complete"
    assert body["features"] is not None
    assert isinstance(body["features"]["bpm"], float)
    assert set(body["features"]["frequency_balance"].keys()) == {
        "sub", "bass", "low_mid", "mid", "high"
    }


def test_reuploading_the_same_file_hits_the_cache(client, auth_headers, sample_wav):
    r1 = _upload(client, auth_headers, sample_wav)
    r2 = _upload(client, auth_headers, sample_wav)
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["status"] == "complete"


def test_three_uploads_in_quick_succession_all_complete(client, auth_headers, tmp_path):
    # Stage 7's actual exit criterion: three tracks uploaded in quick
    # succession all complete, status visible throughout.
    paths = []
    for i, freq in enumerate([220.0, 440.0, 880.0]):
        p = tmp_path / f"track_{i}.wav"
        _write_wav(p, freq)
        paths.append(p)

    track_ids = [_upload(client, auth_headers, p).json()["id"] for p in paths]
    assert len(set(track_ids)) == 3  # three genuinely distinct tracks

    for track_id in track_ids:
        r = client.get(f"/tracks/{track_id}", headers=auth_headers)
        assert r.json()["status"] == "complete"

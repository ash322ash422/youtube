"""
Tests for the FastAPI app (app/api/main.py). run_pipeline is monkeypatched
in each test that needs a particular outcome, so these never touch Azure,
never need real OCR/LLM cache fixtures, and run fast - they're testing the
API's contract (login -> upload -> job_id -> pollable status -> download),
not the pipeline itself (that's covered by test_pipeline.py and
test_job_store.py).
"""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import main as api_main
from app.services import job_store

PDF_BYTES = b"%PDF-1.4 fake content for tests"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")
    monkeypatch.setattr(config, "DATA_UPLOAD_DIR", tmp_path / "data_uploads")
    monkeypatch.setattr(config, "AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setattr(config, "AUTH_PASSWORD", TEST_PASSWORD)
    monkeypatch.setattr(config, "JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")


@pytest.fixture
def client() -> TestClient:
    """A TestClient already logged in, with the bearer token set as a
    default header so every existing test call is authenticated without
    having to pass headers explicitly."""
    test_client = TestClient(api_main.app)
    login = test_client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    token = login.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


def test_login_succeeds_with_correct_credentials():
    response = TestClient(api_main.app).post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_credentials():
    response = TestClient(api_main.app).post(
        "/login", data={"username": TEST_USERNAME, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_auth():
    response = TestClient(api_main.app).get("/tenders")
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token():
    response = TestClient(api_main.app).get(
        "/tenders", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_create_tender_rejects_non_pdf(client):
    response = client.post("/tenders", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_create_tender_saves_file_and_runs_pipeline_in_background(client, monkeypatch):
    def _fake_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url="/tmp/out.xlsx",
            token_count=42, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    job_id = body["job_id"]

    assert (config.DATA_UPLOAD_DIR / "sample.pdf").read_bytes() == PDF_BYTES

    status = client.get(f"/tenders/{job_id}")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["status"] == "COMPLETED"
    assert status_body["token_count"] == 42

    listing = client.get("/tenders")
    assert any(j["job_id"] == job_id for j in listing.json())


def test_get_unknown_job_returns_404(client):
    response = client.get("/tenders/does-not-exist")
    assert response.status_code == 404


def test_download_before_completion_returns_409(client, monkeypatch):
    monkeypatch.setattr(api_main, "run_pipeline", lambda blob_name, job_id=None: None)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download")
    assert download.status_code == 409


def test_download_returns_local_file(client, monkeypatch, tmp_path):
    output_file = tmp_path / "result.xlsx"
    output_file.write_bytes(b"fake xlsx content")

    def _fake_local_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url=str(output_file),
            token_count=10, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_local_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download")
    assert download.status_code == 200
    assert download.content == b"fake xlsx content"


def test_download_redirects_for_remote_url(client, monkeypatch):
    remote_url = "https://example.blob.core.windows.net/x.xlsx?sig=abc"

    def _fake_remote_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url=remote_url,
            token_count=5, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_remote_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download", follow_redirects=False)
    assert download.status_code == 307
    assert download.headers["location"] == remote_url

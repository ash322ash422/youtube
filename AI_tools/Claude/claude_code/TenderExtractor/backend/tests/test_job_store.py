"""
Unit tests for the SQLite-backed job_store. Each test gets its own
temp-file database via the isolated_db fixture, so nothing here touches
the real backend/cache/job_flow_status.db.
"""
import pytest

from app import config
from app.services import job_store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")


def test_update_job_creates_row_on_first_call():
    job_id = job_store.new_job_id()
    job = job_store.update_job(job_id, blob_name="tender.pdf", status="STARTED")

    assert job["job_id"] == job_id
    assert job["blob_name"] == "tender.pdf"
    assert job["status"] == "STARTED"
    assert job["token_count"] == 0


def test_update_job_merges_into_existing_row():
    job_id = job_store.new_job_id()
    job_store.update_job(job_id, blob_name="tender.pdf", status="STARTED")
    job = job_store.update_job(job_id, status="COMPLETED", token_count=123, download_url="out.xlsx")

    assert job["status"] == "COMPLETED"
    assert job["token_count"] == 123
    assert job["download_url"] == "out.xlsx"
    assert job["blob_name"] == "tender.pdf"  # untouched fields survive the merge


def test_two_jobs_with_same_blob_name_stay_independent():
    """The whole point of keying by job_id instead of blob_name."""
    job_id_1 = job_store.new_job_id()
    job_id_2 = job_store.new_job_id()
    job_store.update_job(job_id_1, blob_name="tender.pdf", status="COMPLETED")
    job_store.update_job(job_id_2, blob_name="tender.pdf", status="FAILED")

    assert job_store.get_job(job_id_1)["status"] == "COMPLETED"
    assert job_store.get_job(job_id_2)["status"] == "FAILED"


def test_get_job_returns_none_for_unknown_id():
    assert job_store.get_job("does-not-exist") is None


def test_all_jobs_orders_most_recent_first():
    job_id_1 = job_store.new_job_id()
    job_store.update_job(job_id_1, blob_name="first.pdf", status="COMPLETED")
    job_id_2 = job_store.new_job_id()
    job_store.update_job(job_id_2, blob_name="second.pdf", status="COMPLETED")

    jobs = job_store.all_jobs()
    assert [j["job_id"] for j in jobs][:2] == [job_id_2, job_id_1]


def test_total_token_usage_sums_across_jobs():
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED", token_count=10)
    job_store.update_job(job_store.new_job_id(), blob_name="b.pdf", status="COMPLETED", token_count=15)

    assert job_store.total_token_usage() == 25

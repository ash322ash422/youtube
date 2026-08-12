Now, for the architecture question — here's what stands between the current setup and a real decoupled frontend, in rough priority order. **No code changed for this part**, just analysis.

## The core gap: there's no API

Right now "communication" between frontend and backend is `frontend/streamlit_app.py` directly importing and calling `run_pipeline()` in-process (via the `sys.path` shim). That only works because Streamlit is also Python. A React (or any JS) frontend runs in the browser and can only talk to your backend over HTTP — so the real work is putting a web API in front of the pipeline.

**Recommendation: FastAPI.** It's a natural fit here — you already use Pydantic models in `tender_extraction_service.py`, so request/response schemas reuse that pattern, and it gives you OpenAPI/Swagger docs for free (handy once a frontend dev who isn't you is consuming it).

Rough endpoint shape:
- `POST /tenders` — upload a PDF, returns a `job_id` immediately
- `GET /tenders/{job_id}/status` — poll progress
- `GET /tenders/{job_id}/download` — get the finished Excel (or a redirect to the Blob SAS URL you already generate)
- `GET /tenders` — list jobs, for a dashboard view

## Things that need to change to support that API

1. **Make the pipeline non-blocking. (DONE)** `run_pipeline()` takes minutes. An HTTP request can't sit open that long. `POST /tenders` should hand off to a background worker and return right away with a `job_id`; the frontend then polls (or you add SSE/WebSocket later for push instead of polling). Simplest option: FastAPI `BackgroundTasks` for now. If you outgrow a single process, upgrade to a real queue (Celery/RQ + Redis).

2. **Give every job a real unique ID. (DONE)** Jobs are currently keyed by `blob_name` (the filename) in `job_store.py`. Two different users uploading `tender.pdf` would collide — same job record, same file in `data_uploads/`, and (worse) `USE_CACHE` would serve one user's cached OCR/extraction output to the other. Switch the key to a generated UUID per upload, independent of the original filename.

3. **`job_store.py`'s JSON file won't survive concurrency. (DONE)** It's a full read-modify-write on one file with no locking. Fine for one CLI run at a time; not fine for concurrent API requests updating different jobs simultaneously — you'll get lost updates. Move to SQLite (easy swap, still zero extra infra) or Postgres if you want real concurrent-write safety.

4. **Isolate per-job files.** `data_uploads/`, `cache/`, `output/` are flat, shared-by-filename directories. For multi-user/production use, namespace them by `job_id` (e.g. `data_uploads/{job_id}/tender.pdf`) so concurrent jobs can't collide or leak into each other.

5. **CORS.** Once the frontend is a separate origin (React dev server on :3000, backend on :8000, or different domains in prod), you'll need CORS middleware configured with the frontend's allowed origin(s).

6. **Auth.** There's currently none. Anything public-facing that triggers real Azure OpenAI/Document Intelligence spend needs at least an API key or token check before accepting an upload — otherwise it's an open door to run up your Azure bill.

7. **Don't leak `config.py` to the API layer.** `config.py` holds Azure keys, connection strings, SMTP credentials. Keep API response models explicit (job status, download URL, error message only) rather than ever serializing `ctx` or `config` directly — easy mistake to make by accident later.

8. **Reuse what already works.** Two things are already API-shaped and don't need rework:
   - The per-stage `job_store.update_job(status=f"{name}_done")` calls already give you a progress trail — a `GET /status` endpoint can read that straight out of the job store for a progress bar.
   - `blob_storage.generate_download_url()` already produces a time-limited SAS URL — that's exactly the download mechanism a web frontend wants (no need to proxy the file through your API server).

9. **Deployment shape.** Containerize backend and frontend separately (a `Dockerfile` each — the repo split we already did makes this natural), add a `/health` endpoint for orchestration, and move secrets out of `.env` into whatever secrets manager your host provides (Key Vault, etc.) once it's not just running on your desktop.

If/when you're ready to act on any of this, I'd suggest starting with #1–#3 (FastAPI + background execution + UUID job IDs) since everything else builds on top of those.
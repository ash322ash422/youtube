# TenderExtractor

Turns a government tender PDF into a validated Excel summary:

```
PDF  ->  OCR (Document Intelligence)  ->  LLM field extraction  ->
validate/normalize  ->  Excel  ->  publish  ->  notify
```

Backend and frontend are fully separate: `frontend/streamlit_app.py` is a
plain HTTP client of the backend's REST API (`app/api/main.py`) - it never
imports backend code - so it can run against a backend on a different
host/process/deployment entirely. It logs in first (single-user JWT auth)
and attaches the token to every subsequent request.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt   # only needed to run the Streamlit UI
cp .env.example .env
# fill in: Azure OpenAI + Document Intelligence keys, and AUTH_PASSWORD
# (the API refuses all logins until AUTH_PASSWORD is set - see ## API below)

# drop PDFs into backend/data_uploads/, then either:

# 1) CLI - processes every PDF in backend/data_uploads/, no auth needed
python backend/main.py
python backend/main.py --file 01_tender_mini_version.pdf   # or just one

# 2) REST API + Streamlit UI - talk to each other over HTTP
cd backend && uvicorn app.api.main:app --reload   # terminal 1
streamlit run frontend/streamlit_app.py           # terminal 2, log in with AUTH_USERNAME/AUTH_PASSWORD
```

Output lands in `backend/output/<name>.xlsx` (clean) and
`backend/output/<name>.nit_audit.xlsx` (original + normalized value + valid
flag, for QA). Progress for every run is tracked in
`backend/cache/job_flow_status.db` (SQLite), keyed by a generated `job_id`
rather than filename, so re-processing the same file - or two different
uploads that happen to share a filename - never overwrites another run's
status. Each row also records `token_count`, the total LLM tokens spent
processing that run. Print a summary of token usage across every recorded
job with:

```bash
cd backend && python -m scripts.print_token_usage
```

## API

`app/api/main.py` is a thin FastAPI wrapper around `run_pipeline()`. Each
upload runs in a background task so the HTTP request returns immediately
with a `job_id`; the frontend polls status from there. Every endpoint
except `/login` and `/health` requires a JWT from `/login`.

```bash
cd backend && uvicorn app.api.main:app --reload
```

| Method | Path                        | Auth | Description                                                              |
|--------|-----------------------------|:----:|---------------------------------------------------------------------------|
| POST   | `/login`                    |  -   | Form-encoded `username`+`password`, checked against `AUTH_USERNAME`/`AUTH_PASSWORD` in `.env`. Returns `{access_token, token_type}`. |
| POST   | `/tenders`                  |  ✓   | Upload a PDF (multipart `file`). Returns `{job_id, blob_name, status}` immediately (202) and starts processing in the background. |
| GET    | `/tenders`                  |  ✓   | List every job, most recent first.                                       |
| GET    | `/tenders/{job_id}`         |  ✓   | Status/details for one job (poll this for progress).                     |
| GET    | `/tenders/{job_id}/download`|  ✓   | Finished Excel file - redirects to the Blob SAS URL, or streams the local file, depending on whether `AZURE_STORAGE_CONNECTION_STRING` is set. 409 if the job isn't COMPLETED yet. |
| GET    | `/health`                   |  -   | Liveness check.                                                          |

Auth is single-user by design (see `app/services/auth.py`) - one
username/password pair from `.env`, no user table. `AUTH_PASSWORD` empty
means login always fails (fails closed, not open). Send the token as
`Authorization: Bearer <token>` on every protected call; tokens expire
after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). Set `JWT_SECRET_KEY` in
`.env` for tokens to survive a server restart - if left blank, a random
key is generated per process and every prior token is invalidated on the
next restart.

Set `CORS_ALLOWED_ORIGINS` in `.env` (comma-separated) to the origin(s) your
frontend is served from - it defaults to the common local dev ports for a
React app (`:3000`) and Streamlit (`:8501`). This only matters for a
browser-based frontend making requests directly (e.g. a future React app);
Streamlit's own requests to the API are server-to-server and aren't
subject to CORS.

Interactive docs (Swagger UI) are available at `/docs` once the server is
running - its "Authorize" button calls `/login` for you.

## Layout

```
backend/
  app/
    config.py               # the only module that reads os.environ
    api/
      main.py                 # FastAPI app: upload/status/download endpoints
      schemas.py               # request/response models
    pipeline/
      context.py             # PipelineContext - the object passed between stages
      stages.py               # one function per pipeline step
      runner.py               # runs the stages in order, updates job status
    services/                # one file per external concern, no pipeline knowledge
      blob_storage.py
      document_intelligence.py
      llm.py
      prompt.py
      index_data_service.py
      nit_data_service.py
      tender_extraction_service.py
      validation.py
      nit_export_excel.py
      tender_export_excel.py
      consolidate_excels_files.py
      email_service.py
      job_store.py            # SQLite-backed job status, keyed by job_id
      auth.py                  # single-user JWT login/verification
    utils/
      logging_config.py
  main.py                    # CLI: discovers PDFs and runs the pipeline over them
  scripts/                   # dev-only utilities (env checks, token usage report)
  tests/
  data_uploads/               # tenders waiting to be processed
  cache/                       # intermediate OCR / LLM output, job_flow_status.db
  output/                       # final Excel deliverables
  logs/
frontend/
  streamlit_app.py            # browser UI; talks to app/api/main.py over HTTP only
```

**Services** know how to talk to one external thing (Blob Storage, Document
Intelligence, the LLM, email) and nothing about tenders or the pipeline.
**Stages** know the tender domain and call one or two services each.
**The runner** knows the *order* of stages; nothing else does.

## Why it's structured this way

- **Modular** - each stage is a plain function `stage_x(ctx) -> None`. Add a
  step by writing one function and adding one line to `STAGES` in
  `runner.py`. Nothing else has to change.
- **Scales to a batch** - `main.py` loops over every PDF in `data_uploads/`
  (or a Blob container, once `USE_LOCAL_PDF_FILE=false`), and one tender
  failing doesn't stop the rest. Each *run* gets its own row in
  `cache/job_flow_status.db`, keyed by a generated `job_id` rather than
  filename, so concurrent/repeated runs never collide.
- **Cheap to re-run** - OCR and LLM calls are the expensive/slow steps, so
  their output is cached to disk per-file (`USE_CACHE=true`). Re-running the
  pipeline after a code change in a later stage doesn't re-call Azure.
- **Degrades gracefully** - if `AZURE_STORAGE_CONNECTION_STRING` isn't set,
  the `publish` stage just leaves the Excel file in `output/` instead of
  failing. Good for local development; nothing to configure for a POC.
- **Not over-engineered** - no web framework, no async, no class
  hierarchies. It's a list of functions run in order. That's the whole
  abstraction, which is enough for a linear document pipeline like this one.

## Adding a new field to extract

1. Add `{"name": ..., "description": ...}` to `FIELDS_TO_EXTRACT` in
   `backend/app/services/prompt.py`.
2. If it's a date or currency amount, add its exact name to `DATE_FIELDS` /
   `AMOUNT_FIELDS` in `backend/app/services/validation.py` so it gets
   normalized automatically. Otherwise it's carried through as-is.

## Tests

```bash
cd backend && pytest tests/
```

Covers prompt building, chunk-merging, field validation, the SQLite job
store, and the API's login/upload/status/download contract (with
`run_pipeline` mocked, so these never touch Azure or need OCR/LLM cache
fixtures) - everything that doesn't need live Azure credentials to test.

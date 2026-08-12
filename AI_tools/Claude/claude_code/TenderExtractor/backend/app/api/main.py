"""
FastAPI wrapper around the tender-extraction pipeline, so a frontend
(React, another JS framework, or Streamlit talking HTTP instead of
importing app.* directly) can drive it over a network instead of an
in-process function call.

Run from the backend/ directory:
    uvicorn app.api.main:app --reload

Endpoints:
    POST   /login                      username+password (form-encoded) ->
                                        JWT access token. Everything below
                                        requires it as `Authorization: Bearer
                                        <token>`.
    POST   /tenders                    upload a PDF; returns a job_id and
                                        starts processing in the background
    GET    /tenders                    list every job, most recent first
    GET    /tenders/{job_id}           status/details for one job
    GET    /tenders/{job_id}/download  the finished Excel file (redirects
                                        to the Blob SAS URL, or streams the
                                        local file, depending on how
                                        Blob Storage is configured)
    GET    /health                     liveness check (no auth required)

A run's status/error/download_url/token_count live in job_store (SQLite),
which is exactly what stage-by-stage GET /tenders/{job_id} polling reads -
no separate progress-tracking mechanism needed.
"""
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app import config
from app.api.schemas import JobCreatedResponse, JobResponse, TokenResponse
from app.pipeline.runner import run_pipeline
from app.services import auth, job_store
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

app = FastAPI(title="TenderExtractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# tokenUrl points Swagger UI's "Authorize" button at /login so protected
# endpoints can be tried out directly from /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    username = auth.decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def _run_pipeline_in_background(blob_name: str, job_id: str) -> None:
    """
    run_pipeline() already writes a FAILED status (with error/failed_stage)
    to job_store before re-raising, so a failure here only needs to be
    logged - there is no HTTP request left to propagate it to.
    """
    try:
        run_pipeline(blob_name, job_id=job_id)
    except Exception:
        logger.exception("[%s] (job %s) background pipeline run failed", blob_name, job_id)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    if not auth.verify_credentials(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = auth.create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)


@app.post("/tenders", response_model=JobCreatedResponse, status_code=202)
async def create_tender(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
) -> JobCreatedResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    config.DATA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = config.DATA_UPLOAD_DIR / file.filename
    dest_path.write_bytes(await file.read())

    job_id = job_store.new_job_id()
    job_store.update_job(job_id, blob_name=file.filename, status="PENDING")

    background_tasks.add_task(_run_pipeline_in_background, file.filename, job_id)

    logger.info("[%s] (job %s) queued for processing", file.filename, job_id)
    return JobCreatedResponse(job_id=job_id, blob_name=file.filename, status="PENDING")


@app.get("/tenders", response_model=list[JobResponse])
def list_tenders(current_user: str = Depends(get_current_user)) -> list[dict]:
    return job_store.all_jobs()


@app.get("/tenders/{job_id}", response_model=JobResponse)
def get_tender(job_id: str, current_user: str = Depends(get_current_user)) -> dict:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/tenders/{job_id}/download")
def download_tender(job_id: str, current_user: str = Depends(get_current_user)):
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    download_url = job.get("download_url")
    if job["status"] != "COMPLETED" or not download_url:
        raise HTTPException(status_code=409, detail=f"Job is not complete yet (status: {job['status']}).")

    if download_url.startswith("http://") or download_url.startswith("https://"):
        return RedirectResponse(download_url)

    local_path = Path(download_url)
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="Output file no longer exists on disk.")
    return FileResponse(local_path, filename=local_path.name)

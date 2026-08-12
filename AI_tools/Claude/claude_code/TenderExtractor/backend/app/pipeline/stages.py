# stages.py
"""
Each function here is one pipeline stage. A stage takes the shared
PipelineContext, does one job, and writes its result back onto it.

To add a new stage: write a function with this same signature, then
register it in STAGES in app/pipeline/runner.py. Nothing else needs
to change.
"""
import json
# import pandas as pd
import openpyxl

from app import config
from app.pipeline.context import PipelineContext
from app.services import (
    blob_storage,
    document_intelligence,
    index_data_service,
    nit_data_service,
    validation,
    nit_export_excel,
    tender_extraction_service,
    tender_export_excel,
    consolidate_excels_files,
    email_service,
)
from app.services.prompt import FIELDS_TO_EXTRACT
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _accumulate_tokens(ctx: PipelineContext, count: int) -> None:
    ctx.token_count += count


def _save_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_pages(ctx: PipelineContext) -> list:
    """
    OCR pages for `ctx`, preferring the in-memory copy but falling back
    to the OCR cache file - a defensive fallback for stages being run
    out of the normal STAGES order (e.g. in isolation/tests), since in a
    normal run stage_ocr always populates ctx.document_data first.
    """
    if ctx.document_data is not None:
        return ctx.document_data["pages"]
    if ctx.ocr_cache_path.exists():
        return _load_json(ctx.ocr_cache_path)["pages"]
    raise FileNotFoundError(
        f"No OCR data available for {ctx.blob_name} "
        f"(ctx.document_data is empty and {ctx.ocr_cache_path} does not exist)"
    )


# --------------------------------------------------------------------------
# Stage 1: get the PDF bytes onto local disk / into memory
# --------------------------------------------------------------------------
def stage_ingest(ctx: PipelineContext) -> None:
    if config.USE_LOCAL_PDF_FILE:
        if not ctx.local_pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {ctx.local_pdf_path}")
        ctx.pdf_bytes = ctx.local_pdf_path.read_bytes()
    else:
        ctx.pdf_bytes = blob_storage.download_blob_as_stream(
            connection_string=config.AZURE_STORAGE_CONNECTION_STRING,
            container_name=config.BLOB_CONTAINER_INCOMING,
            blob_name=ctx.blob_name,
        )

    # Best-effort durability copy in Blob Storage - never fails the pipeline.
    if config.AZURE_STORAGE_CONNECTION_STRING:
        try:
            client = blob_storage.get_blob_service_client(config.AZURE_STORAGE_CONNECTION_STRING)
            container = blob_storage.get_or_create_container(client, config.BLOB_CONTAINER_INCOMING)
            if not blob_storage.blob_exists(container, ctx.blob_name):
                blob_storage.upload_file(container, ctx.local_pdf_path, ctx.blob_name)
        except Exception:
            logger.warning("[%s] Could not mirror PDF to Blob Storage, continuing.", ctx.blob_name)


# --------------------------------------------------------------------------
# Stage 2: OCR / layout extraction. It stores the result in ctx.document_data locally in cache if configured.
# --------------------------------------------------------------------------
def stage_ocr(ctx: PipelineContext) -> None:
    if config.USE_CACHE and ctx.ocr_cache_path.exists():
        logger.info("[%s] OCR data found in cache and using it: %s", ctx.blob_name, ctx.ocr_cache_path)
        ctx.document_data = _load_json(ctx.ocr_cache_path)
        return

    document_intelligence.validate_pdf_is_digital(ctx.pdf_bytes)

    result = document_intelligence.analyze_document_from_bytes(
        document_bytes=ctx.pdf_bytes,
        endpoint=config.AZURE_DOCINTEL_ENDPOINT,
        key=config.AZURE_DOCINTEL_KEY,
        model_name=config.AZURE_DOCINTEL_MODEL,
    )

    ctx.document_data = document_intelligence.extract_document_data(result)
    _save_json(ctx.ocr_cache_path, ctx.document_data)


# --------------------------------------------------------------------------
# Stage: extract "index" (table of contents) data. This contains useful info like page number of T&C, etc.
# --------------------------------------------------------------------------
def stage_extract_index_data(ctx: PipelineContext) -> None:
    cache_file = ctx.extracted_index_cache_path

    if config.USE_CACHE and cache_file.exists():
        logger.info(
            "[%s] Using extracted 'index' data found in cache: %s",
            ctx.blob_name, cache_file,
        )
        ctx.extracted_index_data = _load_json(cache_file)
        return

    pages = _get_pages(ctx)

    try:
        ctx.extracted_index_data = index_data_service.extract_data(
            pages, token_callback=lambda n: _accumulate_tokens(ctx, n)
        )
        _save_json(cache_file, ctx.extracted_index_data)

    except ValueError:
        logger.warning(
            "[%s] '%s' section not found, skipping.",
            ctx.blob_name, index_data_service.TARGET_HEADING,
        )



# --------------------------------------------------------------------------
# Stage 3: Field extraction via LLM: Loads the OCRed text data and then 
# sends it to LLM for extraction of NIT data
# --------------------------------------------------------------------------
def stage_extract_nit_data(ctx: PipelineContext) -> None:
    if config.USE_CACHE and ctx.extracted_nit_cache_path.exists():
        logger.info("[%s] Using Extracted NIT data found in cache: %s", ctx.blob_name, ctx.extracted_nit_cache_path)
        ctx.extracted_nit_data = _load_json(ctx.extracted_nit_cache_path)
        return

    ctx.extracted_nit_data = nit_data_service.extract_document(
        document_data=ctx.document_data,
        fields=FIELDS_TO_EXTRACT,
        pages_per_chunk=config.PAGES_PER_CHUNK,
        token_callback=lambda n: _accumulate_tokens(ctx, n),
    )
    _save_json(ctx.extracted_nit_cache_path, ctx.extracted_nit_data)


# --------------------------------------------------------------------------
# Stage 4: validate / normalize the NIT data
# --------------------------------------------------------------------------
def stage_validate_nit(ctx: PipelineContext) -> None:
    ctx.validated_nit_data = validation.validate_nit_extracted_json(ctx.extracted_nit_data)
    _save_json(ctx.validated_nit_cache_path, ctx.validated_nit_data)


# --------------------------------------------------------------------------
# Stage 5: Export to Excel
# --------------------------------------------------------------------------
def stage_export_nit_data(ctx: PipelineContext) -> None:
    audit_df = nit_export_excel.validation_json_to_dataframe(ctx.validated_nit_data)
    nit_export_excel.save_dataframe_to_excel(audit_df, ctx.audit_nit_excel_path)

    clean_df = nit_export_excel.validation_json_to_clean_dataframe(ctx.validated_nit_data)
    nit_export_excel.save_dataframe_to_excel(clean_df, ctx.clean_nit_excel_path)


# --------------------------------------------------------------------------
# Stage : extract "terms and conditions", "List of document to be  scanned and upload", "Acceptable make"
# --------------------------------------------------------------------------
def stage_extract_tender_misc_data(ctx: PipelineContext) -> None:
    cache_file = ctx.extracted_misc_cache_path

    if config.USE_CACHE and cache_file.exists():
        logger.info(
            "[%s] Using extracted data found in cache: %s",
            ctx.blob_name, cache_file,
        )
        ctx.extracted_misc_data = _load_json(cache_file)
        return

    pages = _get_pages(ctx)

    try:
        ctx.extracted_misc_data = tender_extraction_service.extract_data(
            pages, token_callback=lambda n: _accumulate_tokens(ctx, n)
        )
        _save_json(cache_file, ctx.extracted_misc_data)

    except ValueError:
        logger.warning("[%s] Miscellaneous data not found", ctx.blob_name)


# --------------------------------------------------------------------------
# Stage: Export the miscellaneous data to excel
# --------------------------------------------------------------------------
def stage_export_tender_misc_data(ctx: PipelineContext) -> None:

    data = ctx.extracted_misc_data

    # 1. Defensive Guard Clause
    if not data:
        logger.warning("[%s] No extracted misc. data found in context. Skipping export.", ctx.blob_name)
        return

    # 2. Safe Generation and Save
    try:
        filename = tender_export_excel.export_extraction_to_excel(data, ctx.exported_misc_excel_path)
        logger.info("[%s] Wrote misc data to -> %s", 
                    ctx.blob_name, ctx.exported_misc_excel_path)
    except (ValueError, KeyError, TypeError) as e:
            logger.error(
                "[%s] Failed to build or save misc workbook. Error: %s",
                ctx.blob_name, str(e)
            )    
        


# --------------------------------------------------------------------------
# Stage 8: consolidate all excels into one workbook,
# --------------------------------------------------------------------------
def stage_consolidate_all_excels(ctx: PipelineContext) -> None:
    # (file_path, sheet_name_override): override renames a single-sheet file's
    # sheet; None means "copy every sheet from this workbook, keep its own name".
    input_files = [
        (ctx.clean_nit_excel_path, "NIT Data"),
        (ctx.exported_misc_excel_path, None),
    ]
    
    existing_files = [(p, override) for p, override in input_files if p.exists()]
    if not existing_files:
        logger.warning("[%s] No individual excel outputs found to consolidate. Skipping.",
                       ctx.blob_name
        )
        return
    if len(existing_files) < len(input_files):
        existing_paths = {p for p, _ in existing_files}
        missing = [p.name for p, _ in input_files if p not in existing_paths]
        logger.warning("[%s] Missing excel outputs, consolidating available ones only: %s",
                       ctx.blob_name, missing
        )

    try:
        consolidated_wb = openpyxl.Workbook()
        consolidated_wb.remove(consolidated_wb.active)  # drop the default blank sheet

        for path, override in existing_files:
            src_wb = openpyxl.load_workbook(path)
            # override => only that file's first sheet, renamed; None => every sheet, original names
            src_sheet_names = [src_wb.sheetnames[0]] if override else src_wb.sheetnames
            for src_sheet_name in src_sheet_names:
                src_ws = src_wb[src_sheet_name]
                title = (override or src_sheet_name)[:31]  # Excel sheet names capped at 31 chars
                dst_ws = consolidated_wb.create_sheet(title)
                consolidate_excels_files._copy_worksheet(src_ws, dst_ws)
            src_wb.close()

        consolidated_wb.save(ctx.consolidated_excel_path)
        logger.info("[%s] Wrote consolidated excel -> %s",
                    ctx.blob_name,
                    ctx.consolidated_excel_path
        )
    except (ValueError, KeyError, TypeError, OSError) as e:
        logger.error(
            "[%s] Failed to build or save consolidated workbook. Error: %s",
            ctx.blob_name, str(e),
        )


# --------------------------------------------------------------------------
# Stage 10: publish the output (Blob Storage if configured, else local disk)
# --------------------------------------------------------------------------
def stage_publish(ctx: PipelineContext) -> None:
    if not config.AZURE_STORAGE_CONNECTION_STRING:
        ctx.download_url = str(ctx.consolidated_excel_path)
        logger.info("[%s] Blob Storage not configured - output kept locally at %s", 
                    ctx.blob_name, 
                    ctx.download_url
        )
        return

    client = blob_storage.get_blob_service_client(config.AZURE_STORAGE_CONNECTION_STRING)
    processed_container = blob_storage.get_or_create_container(client, 
                                                               config.BLOB_CONTAINER_PROCESSED
    )

    blob_storage.upload_file(processed_container, ctx.consolidated_excel_path)

    blob_storage.move_blob(
        client,
        source_container=config.BLOB_CONTAINER_INCOMING,
        destination_container=config.BLOB_CONTAINER_PROCESSED,
        blob_name=ctx.blob_name,
    )

    ctx.download_url = blob_storage.generate_download_url(
        connection_string=config.AZURE_STORAGE_CONNECTION_STRING,
        container_name=config.BLOB_CONTAINER_PROCESSED,
        blob_name=ctx.consolidated_excel_path.name,
        expiry_hours=config.URL_EXPIRY_HOURS,
    )

# --------------------------------------------------------------------------
# Stage 11: notify (optional, non-fatal - a failed email shouldn't fail a
# tender that was otherwise processed successfully)
# --------------------------------------------------------------------------
def stage_notify(ctx: PipelineContext) -> None:
    if not config.NOTIFY_ON_COMPLETE:
        return

    if len(config.NOTIFY_RECIPIENTS) == 0:
        logger.warning("[%s] NOTIFY_ON_COMPLETE is set but NOTIFY_RECIPIENTS is empty, skipping.",
                       ctx.blob_name
        )
        return

    for recipient in config.NOTIFY_RECIPIENTS:
        try:
            email_service.send_notification(recipient, 
                                            ctx.download_url, 
                                            ctx.blob_name
            )
        except Exception:
            logger.exception("[%s] Notification email failed, tender output is still valid.",
                            ctx.blob_name
            )

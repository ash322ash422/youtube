"""
Sends OCR'd pages to the LLM in chunks and merges the partial results
into one flat dict of extracted fields.
"""
import json
from typing import Callable, Optional

from langchain_community.callbacks.manager import get_openai_callback

from app.services import llm as llm_service
from app.services.prompt import build_extraction_prompt
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

def extract_chunk(
    pages: list,
    fields: list,
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:

    llm = llm_service.get_llm()
    prompt = build_extraction_prompt(pages=pages, fields=fields)
    logger.info(".....Sending %s pages to LLM for extraction", len(pages))

    with get_openai_callback() as cb:
        response = llm.invoke(prompt)
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    return json.loads(response.content)

def merge_results(results: list) -> dict:
    """First non-empty value wins across chunks."""
    final = {}
    for partial in results:
        for key, value in partial.items():
            if value and not final.get(key):
                final[key] = value
    return final



def extract_document(
    document_data: dict,
    fields: list,
    pages_per_chunk: int = 2,
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:

    if document_data is None:
        logger.error("Received None for document_data.")
        return {}

    # NIT data is present only in  first 4 pages
    pages = document_data.get("pages", [])[:4]
    
    # 1. Guard Clause for Empty Input
    if not pages:
        logger.warning("No pages found in document_data. Skipping extraction.")
        return {}

    partial_results = []

    # 2. Safe Chunked Iteration
    for i in range(0, len(pages), pages_per_chunk):
        chunk = pages[i : i + pages_per_chunk]
        
        # Explicit check to guarantee chunk elements exist before logging
        if chunk:
            start_page = chunk[0].get("page_number", i + 1)
            end_page = chunk[-1].get("page_number", i + len(chunk))
            logger.info("Extracting pages %s-%s", start_page, end_page)
        
        # 3. Process Chunk
        result = extract_chunk(chunk, fields, token_callback=token_callback)
        if result:  # Only append if the LLM successfully returned data
            partial_results.append(result)

    # 4. Defensive Merge
    if not partial_results:
        return {}
        
    return merge_results(partial_results)

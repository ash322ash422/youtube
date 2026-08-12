
# To run this as standalone: python -m app.services.tender_extraction_service
from __future__ import annotations

import json
from typing import Callable, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langchain_community.callbacks.manager import get_openai_callback
    
from app.services.llm import get_llm
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# No hard page cap by default. In real NITs, these sections routinely start
# well past the first few pages (in three sample tenders they started on
# pages 6, 9, and 11, and one ran through page 13) so truncating early
# silently drops data. Override via extract_data(..., max_pages=N) only if
# you know the section you need is near the front and want to save tokens.
DEFAULT_MAX_PAGES: Optional[int] = None

# Rough safety valve: warn if the OCR text is large enough that a single
# call might approach typical context limits. This does NOT chunk for you -
# it just tells you loudly instead of silently truncating or erroring deep
# inside the model call. Tune to your model's actual context window.
WARN_CHAR_THRESHOLD = 400_000


SYSTEM_PROMPT = """
You are a precise information-extraction assistant. You are an expert in extracting key data from Indian
government tender files.

You will be given JSON-derived OCR text from a PDF of an Indian government tender document (NIT), broken
into pages. Each page may also include a separate list of tables already parsed into rows and columns -
use those when present instead of re-parsing table-like text yourself, since they are more reliable.

Your job is to extract exactly three items:

1. "Terms and Conditions" - may appear under headings such as "General Terms & Conditions",
   "Terms & Conditions", "Special Conditions", "General Conditions", etc. A document may contain more than
   one such section under different headings (e.g. both "Terms & Conditions" and "General Conditions") -
   capture each as a separate section.

2. "Acceptable Make" - may appear under headings such as "List of Acceptable Makes", "Approved Makes",
   "Make of Material", etc. This is sometimes a standalone table/section, and sometimes embedded inside a
   numbered clause of the Terms and Conditions (e.g. "the contractor shall use any of the following makes:
   a) MS Pipe: Jindal/Tata ..."). Extract it as its own field either way.

3. "List of Documents to be Scanned and Uploaded" - may appear as "Documents to be scanned and uploaded",
   "List of Documents required to be uploaded", etc. A document may contain more than one such list for
   different bidder categories (e.g. one list "for CPWD registered contractors" and another "for Non-CPWD
   agencies") - capture each as a separate section.

Rules:
- Only use information explicitly present in the provided text. Do not infer or fabricate content.
- Any of the three items may span multiple pages and/or multiple distinct headings - merge content for the
  same logical item together, but keep distinct headings as distinct sections.
- Preserve original numbering/lettering exactly as printed (e.g. "1.", "(iii)", "a)"). If an item has no
  numbering in the source, leave the number field null.
- Preserve tables as structured rows/columns rather than flattening them into prose.
- Preserve footnotes/notes attached to a section (e.g. "Note: ...") separately from the numbered items.
- If an item is not present anywhere in the provided text, mark it as not present and leave its sections
  list empty - do not guess.
- Record which page number(s) each section's content came from.
"""


# --------------------------------------------------------------------------
# Structured output schema
#
# Generic enough to cover every shape we've actually seen: a single plain
# numbered list (tender 1), a single very long numbered list split across
# many pages (tender 2), two differently-headed numbered lists for the same
# field (tender 3's "Terms & Conditions" + "General Conditions", and its two
# "Documents" lists for CPWD vs non-CPWD bidders), and a table that's either
# standalone or embedded inside another clause.
# --------------------------------------------------------------------------

class ExtractedTable(BaseModel):
    caption: Optional[str] = Field(
        None, description="Short label for the table if the source gives one, else null."
    )
    columns: list[str] = Field(
        default_factory=list, description="Column headers, in order, exactly as printed."
    )
    rows: list[list[str]] = Field(
        default_factory=list, description="Table rows; each row's cells align with `columns`."
    )


class ExtractedItem(BaseModel):
    number: Optional[str] = Field(
        None, description="Numbering/lettering exactly as printed, e.g. '1.', '(iii)', 'a)'. Null if unnumbered."
    )
    text: str = Field(description="Verbatim text of this clause/item/document requirement.")


class ExtractedSection(BaseModel):
    heading: Optional[str] = Field(
        None,
        description=(
            "Exact heading text this content appears under, e.g. 'General Terms & Conditions', "
            "'List of Documents for CPWD Reg. Contractors'. Null if the content has no heading of its own "
            "(e.g. a make list embedded inside a Terms & Conditions clause)."
        ),
    )
    source_pages: list[int] = Field(
        default_factory=list, description="Page numbers this section's content was found on."
    )
    items: list[ExtractedItem] = Field(
        default_factory=list, description="Numbered/lettered/plain list items, in original order."
    )
    tables: list[ExtractedTable] = Field(
        default_factory=list, description="Tables belonging to this section, if any."
    )
    notes: list[str] = Field(
        default_factory=list, description="Footnotes/asterisked notes/caveats attached to this section."
    )


class ExtractedField(BaseModel):
    present: bool = Field(description="True if this item was found anywhere in the provided text.")
    sections: list[ExtractedSection] = Field(
        default_factory=list,
        description="One entry per distinct heading/variant found. Empty when `present` is False.",
    )


class TenderExtraction(BaseModel):
    terms_and_conditions: ExtractedField
    acceptable_make: ExtractedField
    documents_to_be_scanned_and_uploaded: ExtractedField


def _build_user_prompt(pages: list[dict], max_pages: Optional[int]) -> str:
    selected = pages if max_pages is None else pages[:max_pages]

    blocks = []
    for p in selected:
        block = [f"--- Page {p['page_number']} ---", p.get("text", "")]
        tables = p.get("tables") or []
        for i, table in enumerate(tables, start=1):
            if not table:
                continue
            block.append(f"[Page {p['page_number']} parsed table {i}]")
            block.append(json.dumps(table, ensure_ascii=False))
        blocks.append("\n".join(block))

    excerpt = "\n\n".join(blocks)

    if len(excerpt) > WARN_CHAR_THRESHOLD:
        logger.warning(
            "OCR excerpt is %d characters across %d pages; this may approach the model's "
            "context limit in a single call. Consider chunking by page ranges if you see "
            "truncated or failed responses.",
            len(excerpt),
            len(selected),
        )

    return f"OCR text (with parsed tables where available) from {len(selected)} page(s):\n\n{excerpt}"


def _call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> TenderExtraction:
    llm = get_llm()
    structured_llm = llm.with_structured_output(TenderExtraction)

    with get_openai_callback() as cb:
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    # Some langchain backends return the pydantic model directly; others
    # return a dict-like object depending on configuration.
    if isinstance(response, TenderExtraction):
        return response

    return TenderExtraction.model_validate(response)


def _call_llm_fallback(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> TenderExtraction:
    """
    Fallback path for LLM backends that don't support with_structured_output.
    Embeds the JSON schema in the prompt and parses/validates the raw
    response, tolerating code-fenced responses.
    """
    llm = get_llm()
    schema_hint = (
        "\n\nRespond with ONLY a single JSON object matching exactly this schema "
        "(no markdown fences, no commentary):\n"
        f"{json.dumps(TenderExtraction.model_json_schema(), indent=2)}"
    )
    # response = llm.invoke(
    #     [
    #         SystemMessage(content=system_prompt + schema_hint),
    #         HumanMessage(content=user_prompt),
    #     ]
    # )

    with get_openai_callback() as cb:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw.split("\n", 1)[-1]
    try:
        return TenderExtraction.model_validate_json(raw)
    except Exception as e:
        raise ValueError(f"LLM did not return JSON matching the expected schema: {raw!r}") from e


def extract_data(
    pages: list[dict],
    max_pages: Optional[int] = DEFAULT_MAX_PAGES,
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:
    """
    Extract Terms and Conditions, Acceptable Make, and List of Documents to
    be Scanned and Uploaded from OCR page data, returning a JSON-ready dict
    matching the TenderExtraction schema.

    Each of the three top-level fields is an object of the form:
        {"present": bool, "sections": [ {heading, source_pages, items, tables, notes}, ... ]}

    A field with "present": false means the LLM looked and genuinely could
    not find that item anywhere in the supplied pages - that is an expected,
    valid result, not an error. This function raises ValueError only if the
    LLM call itself fails or its output can't be validated against the
    schema.

    The output is designed to convert cleanly to Excel later: iterate
    top-level fields -> sections -> items/tables, writing one sheet per
    field (as done for these three tenders already) or one row block per
    section within a sheet.

    token_callback, if given, is invoked once with the total token count
    used by this call (see app.pipeline.stages, which uses it to
    accumulate PipelineContext.token_count).
    """
    user_prompt = _build_user_prompt(pages, max_pages)

    try:
        llm = get_llm()
        if hasattr(llm, "with_structured_output"):
            extraction = _call_llm_structured(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
        else:
            extraction = _call_llm_fallback(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"LLM call failed while extracting tender data: {e}") from e

    result = extraction.model_dump(mode="json")

    if not any(result[key]["present"] for key in result):
        logger.warning(
            "LLM could not find any of the three target sections in the %d page(s) provided.",
            len(pages) if max_pages is None else min(max_pages, len(pages)),
        )

    return result


if __name__ == "__main__":
    # Quick manual test with fake OCR pages - hits the real LLM (needs valid
    # AZURE_OPENAI_* env vars, or whatever get_llm() is configured for).
    # "Acceptable Make" is deliberately absent so you can confirm the
    # not-present behavior actually works, and one clause is deliberately
    # numbered with a letter to check numbering preservation.
    
    fake_pages = [
        {
            "page_number": 1,
            "text": "GOVERNMENT OF INDIA\nCENTRAL PUBLIC WORKS DEPARTMENT\n"
            "NOTICE INVITING TENDER\nNIT No. 41/EE/E/PEED/2026-2027\n"
            "Name of Work: RMO Fire Alarm & Fire Fighting System.",
            "tables": [],
        },
        {
            "page_number": 5,
            "text": "List of Documents to be scanned and uploaded within the period of bid submission:\n"
            "1. Treasury Challan / Demand Draft against EMD.\n"
            "2. Copy of receipt for deposition of original EMD.\n"
            "3. Enlistment Order of the Contractor.",
            "tables": [],
        },
        {
            "page_number": 6,
            "text": "TERMS AND CONDITIONS\n"
            "1. Materials shall be got approved from the Engineer-in-Charge before use at site.\n"
            "2. Any damages done to the building shall be made good by the contractor.\n"
            "S.No. Description of Items Unit Rate",
            "tables": [
                [
                    ["S.No.", "Description of Items", "Unit", "Rate"],
                    ["1", "2x1.5 sq.mm fire alarm armored cable", "P/Mtrs", "30"],
                    ["2", "Addressable photo thermal detector", "Each", "90"],
                ]
            ],
        },
    ]
    
    
    # path = r"C:\Users\hi\Desktop\projects\python_projects\tutorial\play_langchain_llamaindex_langgraph\TenderExtractor\cache\01_tender_mini_version.ocr.json"
    # with open(path, "r", encoding="utf-8") as f:
    #         documents = json.load(f)
    # # print(documents['pages'])
    
    pages = fake_pages # documents['pages'] # or fake_pages
    
    result = extract_data(pages)
    print(json.dumps(result, indent=2))

"""
tool_schemas.py
----------------
INDUSTRY PATTERN: one typed contract per tool, used twice.

Every tool an agent can call has a Pydantic model describing its
arguments. That one model does two jobs:

  1. `.model_json_schema()` generates the JSON Schema we hand to Claude
     in the `tools=[...]` parameter, so the model knows exactly what
     arguments a tool accepts (names, types, which are required).

  2. `Model.model_validate(tool_use.input)` validates whatever the LLM
     actually sends back at runtime, BEFORE we let it touch real code.
     LLMs occasionally send malformed or missing arguments -- treating
     that input as untrusted and validating it is exactly what you'd do
     with input coming from any other external, non-deterministic
     client.

If validation fails, we don't crash -- we send the validation error
back to the model as a tool_result with `is_error=True`, so the model
can see what it got wrong and correct itself on the next turn. This
"self-correcting" loop is a standard pattern in real tool-calling agents.
"""

from typing import Literal
from pydantic import BaseModel, Field


class EmptyInput(BaseModel):
    """For tools that take no arguments (e.g. simple data-fetch calls)."""
    pass


class LookupChannelContextInput(BaseModel):
    channel: str = Field(..., description="Marketing channel name, e.g. 'Google Search'")


class GetPastRecommendationsInput(BaseModel):
    limit: int = Field(3, ge=1, le=20, description="How many past recommendations to retrieve")


class ApplyRecommendationInput(BaseModel):
    """
    Arguments for the one tool in this project that WRITES something
    rather than just reading it. See agents/copilot_agent.py -- calls
    to this tool are intercepted and require human approval before
    they actually execute, regardless of what the model decides.
    """
    channel: str = Field(..., description="Marketing channel this recommendation applies to")
    action: Literal["INCREASE", "MAINTAIN", "MONITOR", "REDUCE"] = Field(
        ..., description="Recommended budget action for this channel"
    )
    rationale: str = Field(..., description="One or two sentence justification for this action")

"""
agents/base_agent.py
---------------------
The shared machinery every agent in this project inherits. This is
where the three ingredients of an agent actually live:

  1. TOOLS  -> registered functions + Pydantic input schemas, exposed to
               Claude via the Messages API's native tool-use feature.
               The LLM genuinely decides which tool to call and with
               what arguments -- this file does not pre-decide that for
               it. That's the difference between this version and the
               "wireframe" version of this project, where an agent's
               LLM call only narrated a plan that the code ignored.

  2. LLM    -> `run_agentic_loop()` implements the standard tool-use
               loop: call the model, execute any tools it asks for,
               feed the results back, repeat until it produces a final
               answer (or we hit a safety limit).

  3. MEMORY -> a small persistent store per agent (JSON file today,
               swappable for a real database or vector store later)
               that tools can read from and write to.

Production systems built on the Claude API follow this same shape --
what changes going to prod is usually the *scale and robustness* of
each ingredient (a real vector DB instead of a JSON file, a workflow
engine instead of a for-loop), not the ingredients themselves.
"""

import json
import os
import time
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic import Anthropic, APIError, APIConnectionError, APITimeoutError, RateLimitError

import config
from logging_config import get_logger


class ToolExecutionError(Exception):
    """Raised when a tool's own logic fails (as opposed to bad input)."""


class RegisteredTool:
    """
    Bundles everything the agent loop needs to expose one Python
    function to Claude as a callable tool: its name, the JSON schema
    Claude sees, the Pydantic model used to validate incoming
    arguments, and the function to actually run.
    """

    def __init__(self, name: str, description: str, input_model: Type[BaseModel], func: Callable):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.func = func

    def to_anthropic_schema(self) -> dict:
        """The exact shape the Messages API expects in `tools=[...]`."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


class BaseAgent:
    """
    Shared base class for every agent. Subclasses:
      - call `self.register_tool(...)` in __init__ for each tool
      - implement `run(...)` to describe the agent's task
      - override `_fallback_run(...)` for deterministic, no-LLM behavior
    """

    def __init__(self, name: str, use_llm: Optional[bool] = None, model: str = config.MODEL_NAME):
        self.name = name
        self.model = model
        # An agent can be forced into rule-based mode even if the
        # pipeline default is LLM mode (config.USE_LLM) -- and vice
        # versa isn't possible without a real key, which is checked below.
        self.use_llm = config.USE_LLM if use_llm is None else use_llm
        self.tools: dict[str, RegisteredTool] = {}
        self.log = get_logger(name)

        self._client: Optional[Anthropic] = None
        if self.use_llm and config.ANTHROPIC_API_KEY:
            self._client = Anthropic(
                api_key=config.ANTHROPIC_API_KEY,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
            )
        elif self.use_llm and not config.ANTHROPIC_API_KEY:
            self.log.warning("USE_LLM is on but no ANTHROPIC_API_KEY was found; "
                              "falling back to rule-based mode for this agent.")
            self.use_llm = False

        os.makedirs(config.MEMORY_DIR, exist_ok=True)
        self.memory_path = os.path.join(config.MEMORY_DIR, f"{name}.json")
        self.memory: list[dict] = self._load_memory()

    # ------------------------------------------------------------------
    # MEMORY
    # ------------------------------------------------------------------
    def _load_memory(self) -> list[dict]:
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.log.warning("memory file was corrupt; starting fresh",
                                  extra={"path": self.memory_path})
        return []

    def remember(self, event: dict) -> None:
        """
        Append a structured event to this agent's memory and persist it
        immediately. Writing on every event (rather than batching) trades
        a little I/O for the guarantee that memory is never lost if the
        process crashes mid-run -- the right tradeoff for something
        meant to model durable state.
        """
        event = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}
        self.memory.append(event)
        with open(self.memory_path, "w") as f:
            json.dump(self.memory, f, indent=2, default=str)

    def recall(self, n: int = 5, event_type: Optional[str] = None) -> list[dict]:
        """Return the last n memory entries, optionally filtered by type."""
        entries = self.memory if event_type is None else [m for m in self.memory if m.get("type") == event_type]
        return entries[-n:]

    # ------------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------------
    def register_tool(self, name: str, func: Callable, description: str, input_model: Type[BaseModel]):
        self.tools[name] = RegisteredTool(name, description, input_model, func)

    def _tool_schemas(self) -> list[dict]:
        return [t.to_anthropic_schema() for t in self.tools.values()]

    def _execute_tool(self, tool_name: str, raw_input: dict) -> tuple[str, bool]:
        """
        Validates the LLM's arguments against the tool's Pydantic model,
        then runs the tool. Returns (result_text, is_error) so the
        caller can report the outcome back to the model as a proper
        tool_result block, including the `is_error` flag Claude uses to
        distinguish a successful result from a failure it should react to.
        """
        tool = self.tools.get(tool_name)
        if tool is None:
            return f"Error: no such tool '{tool_name}' is registered.", True

        # 1. Validate untrusted, model-generated input against our schema.
        try:
            validated = tool.input_model.model_validate(raw_input)
        except ValidationError as e:
            self.log.warning("tool input failed validation",
                              extra={"tool": tool_name, "error": str(e)})
            return f"Invalid arguments for '{tool_name}': {e}", True

        # 2. Run the tool itself, with its own error handling.
        try:
            self.log.info("executing tool", extra={"tool": tool_name, "args": validated.model_dump()})
            result = tool.func(**validated.model_dump())
            self.remember({"type": "tool_call", "tool": tool_name,
                            "args": validated.model_dump(), "result_summary": str(result)[:300]})
            return json.dumps(result, default=str), False
        except Exception as e:
            self.log.error("tool execution failed", extra={"tool": tool_name, "error": str(e)})
            self.remember({"type": "tool_error", "tool": tool_name, "error": str(e)})
            return f"Tool '{tool_name}' raised an error: {e}", True

    # ------------------------------------------------------------------
    # LLM -- the real agentic tool-use loop
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.RETRY_MIN_WAIT_SECONDS, max=config.RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
        reraise=True,
    )
    def _call_llm(self, system_prompt: str, messages: list[dict]) -> Any:
        """
        A single call to the Messages API, wrapped with retry-with-
        backoff for the transient failure modes worth retrying
        (connection drops, timeouts, rate limits). We deliberately do
        NOT retry on things like APIStatusError for a 400 (bad request)
        -- retrying a malformed request just fails the same way three
        more times. Only retry what a retry can plausibly fix.
        """
        return self._client.messages.create(
            model=self.model,
            max_tokens=config.MAX_OUTPUT_TOKENS,
            system=system_prompt,
            messages=messages,
            tools=self._tool_schemas(),
        )

    def run_agentic_loop(self, system_prompt: str, user_message: str) -> str:
        """
        The core agent loop:

          1. Send the model the task + available tools.
          2. If it asks to use a tool (stop_reason == "tool_use"),
             execute every tool call it requested, and send the
             results back.
          3. Repeat until it responds with a final answer, or we hit
             MAX_TOOL_ITERATIONS -- a hard safety cap so a confused
             model (or a bug) can never loop forever and rack up cost.

        This is the standard shape of every production tool-using agent
        built on the Anthropic API, regardless of how many tools or how
        complex the task.
        """
        messages: list[dict] = [{"role": "user", "content": user_message}]

        for iteration in range(config.MAX_TOOL_ITERATIONS):
            try:
                response = self._call_llm(system_prompt, messages)
            except APIError as e:
                # All retries exhausted (or a non-retryable API error).
                # Fail loudly rather than silently returning nothing --
                # the orchestrator needs to know this agent didn't complete.
                self.log.error("LLM call failed after retries", extra={"error": str(e)})
                raise

            self.remember({"type": "llm_response", "stop_reason": response.stop_reason,
                            "iteration": iteration})

            if response.stop_reason != "tool_use":
                # Model is done reasoning/acting -- extract its final text.
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                return final_text

            # Model wants to call one or more tools. Anthropic's API can
            # return several tool_use blocks in a single turn (parallel
            # tool calls) -- we must answer every one of them.
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text, is_error = self._execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                    "is_error": is_error,
                })
            messages.append({"role": "user", "content": tool_results})

        # Safety cap hit: the model kept requesting tools without
        # concluding. Better to surface this loudly than to silently
        # return a truncated/confused answer.
        self.log.warning("hit MAX_TOOL_ITERATIONS without a final answer")
        return "[Agent stopped: exceeded maximum tool-call iterations without producing a final answer.]"

    # ------------------------------------------------------------------
    # Entry point every subclass implements
    # ------------------------------------------------------------------
    def run(self, *args, **kwargs):
        raise NotImplementedError

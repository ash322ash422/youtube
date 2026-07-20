# Marketing campaign analysis agent -- production-pattern version

A capstone-ready rewrite of the agentic pipeline that uses the actual
patterns production teams use when building on the Claude API: real
tool-calling, input validation, retries, structured logging, a
checkpointed/resumable orchestrator, unit tests, and a human-approval
gate before any write action.

It still runs with **zero setup** in rule-based mode, and every file is
commented to explain *why* each pattern exists, not just what the code
does -- read the comments as you go, they're the actual lesson.

## Quickstart

```bash
pip install -r requirements.txt

# Rule-based mode -- no API key needed, every agent uses deterministic logic
python main.py

# Real LLM + tool-calling mode
cp .env.example .env        # then paste a real ANTHROPIC_API_KEY into it
python main.py --use-llm

# Skip the human-approval prompt (useful for demos / CI)
python main.py --use-llm --auto-approve

# Run tests
pytest tests/ -v
```

## What changed from the "wireframe" version

| | Wireframe version | This version |
|---|---|---|
| LLM's role | Narrated a plan; code ignored it and called tools in fixed order | LLM genuinely decides which tool to call, via Claude's native tool-use API (`agents/base_agent.py: run_agentic_loop`) |
| Tool inputs | Called directly, no validation | Every tool has a Pydantic schema; the LLM's arguments are validated before anything runs (`agents/tool_schemas.py`) |
| Failures | None handled | Retries with exponential backoff on transient API errors (`tenacity`, see `base_agent._call_llm`); tool errors reported back to the model as `is_error` results so it can self-correct |
| Logging | `print()` | Structured, one-JSON-object-per-line logs (`logging_config.py`) |
| Orchestration | Plain function calls, restart from scratch on crash | Checkpointed after every stage; resumes instead of repeating finished work (`orchestrator.py`) |
| Consequential actions | None existed | `apply_recommendation` is a WRITE tool gated behind an explicit human-approval step (`agents/copilot_agent.py`) |
| Testing | None | `pytest` unit tests for every deterministic function (`tests/`) |
| Config | Scattered | One `config.py`, entirely env-var driven |

## Project structure

```
capstone_project/
├── main.py                      <- CLI entry point
├── config.py                    <- all tunables, read from env vars
├── logging_config.py            <- structured JSON logging setup
├── orchestrator.py               <- checkpointed, resumable pipeline runner
├── requirements.txt
├── .env.example
├── data/
│   └── campaign_data.csv
├── memory/                       <- created at runtime, one JSON file per agent
├── checkpoints/                  <- created at runtime, resumable pipeline state
├── agents/
│   ├── base_agent.py              <- the real tool-use loop + memory + retries
│   ├── tool_schemas.py              <- Pydantic input schemas for every tool
│   ├── data_agent.py                 <- Agent 1
│   ├── analytics_agent.py             <- Agent 2
│   └── copilot_agent.py                <- Agent 3
└── tests/
    └── test_analytics_agent.py    <- unit tests for the deterministic math/logic
```

## The core idea: `run_agentic_loop`

Every agent's "smart" behavior funnels through one method in
`agents/base_agent.py`:

1. Send Claude the task, plus JSON-schema definitions of every tool
   this agent has.
2. If Claude's response says `stop_reason == "tool_use"`, the model has
   decided (on its own) to call one or more tools with specific
   arguments. We validate those arguments, execute the real Python
   function, and send the result back.
3. Repeat until Claude produces a final answer, or a safety cap
   (`MAX_TOOL_ITERATIONS`) is hit.

This is the actual mechanism, not a simulation of it -- when
`--use-llm` is on and a valid API key is set, the model is making real
decisions about which tool to call and when.

## Why some functions are tools and some aren't

`compute_kpis` (in `AnalyticsAgent`) and `_rule_based_decision` (in
`CopilotAgent`) are **not** exposed to the LLM as callable tools --
they're called directly by Python code. Read the design notes at the
top of those two files for the full reasoning, but the short version:
anything that's pure, deterministic math or a governed business rule
should stay deterministic. Tool-calling is for judgment calls the model
is well-suited to make (should I look up more context? what's a good
rationale?) -- not for arithmetic you can already test and trust.

## The human-in-the-loop gate

`CopilotAgent.apply_recommendation` is the one tool in this project
that *writes* something (it stands in for pushing a real budget change
to an ads platform). Every call to it -- whether the LLM or the rule
engine decided on the action -- is intercepted by
`_request_human_approval`, which blocks on a real y/n prompt before
anything is considered "applied." This mirrors a non-negotiable rule in
production agent design: an agent deciding to do something is not the
same as being authorized to do it.

## Exercises for a capstone project

1. **Add a fourth agent.** A `ForecastAgent` that projects next month's
   spend needs given current trends -- give it its own tool(s), wire it
   into the orchestrator as a fourth checkpointed stage.
2. **Swap memory for a real store.** Replace the JSON file in
   `BaseAgent.remember`/`recall` with SQLite or a vector DB, and explain
   in a short writeup what actually gets easier/harder.
3. **Add a genuine async fan-out.** `DataAgent`'s two tools don't depend
   on each other -- rewrite it so both are fetched concurrently (e.g.
   with `asyncio.gather`), and measure the wall-clock difference.
4. **Break it on purpose.** Force `_execute_tool` to receive bad
   arguments (e.g. temporarily remove a required field from
   `ApplyRecommendationInput`) and trace exactly how the validation
   error reaches the model, and whether it self-corrects.
5. **Write an eval, not just a unit test.** Using `--use-llm`, run the
   pipeline 5 times and grade whether `AnalyticsAgent`'s notes actually
   mention every channel that breached a rule-based threshold. This is
   the beginning of a real LLM eval harness.
6. **Replace the checkpoint file with a real workflow engine.** Try
   reimplementing `orchestrator.py`'s resumability using LangGraph, and
   compare how much of `orchestrator.py` you got to delete.
